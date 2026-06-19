import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel


BASE_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = BASE_DIR / "my_auto_learn.py"
USER_DIR = BASE_DIR / "users"
DATA_DIR = BASE_DIR / "Data"
STATIC_DIR = BASE_DIR / "static"
RUNTIME_DIR = BASE_DIR / ".runtime"
MAX_LOG_LINES = int(os.getenv("AUTO_LEARN_MAX_LOG_LINES", "1200"))

app = FastAPI(title="Auto Learn Web", version="0.1.0")
_auto_module = None
_auto_module_lock = threading.Lock()


def load_auto_module():
    global _auto_module
    with _auto_module_lock:
        if _auto_module is None:
            spec = importlib.util.spec_from_file_location("auto_learn_core", SCRIPT_PATH)
            if spec is None or spec.loader is None:
                raise RuntimeError(f"无法加载脚本: {SCRIPT_PATH}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            _auto_module = module
        return _auto_module


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class QueueWriter(io.TextIOBase):
    def __init__(self, job: "JobState"):
        self.job = job
        self._buffer = ""

    def writable(self) -> bool:
        return True

    def write(self, text: str) -> int:
        if not text:
            return 0
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self.job.log(line)
        return len(text)

    def flush(self):
        if self._buffer:
            self.job.log(self._buffer)
            self._buffer = ""


@dataclass
class JobState:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    action: str = ""
    user_file: str = ""
    username: str = ""
    finish_exam: bool = True
    status: str = "idle"
    message: str = ""
    current_step: str = "等待开始"
    current_course: str = ""
    course_index: int = 0
    total_courses: int = 0
    current_chapter: str = ""
    chapter_index: int = 0
    total_chapters: int = 0
    chapter_progress: int = 0
    chapter_progress_updated_at: Optional[float] = None
    remaining_courses: int = 0
    business_failed: bool = False
    study_windows: str = ""
    keep_schedule: bool = True
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    wait_started_at: Optional[float] = None
    wait_total_seconds: int = 0
    wait_until_at: Optional[float] = None
    logs: List[str] = field(default_factory=list)
    stop_event: threading.Event = field(default_factory=threading.Event)
    thread: Optional[threading.Thread] = None
    process: Optional[subprocess.Popen] = None

    def log(self, line: str):
        line = strip_ansi(line).rstrip()
        if not line:
            return
        self.update_progress(line)
        self.logs.append(f"[{now_text()}] {line}")
        if len(self.logs) > MAX_LOG_LINES:
            self.logs = self.logs[-MAX_LOG_LINES:]

    def update_progress(self, line: str):
        course_match = re.search(r'\[\s*(\d+)\s*/\s*(\d+)\s*\]\s+(.+)$', line)
        if course_match:
            self.clear_wait_countdown()
            self.course_index = int(course_match.group(1))
            self.total_courses = int(course_match.group(2))
            self.current_course = course_match.group(3).strip()
            self.current_chapter = ""
            self.chapter_index = 0
            self.total_chapters = 0
            self.chapter_progress = 0
            self.current_step = "学习课程"
            return

        chapter_match = re.search(r'第\s*(\d+)\s*/\s*(\d+)\s*章:\s*(.+?)(?:\s*\((\d+)%\))?$', line)
        if chapter_match:
            self.clear_wait_countdown()
            self.chapter_index = int(chapter_match.group(1))
            self.total_chapters = int(chapter_match.group(2))
            self.current_chapter = chapter_match.group(3).strip()
            if chapter_match.group(4):
                self.chapter_progress = int(chapter_match.group(4))
                self.chapter_progress_updated_at = time.time()
            self.current_step = "观看视频"
            return

        chapter_done_match = re.search(r'章节完成:\s*(.+)$', line)
        if chapter_done_match:
            self.clear_wait_countdown()
            self.current_chapter = chapter_done_match.group(1).strip()
            self.chapter_progress = 100
            self.chapter_progress_updated_at = time.time()
            self.current_step = "完成当前章节"

        total_match = re.search(r'找到\s+(\d+)\s+门未完成课程', line)
        if total_match:
            self.clear_wait_countdown()
            self.total_courses = int(total_match.group(1))
            self.current_step = "准备学习"
            return

        if "开始学习视频" in line:
            self.clear_wait_countdown()
            self.current_step = "观看视频"
        elif "收集考试题目" in line or "开始收集题目" in line:
            self.clear_wait_countdown()
            self.current_step = "收集题库"
        elif "参加最终考试" in line or "开始最终考试" in line:
            self.clear_wait_countdown()
            self.current_step = "自动答题"
        elif "课程学习完成" in line or "视频学习完成" in line:
            self.clear_wait_countdown()
            self.current_step = "完成当前课程"
        elif "所有课程都已完成" in line:
            self.clear_wait_countdown()
            self.current_step = "全部完成"
        elif "当前不在学习时间内" in line or "当前不在允许学习时间内" in line:
            self.current_step = "等待学习时间"
            self.start_wait_countdown()
        elif "正在登录认证" in line:
            self.clear_wait_countdown()
            self.current_step = "登录认证"
        elif "获取课程信息" in line or "正在扫描课程列表" in line:
            self.clear_wait_countdown()
            self.current_step = "获取课程"

        remaining_match = re.search(r'还有\s+(\d+)\s+门课程需要处理', line)
        if remaining_match:
            self.remaining_courses = int(remaining_match.group(1))
            self.current_step = "任务未完成"

        if any(keyword in line for keyword in ("章节失败", "视频学习失败", "考试失败", "题目收集失败", "最终考试失败")):
            self.clear_wait_countdown()
            self.business_failed = True
            self.current_step = "任务未完成"

    def seconds_until_next_window(self) -> int:
        if not self.study_windows:
            return 0
        try:
            module = load_auto_module()
            return int(module.StudyTimeWindow(self.study_windows).seconds_until_next_window())
        except Exception:
            return 0

    def start_wait_countdown(self):
        remaining = self.seconds_until_next_window()
        now = time.time()
        if remaining <= 0:
            self.clear_wait_countdown()
            return
        if not self.wait_until_at or abs(self.wait_until_at - (now + remaining)) > 5:
            self.wait_started_at = now
            self.wait_total_seconds = remaining
            self.wait_until_at = now + remaining

    def clear_wait_countdown(self):
        self.wait_started_at = None
        self.wait_total_seconds = 0
        self.wait_until_at = None

    def wait_snapshot(self) -> Dict[str, Any]:
        running = self.process is not None and self.process.poll() is None
        if self.current_step != "等待学习时间" or not running:
            return {
                "wait_remaining_seconds": 0,
                "wait_total_seconds": 0,
                "wait_progress_percent": 0,
                "wait_until_at": None,
            }

        remaining = self.seconds_until_next_window()
        if remaining <= 0:
            return {
                "wait_remaining_seconds": 0,
                "wait_total_seconds": self.wait_total_seconds,
                "wait_progress_percent": 100,
                "wait_until_at": self.wait_until_at,
            }

        if self.wait_total_seconds <= 0 or remaining > self.wait_total_seconds:
            self.wait_started_at = time.time()
            self.wait_total_seconds = remaining
            self.wait_until_at = self.wait_started_at + remaining

        total = max(remaining, self.wait_total_seconds, 1)
        progress = max(0, min(100, round((1 - remaining / total) * 100)))
        return {
            "wait_remaining_seconds": remaining,
            "wait_total_seconds": total,
            "wait_progress_percent": progress,
            "wait_until_at": self.wait_until_at,
        }

    def snapshot(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "action": self.action,
            "user_file": self.user_file,
            "username": self.username,
            "finish_exam": self.finish_exam,
            "status": self.status,
            "message": self.message,
            "current_step": self.current_step,
            "current_course": self.current_course,
            "course_index": self.course_index,
            "total_courses": self.total_courses,
            "current_chapter": self.current_chapter,
            "chapter_index": self.chapter_index,
            "total_chapters": self.total_chapters,
            "chapter_progress": self.chapter_progress,
            "chapter_progress_updated_at": self.chapter_progress_updated_at,
            "remaining_courses": self.remaining_courses,
            "study_windows": self.study_windows,
            "keep_schedule": self.keep_schedule,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "logs": self.logs,
            "running": self.process is not None and self.process.poll() is None,
        }
        data.update(self.wait_snapshot())
        return data


def strip_ansi(text: str) -> str:
    import re

    return re.sub(r"\x1b\[[0-9;]*m", "", text)


job_lock = threading.Lock()
jobs: Dict[str, JobState] = {}


class CreateUserRequest(BaseModel):
    auth_code: str


class JobRequest(BaseModel):
    action: str
    user_file: str
    finish_exam: bool = True
    study_windows: str = ""
    keep_schedule: bool = True
    course_type: str = ""
    year: int = 0
    credit: float = 30.0


class StopJobRequest(BaseModel):
    user_file: Optional[str] = None


class UpdateScheduleRequest(BaseModel):
    user_file: str
    study_windows: str = ""
    keep_schedule: bool = True


def read_schedule_control(user_file: str) -> Dict[str, Any]:
    path = control_path_for_user(user_file)
    if not path.exists():
        return {"study_windows": "", "keep_schedule": True}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "study_windows": data.get("study_windows", ""),
            "keep_schedule": bool(data.get("keep_schedule", True)),
        }
    except Exception:
        return {"study_windows": "", "keep_schedule": True}


def list_users() -> List[Dict[str, Any]]:
    USER_DIR.mkdir(exist_ok=True)
    users = []
    for path in sorted(USER_DIR.glob("*.atl")):
        username = path.stem
        try:
            with path.open("r", encoding="utf-8") as f:
                username = json.load(f).get("username") or username
        except Exception:
            pass
        schedule = read_schedule_control(path.name)
        users.append({"file": path.name, "username": username, **schedule})
    return users


def user_path_from_name(name: str) -> Path:
    path = (USER_DIR / name).resolve()
    if not path.is_file() or path.parent != USER_DIR.resolve() or path.suffix != ".atl":
        raise HTTPException(status_code=400, detail="用户文件不存在")
    return path


def safe_runtime_name(name: str) -> str:
    readable = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._")[:24] or "user"
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:16]
    return f"{readable}-{digest}"


def control_path_for_user(user_file: str) -> Path:
    RUNTIME_DIR.mkdir(exist_ok=True)
    return RUNTIME_DIR / f"{safe_runtime_name(user_file)}.json"


def write_schedule_control(user_file: str, study_windows: str, keep_schedule: bool):
    control_path_for_user(user_file).write_text(
        json.dumps({"study_windows": study_windows, "keep_schedule": keep_schedule}, ensure_ascii=False),
        encoding="utf-8",
    )


def sleep_until_window(job: JobState, guard, stop_event: threading.Event):
    wait_seconds = guard.seconds_until_next_window()
    job.log(f"当前不在学习时间内，下次时间窗约 {wait_seconds // 60} 分钟后开始")
    while wait_seconds > 0 and not stop_event.is_set():
        nap = min(60, wait_seconds)
        time.sleep(nap)
        wait_seconds -= nap


def execute_payload(payload: JobRequest):
    module = load_auto_module()

    username, url_zxpx = module._decode_read(path=user_path_from_name(payload.user_file))
    print(f"已选择用户: {username}", flush=True)

    if payload.action == "learn":
        guard = module.StudyTimeWindow(payload.study_windows)
        schedule_settings = {"keep_schedule": payload.keep_schedule, "study_windows": payload.study_windows}
        schedule_stop = threading.Event()

        def sync_schedule():
            last_text = None
            while not schedule_stop.is_set():
                try:
                    control_path = control_path_for_user(payload.user_file)
                    if control_path.exists():
                        text = control_path.read_text(encoding="utf-8")
                        if text != last_text:
                            data = json.loads(text)
                            schedule_settings["study_windows"] = data.get("study_windows", "")
                            schedule_settings["keep_schedule"] = bool(data.get("keep_schedule", True))
                            guard.update(schedule_settings["study_windows"])
                            print(f"学习时间窗已更新: {guard.describe()}", flush=True)
                            last_text = text
                except Exception as exc:
                    print(f"学习时间窗更新失败: {exc}", flush=True)
                schedule_stop.wait(5)

        schedule_thread = threading.Thread(target=sync_schedule, daemon=True)
        schedule_thread.start()
        if guard.enabled():
            print(f"学习时间窗: {guard.describe()}", flush=True)

        try:
            while True:
                if guard.enabled() and not guard.is_allowed():
                    if not schedule_settings["keep_schedule"]:
                        raise module.StudyWindowClosed(f"当前不在允许学习时间内: {guard.describe()}")
                    wait_seconds = guard.seconds_until_next_window()
                    print(f"当前不在学习时间内，下次时间窗约 {wait_seconds // 60} 分钟后开始", flush=True)
                    while wait_seconds > 0 and guard.enabled() and not guard.is_allowed():
                        time.sleep(min(30, wait_seconds))
                        wait_seconds = guard.seconds_until_next_window()
                    continue

                auto_study = module.AutoStudyRefactored(
                    data_folder=DATA_DIR,
                    username=username,
                    url_zxpx=url_zxpx,
                    study_time_window=guard,
                )
                try:
                    auto_study.all_in_one(finish_exam=payload.finish_exam)
                    break
                except module.StudyWindowClosed as exc:
                    print(str(exc), flush=True)
                    if not schedule_settings["keep_schedule"]:
                        raise
        finally:
            schedule_stop.set()

    elif payload.action == "add_course":
        auto_study = module.AutoStudyRefactored(data_folder=DATA_DIR, username=username, url_zxpx=url_zxpx)
        auto_study.add_course(rt=payload.course_type, year=payload.year, credit=payload.credit)

    elif payload.action == "cancel_course":
        auto_study = module.AutoStudyRefactored(data_folder=DATA_DIR, username=username, url_zxpx=url_zxpx)
        auto_study.cancel_all_course()
    else:
        raise ValueError("未知任务类型")


def payload_to_json(payload: JobRequest) -> str:
    if hasattr(payload, "model_dump_json"):
        return payload.model_dump_json()
    return payload.json()


def run_job(job: JobState, payload: JobRequest):
    job.started_at = now_text()
    job.status = "running"
    job.message = "任务运行中"
    job.current_step = "启动任务"
    job.study_windows = payload.study_windows
    job.keep_schedule = payload.keep_schedule
    job.finish_exam = payload.finish_exam
    write_schedule_control(payload.user_file, payload.study_windows, payload.keep_schedule)

    try:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        process = subprocess.Popen(
            [sys.executable, "-u", str(Path(__file__).resolve()), "--worker", payload_to_json(payload)],
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
        job.process = process
        if process.stdout:
            for line in process.stdout:
                job.log(line)

        return_code = process.wait()
        if job.stop_event.is_set():
            job.clear_wait_countdown()
            job.status = "stopped"
            job.message = "任务已停止"
            job.current_step = "已停止"
        elif return_code == 0:
            job.clear_wait_countdown()
            if job.business_failed or job.remaining_courses > 0:
                job.status = "incomplete"
                job.message = f"还有 {job.remaining_courses} 门课程需要处理" if job.remaining_courses > 0 else "任务未完成"
                job.current_step = "任务未完成"
            else:
                job.status = "success"
                job.message = "任务完成"
                if job.current_step != "全部完成":
                    job.current_step = "任务完成"
        else:
            job.clear_wait_countdown()
            job.status = "failed"
            job.message = f"任务退出码: {return_code}"
            job.current_step = "任务失败"
    except Exception as exc:
        job.clear_wait_countdown()
        job.status = "failed"
        job.message = str(exc)
        job.current_step = "任务失败"
        job.log(f"任务失败: {exc}")
        job.log(traceback.format_exc())
    finally:
        job.ended_at = now_text()


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/favicon.svg")
def favicon_svg():
    return FileResponse(STATIC_DIR / "favicon.svg", media_type="image/svg+xml")


@app.get("/favicon.ico")
def favicon_ico():
    return FileResponse(STATIC_DIR / "favicon.svg", media_type="image/svg+xml")


@app.get("/api/users")
def api_users():
    return {"users": list_users()}


@app.post("/api/users")
def api_create_user(payload: CreateUserRequest):
    if not payload.auth_code.strip():
        raise HTTPException(status_code=400, detail="authCode 不能为空")
    module = load_auto_module()
    username, url_zxpx = module._login(authCode=payload.auth_code.strip())
    if not username or not url_zxpx:
        raise HTTPException(status_code=400, detail="登录失败，请重新获取 authCode")
    USER_DIR.mkdir(exist_ok=True)
    target = USER_DIR / f"{username}.atl"
    if not module._encode_write(username=username, text=url_zxpx, path=target):
        raise HTTPException(status_code=500, detail="用户文件保存失败")
    return {"ok": True, "username": username, "file": target.name}


@app.get("/api/state")
def api_state():
    with job_lock:
        snapshots = [job.snapshot() for job in jobs.values()]
        snapshots.sort(key=lambda item: item.get("started_at") or "", reverse=True)
        return JSONResponse({"jobs": snapshots})


@app.post("/api/jobs")
def api_start_job(payload: JobRequest):
    with job_lock:
        user_path = user_path_from_name(payload.user_file)
        username = payload.user_file
        try:
            with user_path.open("r", encoding="utf-8") as f:
                username = json.load(f).get("username") or payload.user_file
        except Exception:
            pass

        existing_job = jobs.get(payload.user_file)
        if existing_job and existing_job.process is not None and existing_job.process.poll() is None:
            raise HTTPException(status_code=409, detail=f"{username} 已有任务正在运行")

        job = JobState(
            action=payload.action,
            user_file=payload.user_file,
            username=username,
            finish_exam=payload.finish_exam,
            study_windows=payload.study_windows,
            keep_schedule=payload.keep_schedule,
        )
        jobs[payload.user_file] = job
        thread = threading.Thread(target=run_job, args=(job, payload), daemon=True)
        job.thread = thread
        thread.start()
        return job.snapshot()


@app.post("/api/jobs/stop")
def api_stop_job(payload: StopJobRequest):
    with job_lock:
        target_jobs = [jobs[payload.user_file]] if payload.user_file and payload.user_file in jobs else list(jobs.values())
        for job in target_jobs:
            if job.process is None or job.process.poll() is not None:
                continue
            job.stop_event.set()
            job.status = "stopping"
            job.message = "正在停止"
            job.current_step = "正在停止"
            job.log("收到停止请求")
            job.process.terminate()
        return {"jobs": [job.snapshot() for job in jobs.values()]}


@app.post("/api/jobs/schedule")
def api_update_schedule(payload: UpdateScheduleRequest):
    user_path_from_name(payload.user_file)
    try:
        # Validate before writing so a running worker will not receive bad input.
        module = load_auto_module()
        module.StudyTimeWindow(payload.study_windows)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    with job_lock:
        write_schedule_control(payload.user_file, payload.study_windows, payload.keep_schedule)
        job = jobs.get(payload.user_file)
        if job:
            job.study_windows = payload.study_windows
            job.keep_schedule = payload.keep_schedule
            if job.current_step == "等待学习时间":
                job.clear_wait_countdown()
                job.start_wait_countdown()
            job.log(f"学习时间窗设置为: {payload.study_windows or '全天'}")
            return job.snapshot()
        return {"user_file": payload.user_file, "study_windows": payload.study_windows, "keep_schedule": payload.keep_schedule}




if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--worker":
        worker_payload = JobRequest.model_validate_json(sys.argv[2]) if hasattr(JobRequest, "model_validate_json") else JobRequest.parse_raw(sys.argv[2])
        execute_payload(worker_payload)
        raise SystemExit(0)

    import uvicorn

    def pick_port(default_port: int = 28000) -> int:
        if os.getenv("PORT"):
            return default_port
        for port in range(default_port, default_port + 20):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                if sock.connect_ex(("127.0.0.1", port)) != 0:
                    return port
        return default_port

    port = pick_port(int(os.getenv("PORT", "28000")))
    print(f"Auto Learn Web 启动中: http://127.0.0.1:{port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
