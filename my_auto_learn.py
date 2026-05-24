"""
完全重构的自动学习系统 - 统一美化版
保持与原代码的数据格式和存储位置完全兼容

更新记录：
2025-05-31 统一输出风格，提升用户体验：
           - 统一所有打印输出使用UIFormatter
           - 保持功能逻辑100%不变，只优化显示效果
           - 添加一致的进度显示和状态反馈
           - 优化错误处理的用户友好性

✨ 美化特性：
- 🎨 全面统一的彩色终端输出
- 📊 一致的进度条和状态显示
- 🎭 统一的图标和符号体系
- 📦 美观的边框和布局
- ⏱️ 统一的时间和统计信息
- 📈 一致的成功率分析

使用说明：
    auto_study = AutoStudyRefactored(data_folder=data_folder, username=username, url_zxpx=url_zxpx)
    auto_study.all_in_one(finish_exam=True)  # 自动学习并考试

主要功能：
- all_in_one: 把选入课表的未完成的视频全部看完，收集题目并做满分答卷
- add_course: 根据条件批量添加课程到课表
- cancel_all_course: 取消所有未开始的课程
"""

import math
import os
import pandas as pd
import requests
import re
from lxml import etree
import time
import json
import random
import sys
import requests.packages.urllib3
from pathlib import Path
import datetime
import numpy as np
from math import comb, ceil, floor
import ast
import contextlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple, Union
from enum import Enum
import logging

# 禁用安全请求警告
requests.packages.urllib3.disable_warnings()


# ================ 美化输出工具 ================

class Colors:
    """颜色定义"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

    # 基础颜色
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'

    # 亮色
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'

    # 背景色
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'


class Icons:
    """图标定义"""
    SUCCESS = '✅'
    FAILURE = '❌'
    WARNING = '⚠️'
    INFO = 'ℹ️'
    PROGRESS = '🔄'
    BOOK = '📚'
    VIDEO = '🎥'
    EXAM = '📝'
    ROCKET = '🚀'
    STAR = '⭐'
    CLOCK = '⏰'
    CHECK = '✓'
    CROSS = '✗'
    ARROW = '➤'
    DOT = '●'
    CIRCLE = '○'
    PLUS = '➕'
    MINUS = '➖'
    FOLDER = '📁'
    FILE = '📄'
    GEAR = '⚙️'
    SHIELD = '🛡️'
    FIRE = '🔥'
    LIGHTNING = '⚡'


class UIFormatter:
    """统一的UI格式化工具"""

    @staticmethod
    def header(text: str, char: str = '═', width: int = 60) -> str:
        """创建统一的标题"""
        text = f" {text} "
        padding = (width - len(text)) // 2
        line = char * width
        title_line = char * padding + text + char * (width - padding - len(text))
        return f"\n{Colors.CYAN}{Colors.BOLD}{line}\n{title_line}\n{line}{Colors.RESET}\n"

    @staticmethod
    def section(text: str, icon: str = Icons.ARROW) -> str:
        """创建统一的章节标题"""
        return f"\n{Colors.BRIGHT_BLUE}{Colors.BOLD}{icon} {text}{Colors.RESET}"

    @staticmethod
    def subsection(text: str, icon: str = Icons.DOT) -> str:
        """创建统一的子章节标题"""
        return f"  {Colors.BLUE}{icon} {text}{Colors.RESET}"

    @staticmethod
    def success(text: str, icon: str = Icons.SUCCESS) -> str:
        """统一的成功消息"""
        return f"{Colors.BRIGHT_GREEN}{icon} {text}{Colors.RESET}"

    @staticmethod
    def error(text: str, icon: str = Icons.FAILURE) -> str:
        """统一的错误消息"""
        return f"{Colors.BRIGHT_RED}{icon} {text}{Colors.RESET}"

    @staticmethod
    def warning(text: str, icon: str = Icons.WARNING) -> str:
        """统一的警告消息"""
        return f"{Colors.BRIGHT_YELLOW}{icon} {text}{Colors.RESET}"

    @staticmethod
    def info(text: str, icon: str = Icons.INFO) -> str:
        """统一的信息消息"""
        return f"{Colors.BRIGHT_CYAN}{icon} {text}{Colors.RESET}"

    @staticmethod
    def status(text: str, status_type: str = "info", icon: str = None) -> str:
        """统一的状态消息"""
        if icon is None:
            icon_map = {
                "success": Icons.CHECK,
                "error": Icons.CROSS,
                "warning": Icons.WARNING,
                "info": Icons.INFO,
                "progress": Icons.PROGRESS
            }
            icon = icon_map.get(status_type, Icons.INFO)

        color_map = {
            "success": Colors.BRIGHT_GREEN,
            "error": Colors.BRIGHT_RED,
            "warning": Colors.BRIGHT_YELLOW,
            "info": Colors.BRIGHT_CYAN,
            "progress": Colors.YELLOW
        }
        color = color_map.get(status_type, Colors.BRIGHT_CYAN)

        return f"{color}{icon} {text}{Colors.RESET}"

    @staticmethod
    def progress_bar(current: int, total: int, width: int = 30,
                     filled_char: str = '█', empty_char: str = '░') -> str:
        """创建统一的进度条"""
        if total == 0:
            percent = 100
        else:
            percent = min(100, (current * 100) // total)

        filled_width = (percent * width) // 100
        empty_width = width - filled_width

        bar = filled_char * filled_width + empty_char * empty_width

        if percent >= 55:
            color = Colors.BRIGHT_GREEN
        elif percent >= 25:
            color = Colors.BRIGHT_YELLOW
        else:
            color = Colors.BRIGHT_RED

        return f"{color}[{bar}] {percent:3d}%{Colors.RESET}"

    @staticmethod
    def numbered_item(index: int, text: str, total: int = None, status: str = "") -> str:
        """统一的编号项目格式"""
        if total:
            prefix = f"{Colors.BRIGHT_BLUE}[{index:2d}/{total:2d}]{Colors.RESET}"
        else:
            prefix = f"{Colors.BRIGHT_BLUE}{index:2d}.{Colors.RESET}"

        item_text = f"{Colors.BOLD}{text}{Colors.RESET}"

        if status:
            return f"{prefix} {item_text} {status}"
        return f"{prefix} {item_text}"

    @staticmethod
    def process_status(process_name: str, status: str, details: str = "") -> str:
        """统一的处理状态格式"""
        status_map = {
            "starting": (Icons.PROGRESS, Colors.YELLOW, "正在开始"),
            "running": (Icons.PROGRESS, Colors.BLUE, "处理中"),
            "success": (Icons.SUCCESS, Colors.BRIGHT_GREEN, "成功"),
            "failed": (Icons.FAILURE, Colors.BRIGHT_RED, "失败"),
            "warning": (Icons.WARNING, Colors.BRIGHT_YELLOW, "警告"),
            "skipped": (Icons.CIRCLE, Colors.DIM, "跳过")
        }

        icon, color, status_text = status_map.get(status, (Icons.INFO, Colors.CYAN, status))

        main_text = f"{color}{icon} {process_name}: {status_text}{Colors.RESET}"

        if details:
            main_text += f" {Colors.DIM}({details}){Colors.RESET}"

        return main_text

    @staticmethod
    def step_indicator(current_step: int, total_steps: int, step_name: str) -> str:
        """统一的步骤指示器"""
        progress = UIFormatter.progress_bar(current_step, total_steps, 20)
        return f"  {progress} {Colors.BOLD}步骤 {current_step}/{total_steps}: {step_name}{Colors.RESET}"

    @staticmethod
    def statistics_summary(title: str, stats: dict) -> str:
        """统一的统计信息摘要"""
        lines = [f"{Colors.BRIGHT_CYAN}{Colors.BOLD}📊 {title}{Colors.RESET}"]

        for key, value in stats.items():
            if isinstance(value, (int, float)):
                if key.endswith("_rate") or key.endswith("率"):
                    # 百分比显示
                    if value >= 90:
                        color = Colors.BRIGHT_GREEN
                        icon = Icons.STAR
                    elif value >= 70:
                        color = Colors.BRIGHT_YELLOW
                        icon = Icons.CHECK
                    else:
                        color = Colors.BRIGHT_RED
                        icon = Icons.WARNING
                    lines.append(f"  {color}{icon} {key}: {value:.1f}%{Colors.RESET}")
                else:
                    # 数字显示
                    lines.append(f"  {Colors.CYAN}{Icons.DOT} {key}: {value}{Colors.RESET}")
            else:
                lines.append(f"  {Colors.CYAN}{Icons.DOT} {key}: {value}{Colors.RESET}")

        return "\n".join(lines)

    @staticmethod
    def menu_item(key: str, description: str, selected: bool = False) -> str:
        """统一的菜单项格式"""
        if selected:
            return f"{Colors.BG_BLUE}{Colors.WHITE} {key} {Colors.RESET} {Colors.BOLD}{description}{Colors.RESET}"
        else:
            return f"{Colors.BRIGHT_BLUE} {key} {Colors.RESET} {description}"

    @staticmethod
    def input_prompt(prompt: str, default: str = None, icon: str = Icons.ARROW) -> str:
        """统一的输入提示格式"""
        prompt_text = f"{Colors.BRIGHT_YELLOW}{icon} {prompt}{Colors.RESET}"
        if default:
            prompt_text += f" {Colors.DIM}(默认: {default}){Colors.RESET}"
        return prompt_text + ": "

    @staticmethod
    def divider(char: str = "─", width: int = 50) -> str:
        """统一的分隔线"""
        return f"{Colors.DIM}{char * width}{Colors.RESET}"

    @staticmethod
    def print_formatted(text: str, prefix: str = ""):
        """统一的格式化打印"""
        if prefix:
            print(f"{prefix}{text}")
        else:
            print(text)


# ================ 数据模型（保持不变）================

class CourseState(Enum):
    """课程状态"""
    NOT_STARTED = 0
    IN_PROGRESS = 1
    COMPLETED = 2


@dataclass
class Course:
    """课程信息"""
    subject_title: str
    ocid: str
    subject_type: str = ""
    subject_teacher: str = ""
    subject_credit: str = "0"
    subject_year: str = ""
    cancel_href: str = ""
    cancel_id: str = ""
    state: int = 0


@dataclass
class Chapter:
    """章节信息"""
    cpcwid: str
    chaptername: str
    hasstarted: int = 0


@dataclass
class Question:
    """题目信息 - 保持原格式"""
    type: str
    title_text: str
    title_id: str
    option_value: List[str]
    option_text: List[str]


# ================ 异常定义（保持不变）================

class AutoStudyException(Exception):
    """自动学习异常基类"""
    pass


class LoginException(AutoStudyException):
    """登录异常"""
    pass


class NetworkException(AutoStudyException):
    """网络请求异常"""
    pass


class DataParseException(AutoStudyException):
    """数据解析异常"""
    pass


class StudyWindowClosed(AutoStudyException):
    """当前不在允许学习时间内"""
    pass


class StudyTimeWindow:
    """学习时间窗守卫，支持 08:00-12:00、20:00-23:30 这类配置"""

    def __init__(self, windows: Optional[Union[str, List[dict], List[Tuple[str, str]]]] = None):
        self.windows = self._parse_windows(windows)

    def update(self, windows: Optional[Union[str, List[dict], List[Tuple[str, str]]]] = None):
        self.windows = self._parse_windows(windows)

    def enabled(self) -> bool:
        return bool(self.windows)

    def describe(self) -> str:
        if not self.windows:
            return "全天"
        return "，".join(f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}" for start, end in self.windows)

    def is_allowed(self, now: Optional[datetime.datetime] = None) -> bool:
        if not self.windows:
            return True
        now_time = (now or datetime.datetime.now()).time()
        return any(self._time_in_window(now_time, start, end) for start, end in self.windows)

    def ensure_allowed(self):
        if not self.is_allowed():
            raise StudyWindowClosed(f"当前不在允许学习时间内，允许时间：{self.describe()}")

    def seconds_until_next_window(self, now: Optional[datetime.datetime] = None) -> int:
        if not self.windows or self.is_allowed(now):
            return 0

        current = now or datetime.datetime.now()
        candidates = []
        for start, _ in self.windows:
            start_dt = datetime.datetime.combine(current.date(), start)
            if start_dt <= current:
                start_dt += datetime.timedelta(days=1)
            candidates.append(start_dt)

        return max(1, int((min(candidates) - current).total_seconds()))

    @staticmethod
    def _time_in_window(now_time: datetime.time, start: datetime.time, end: datetime.time) -> bool:
        if start <= end:
            return start <= now_time <= end
        return now_time >= start or now_time <= end

    @classmethod
    def _parse_windows(cls, windows) -> List[Tuple[datetime.time, datetime.time]]:
        if not windows:
            return []
        if isinstance(windows, str):
            chunks = re.split(r'[,，\n]+', windows)
            items = []
            for chunk in chunks:
                chunk = chunk.strip()
                if not chunk:
                    continue
                if '-' not in chunk:
                    raise ValueError(f"学习时间格式错误: {chunk}")
                start, end = chunk.split('-', 1)
                items.append((cls._parse_time(start), cls._parse_time(end)))
            return items
        parsed = []
        for item in windows:
            if isinstance(item, dict):
                start = item.get('start')
                end = item.get('end')
            else:
                start, end = item
            parsed.append((cls._parse_time(start), cls._parse_time(end)))
        return parsed

    @staticmethod
    def _parse_time(value) -> datetime.time:
        if isinstance(value, datetime.time):
            return value
        text = str(value).strip()
        for fmt in ('%H:%M', '%H:%M:%S'):
            try:
                return datetime.datetime.strptime(text, fmt).time()
            except ValueError:
                pass
        raise ValueError(f"时间格式错误: {value}，请使用 HH:MM")


class FileLock:
    """跨进程文件锁，用于保护题库文件写入"""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = open(self.path, 'w')
        with contextlib.suppress(ImportError):
            import fcntl
            fcntl.flock(self._handle, fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._handle:
            with contextlib.suppress(ImportError):
                import fcntl
                fcntl.flock(self._handle, fcntl.LOCK_UN)
            self._handle.close()


# ================ 工具函数（保持不变）================

def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """设置日志"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def hyperGeo_prob(N, A, n, x):
    """超几何分布概率计算 - 保持原函数"""
    choose_success = math.comb(A, x)
    choose_fail = math.comb(N - A, n - x)
    choose = math.comb(N, n)
    prob = choose_success * choose_fail / choose
    return prob


def binomial_prob(n, p, x):
    """二项分布概率计算 - 保持原函数"""
    prob = comb(n, x) * pow(p, x) * pow(1 - p, n - x)
    return prob


def get_sucess_number(sample_size=20, x_in_log=20, A=250, prio=0.99, prob=0.995, max_iter_number=1000):
    """计算成功次数 - 保持原函数"""
    N = ceil(A / prio)
    hyper_prob = hyperGeo_prob(N, A, sample_size, x_in_log)
    consec_no_new_questions_limit_update = 0
    en = binomial_prob(consec_no_new_questions_limit_update, hyper_prob,
                       consec_no_new_questions_limit_update)
    while consec_no_new_questions_limit_update <= max_iter_number and en > 1 - prob:
        consec_no_new_questions_limit_update += 1
        en = binomial_prob(consec_no_new_questions_limit_update, hyper_prob,
                           consec_no_new_questions_limit_update)
    return consec_no_new_questions_limit_update


# ================ 核心服务类 ================

class NetworkManager:
    """网络请求管理器 - 统一输出风格"""

    def __init__(self, headers: dict, cookies: dict, base_url: str = 'https://m.mynj.cn:11188'):
        self.headers = headers
        self.cookies = cookies
        self.base_url = base_url
        self.session = requests.Session()
        self.logger = setup_logger(self.__class__.__name__)

        # 测试网络连接
        self._test_connection()

    def _request_with_retry(self, method: str, url: str, retries: int = 3, retry_delay: int = 10, **kwargs) -> requests.Response:
        """带重试的网络请求，处理临时断网、超时等问题"""
        last_error = None
        for attempt in range(1, retries + 1):
            try:
                return self.session.request(method, url, verify=False, **kwargs)
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt >= retries:
                    break
                wait_seconds = retry_delay * attempt
                UIFormatter.print_formatted(
                    UIFormatter.status(
                        f"网络请求失败，{wait_seconds} 秒后重试 ({attempt}/{retries}): {e}",
                        "warning",
                        Icons.WARNING
                    )
                )
                time.sleep(wait_seconds)
        raise last_error

    def _test_connection(self):
        """测试网络连接 - 统一输出"""
        try:
            UIFormatter.print_formatted(
                UIFormatter.status("测试网络连接", "progress", Icons.GEAR)
            )
            response = self.session.get(f'{self.base_url}/zxpx/auc/myCourse?state=1&page=1',
                                        headers=self.headers,
                                        cookies=self.cookies,
                                        verify=False,
                                        timeout=10)
            if response.status_code == 200:
                UIFormatter.print_formatted(
                    UIFormatter.status("网络连接正常", "success", Icons.SHIELD)
                )
            elif response.status_code == 404:
                UIFormatter.print_formatted(
                    UIFormatter.status("网络连接正常", "success", Icons.SHIELD)
                )
            else:
                UIFormatter.print_formatted(
                    UIFormatter.status(f"网络连接状态: {response.status_code}", "warning")
                )
        except Exception as e:
            UIFormatter.print_formatted(
                UIFormatter.status(f"网络连接测试失败: {e}", "warning")
            )

    def get(self, endpoint: str, params: dict = None, **kwargs) -> requests.Response:
        """GET请求"""
        url = f"{self.base_url}{endpoint}"
        try:
            if 'timeout' not in kwargs:
                kwargs['timeout'] = 30
            retries = kwargs.pop('retries', 3)
            retry_delay = kwargs.pop('retry_delay', 10)

            response = self._request_with_retry(
                'GET', url, retries=retries, retry_delay=retry_delay,
                headers=self.headers, cookies=self.cookies,
                params=params, **kwargs
            )
            return response
        except Exception as e:
            self.logger.error(f"GET请求失败: {url}, 错误: {e}")
            raise NetworkException(f"GET请求失败: {e}")

    def post(self, endpoint: str, data: dict = None, **kwargs) -> requests.Response:
        """POST请求"""
        url = f"{self.base_url}{endpoint}"
        try:
            if 'timeout' not in kwargs:
                kwargs['timeout'] = 30
            retries = kwargs.pop('retries', 3)
            retry_delay = kwargs.pop('retry_delay', 10)

            response = self._request_with_retry(
                'POST', url, retries=retries, retry_delay=retry_delay,
                headers=self.headers, cookies=self.cookies,
                data=data, **kwargs
            )
            return response
        except Exception as e:
            self.logger.error(f"POST请求失败: {url}, 错误: {e}")
            raise NetworkException(f"POST请求失败: {e}")


class DataStorage:
    """数据存储管理器 - 保持原格式兼容"""

    def __init__(self, data_root: Path):
        self.data_root = data_root
        self.lock_folder = data_root / '.locks'
        self.logger = setup_logger(self.__class__.__name__)

    def _subject_lock(self, subject_title: str) -> FileLock:
        safe_name = re.sub(r'[^\w\u4e00-\u9fff.-]+', '_', subject_title)
        return FileLock(self.lock_folder / f'{safe_name}.lock')

    def save_question_data(self, subject_title: str, question_df: pd.DataFrame, answer_df: pd.DataFrame):
        """保存题目数据 - 保持原格式"""
        with self._subject_lock(subject_title):
            subject_folder = self.data_root / subject_title
            subject_folder.mkdir(exist_ok=True)

            excel_path = subject_folder / f'{subject_title}.xlsx'
            human_questionary_path = subject_folder / f'{subject_title}-human_questionary.txt'
            human_answer_path = subject_folder / f'{subject_title}-human_answer.txt'

            self._write_df_to_excel(excel_path, question_df, answer_df)
            self._write_human_file(human_questionary_path, question_df)
            self._write_human_file(human_answer_path, answer_df)

    def load_question_data(self, subject_title: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """加载题目数据 - 保持原格式"""
        with self._subject_lock(subject_title):
            excel_path = self.data_root / subject_title / f'{subject_title}.xlsx'
            return self._get_df_from_file(excel_path)

    def save_exam_result(self, subject_title: str, username: str, question_df: pd.DataFrame,
                         answer_df: pd.DataFrame, score: int, score_text: str):
        """保存考试结果 - 保持原格式"""
        with self._subject_lock(subject_title):
            subject_folder = self.data_root / subject_title
            subject_folder.mkdir(exist_ok=True)

            question_path = subject_folder / f'{username}_{subject_title}_问卷.txt'
            self._write_human_file(question_path, question_df)

            answer_path = subject_folder / f'{username}_{subject_title}_得分{score}_A.txt'
            self._write_human_file(answer_path, answer_df, score_text)

    def save_summary_file(self, subject_title: str, total_questions: int, text: str = ''):
        """保存汇总文件 - 保持原格式"""
        with self._subject_lock(subject_title):
            subject_folder = self.data_root / subject_title
            subject_folder.mkdir(exist_ok=True)
            summary_path = subject_folder / f'题目总数量：{total_questions}.txt'
            self._write_summary_file(summary_path, text)

    def check_question_bank_complete(self, subject_title: str) -> bool:
        """检查题库是否完整 - 保持原逻辑"""
        subject_folder = self.data_root / subject_title
        if not subject_folder.exists():
            return False

        txt_files = subject_folder.glob("*.txt")
        for txt_file in txt_files:
            if re.match(".*题目总数量.*", txt_file.stem):
                return True
        return False

    def _write_df_to_excel(self, path: Path, df_Q: pd.DataFrame, df_A: pd.DataFrame):
        """写入Excel - 保持原格式"""
        with pd.ExcelWriter(path) as writer:
            df_Q.to_excel(writer, index=False, sheet_name='Q')
            df_A.to_excel(writer, index=False, sheet_name='A')

    def _write_human_file(self, path: Path, df: pd.DataFrame, score_text: str = ''):
        """写入人读文件 - 保持原格式"""
        prev_type = None
        output_str = ''
        if len(score_text) > 0:
            output_str = score_text + '\n'

        for _, row in df.iterrows():
            question_type = row['type']
            question_text = row['title_text']
            options_lst = row['option_text']

            if question_type != prev_type:
                output_str += f"< {question_type} >\n"
                prev_type = question_type

            output_str += question_text + "\n"
            output_str = output_str + "\n".join(options_lst) + "\n"
            output_str += "\n"

        with open(path, 'w', encoding='utf-8') as f:
            f.write(output_str)

    def _write_summary_file(self, path: Path, text: str = ''):
        """写入汇总文件 - 保持原格式"""
        with open(path, 'w', encoding='utf-8') as f:
            if len(text) > 0:
                f.write(text + '\n')

    def _get_df_from_file(self, excel_path: Path) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        """从文件加载DataFrame - 保持原格式"""
        if not excel_path.exists():
            return None, None

        try:
            df_Q = pd.read_excel(excel_path, sheet_name='Q')
            df_A = pd.read_excel(excel_path, sheet_name='A')

            for df in [df_Q, df_A]:
                df['option_value'] = df['option_value'].apply(
                    lambda x: ast.literal_eval(x) if isinstance(x, str) else x
                )
                df['option_text'] = df['option_text'].apply(
                    lambda x: ast.literal_eval(x) if isinstance(x, str) else x
                )

            return df_Q, df_A
        except Exception as e:
            self.logger.error(f"加载数据文件失败: {excel_path}, 错误: {e}")
            return None, None


class CourseRepository:
    """课程数据仓库 - 统一输出风格"""

    def __init__(self, network_manager: NetworkManager):
        self.network = network_manager
        self.logger = setup_logger(self.__class__.__name__)

    def get_all_unfinished_courses(self) -> List[Course]:
        """获取所有未完成课程 - 统一输出"""
        unfinished_courses = []
        seen_courses = set()

        UIFormatter.print_formatted(
            UIFormatter.status("正在扫描课程列表", "progress", Icons.BOOK)
        )

        for state in [1, 0]:
            state_name = "进行中" if state == 1 else "未开始"
            page_num = 0
            consecutive_empty_pages = 0
            max_consecutive_empty = 3
            max_pages = 50

            while consecutive_empty_pages < max_consecutive_empty and page_num < max_pages:
                page_num += 1

                try:
                    response = self.network.get('/zxpx/auc/myCourse',
                                                params={'state': state, 'page': page_num},
                                                timeout=10)

                    if response.status_code != 200:
                        consecutive_empty_pages += 1
                        continue

                    courses = self._parse_course_page(response.text, state)

                    if not courses:
                        consecutive_empty_pages += 1
                        continue

                    page_course_count = 0
                    for course in courses:
                        course_key = (course.subject_title, course.ocid)
                        if course_key not in seen_courses:
                            unfinished_courses.append(course)
                            seen_courses.add(course_key)
                            page_course_count += 1

                    if page_course_count > 0:
                        consecutive_empty_pages = 0
                        UIFormatter.print_formatted(
                            UIFormatter.status(f"扫描{state_name}课程第{page_num}页", "progress"),
                            "    "
                        )
                    else:
                        consecutive_empty_pages += 1

                    time.sleep(0.5)

                except Exception as e:
                    self.logger.error(f"获取课程页面失败: state={state}, page={page_num}, 错误: {e}")
                    consecutive_empty_pages += 1

        UIFormatter.print_formatted(
            UIFormatter.status(f"扫描完成，找到 {len(unfinished_courses)} 门未完成课程", "success")
        )
        return unfinished_courses

    def get_unstarted_courses(self) -> List[Course]:
        """获取未开始的课程 - 保持原逻辑"""
        try:
            response = self.network.get('/zxpx/auc/myCourse?state=0')
            return self._parse_unstarted_course_page(response.text)
        except Exception as e:
            self.logger.error(f"获取未开始课程失败: {e}")
            return []

    def get_course_list(self, rt: str = '', year: int = 0, page: int = 1) -> Tuple[List[dict], int]:
        """获取课程列表 - 保持原逻辑和返回格式"""
        params = {
            "rt": rt,
            "cls": "",
            "ys": year,
            "tag": "",
            "odr": "time",
            "p": page
        }

        try:
            response = self.network.get('/zxpx/hyper/search/courselist', params=params)
            return self._parse_course_list_page(response.text)
        except Exception as e:
            self.logger.error(f"获取课程列表失败: {e}")
            return [], 0

    def _parse_course_page(self, html: str, state: int) -> List[Course]:
        """解析课程页面 - 保持原解析逻辑"""
        courses = []

        try:
            tree = etree.HTML(html)
            table_lst = tree.xpath('/html/body/div[1]/div/div/table')

            if not table_lst:
                return courses

            for table in table_lst:
                try:
                    texts = table.xpath('.//tr/td[1]/p//text()')
                    cleaned_texts = [text.strip() for text in texts if text.strip()]
                    subject_title = ''.join(cleaned_texts)

                    if not subject_title:
                        continue

                    href_elements = table.xpath('.//tr/td[7]/a/@href')
                    if not href_elements:
                        continue

                    href = href_elements[0]
                    ocid_matches = re.findall(r'ocid=(.+)', href)
                    if not ocid_matches:
                        continue

                    ocid = ocid_matches[0]

                    course = Course(
                        subject_title=subject_title,
                        ocid=ocid,
                        state=state
                    )
                    courses.append(course)

                except Exception as e:
                    continue

        except Exception as e:
            self.logger.error(f"解析课程页面失败: {e}")

        return courses

    def _parse_unstarted_course_page(self, html: str) -> List[Course]:
        """解析未开始课程页面 - 保持原格式"""
        courses = []
        ex = r"\('(.+)'\)"

        try:
            tree = etree.HTML(html)
            table_lst = tree.xpath('/html/body/div[1]/div/div/table')

            for table in table_lst:
                texts = table.xpath('.//tr/td[1]/p//text()')
                cleaned_texts = [text.strip() for text in texts if text.strip()]
                subject_title = ''.join(cleaned_texts)

                subject_type = table.xpath('.//tr/td[2]/text()')[0].strip()
                subject_teacher = table.xpath('.//tr/td[3]/text()')[0].strip()
                subject_credit = table.xpath('.//tr/td[4]/text()')[0].strip()
                subject_year = table.xpath('.//tr/td[5]/text()')[0].strip()
                cancel_href = table.xpath('.//tr/td[7]/a/@href')[-1]
                cancel_id = re.findall(ex, cancel_href)[0]

                course = Course(
                    subject_title=subject_title,
                    ocid="",
                    subject_type=subject_type,
                    subject_teacher=subject_teacher,
                    subject_credit=subject_credit,
                    subject_year=subject_year,
                    cancel_href=cancel_href,
                    cancel_id=cancel_id
                )
                courses.append(course)

        except Exception as e:
            self.logger.error(f"解析未开始课程失败: {e}")

        return courses

    def _parse_course_list_page(self, html: str) -> Tuple[List[dict], int]:
        """解析课程列表页面 - 保持原格式"""
        course_lst = []
        max_pages = 0

        try:
            tree = etree.HTML(html)
            if tree is None:
                return course_lst, max_pages

            li_list = tree.xpath("/html/body/div[2]/div/ul/li")
            ex = 'ocid=(.+?)&'

            for item in li_list:
                try:
                    title = item.xpath('./div[2]/div[1]/text()')
                    href = item.xpath('./div[2]/div[4]/div[2]/a/@href')
                    text = item.xpath('./div[2]/div[4]/div[2]/a/text()')
                    credit = item.xpath('./div[2]/div[3]/div[2]//span/text()')
                    if not title or not href or not text or not credit:
                        continue
                    ocid_match = re.findall(ex, href[0])
                    if not ocid_match:
                        continue
                    course_lst.append({
                        'title': title[0],
                        'href': href[0],
                        'text': text[0],
                        'credit': credit[0],
                        'ocid': ocid_match[0],
                    })
                except Exception:
                    continue

            total_courses_texts = tree.xpath('//*[@id="selection-order"]/li[1]/a/text()')
            if not total_courses_texts:
                return course_lst, max_pages

            ex = '（(\\d+)）'
            total_match = re.findall(ex, total_courses_texts[0])
            if not total_match:
                return course_lst, max_pages

            total_course_num = int(total_match[0])
            max_pages = math.ceil(total_course_num / 10) if total_course_num > 0 else 0

        except Exception as e:
            self.logger.error(f"解析课程列表页面失败: {e}")

        return course_lst, max_pages


class ChapterRepository:
    """章节数据仓库 - 统一输出风格"""

    def __init__(self, network_manager: NetworkManager):
        self.network = network_manager
        self.logger = setup_logger(self.__class__.__name__)

    def get_chapters_by_course(self, ocid: str) -> Tuple[List[Chapter], List[Chapter], List[Chapter]]:
        """获取课程章节信息 - 保持原格式"""
        reqtdate = round(time.time() * 1000)
        params = {'ocid': ocid, '_': reqtdate}

        try:
            response = self.network.get('/zxpx/course/chapterList', params=params)
            response_data = response.json()

            if not response_data.get('success', False):
                self.logger.error("获取章节列表失败")
                return [], [], []

            chapter_list = json.loads(response_data.get('resData', {}).get('chapterList', '[]'))
            return self._categorize_chapters(chapter_list)

        except Exception as e:
            self.logger.error(f"获取章节列表异常: {e}")
            return [], [], []

    def _categorize_chapters(self, chapter_data: List[dict]) -> Tuple[List[Chapter], List[Chapter], List[Chapter]]:
        """分类章节 - 保持原逻辑"""
        unfinished_chapters = []
        finished_chapters = []
        all_chapters = []

        for item in chapter_data:
            cpcwid = item.get('cpcwid')
            name = item.get('chaptername')
            hasstarted = item.get('hasstarted')

            chapter = Chapter(
                cpcwid=cpcwid,
                chaptername=name,
                hasstarted=int(hasstarted) if hasstarted is not None else 0
            )

            if item.get('type') == '3':
                all_chapters.append(chapter)

                if item.get('playfinished') != '1':
                    unfinished_chapters.append(chapter)
                else:
                    finished_chapters.append(chapter)

        for chapter_list in [unfinished_chapters, finished_chapters, all_chapters]:
            chapter_list.sort(key=lambda x: (-x.hasstarted, x.cpcwid))

        return unfinished_chapters, finished_chapters, all_chapters


class VideoLearningService:
    """视频学习服务 - 统一输出风格"""

    def __init__(self, network_manager: NetworkManager, delay_time: int = 30,
                 study_time_window: Optional[StudyTimeWindow] = None):
        self.network = network_manager
        self.delay_time = delay_time
        self.study_time_window = study_time_window or StudyTimeWindow()
        self.logger = setup_logger(self.__class__.__name__)

    def _ensure_study_time(self):
        self.study_time_window.ensure_allowed()

    def learn_course_videos(self, course: Course, course_index: int = 0, total_courses: int = 0,
                            completed_courses: int = 0, total_chapters: int = 0,
                            finished_chapter_count: int = 0) -> bool:
        """学习课程视频 - 统一输出格式"""
        self._ensure_study_time()
        chapter_repo = ChapterRepository(self.network)
        unfinished_chapters, finished_chapters, all_chapters = chapter_repo.get_chapters_by_course(course.ocid)

        total_chapters = len(all_chapters)  # 使用总章节数
        finished_chapter_count = len(finished_chapters)  # 已完成的章节数

        if len(unfinished_chapters) == 0:
            UIFormatter.print_formatted(
                UIFormatter.status("所有视频已完成", "success", Icons.CHECK),
                "    "
            )
            return True

        UIFormatter.print_formatted(
            UIFormatter.subsection(f"开始学习视频 ({len(unfinished_chapters)}个待学章节，共{total_chapters}章)",
                                   Icons.VIDEO),
            "  "
        )

        for index, chapter in enumerate(unfinished_chapters):
            self._ensure_study_time()
            chapter_name = chapter.chaptername
            current_chapter_index = finished_chapter_count + index + 1  # 当前章节在所有章节中的位置

            if course_index > 0 and total_courses > 0:
                # 章节开始时显示0%进度（本章节还未开始学习）
                # chapter_progress_bar = UIFormatter.progress_bar(0, 100, 30)  # 当前章节进度0%
                # chapter_progress_bar = ''
                # UIFormatter.print_formatted(
                #     f"    {chapter_progress_bar} 第{current_chapter_index}/{total_chapters}章: {chapter_name}",
                # )
                pass
            else:
                # 只显示章节信息
                UIFormatter.print_formatted(
                    UIFormatter.status(f"第{current_chapter_index}/{total_chapters}章: {chapter_name}", "progress",
                                       Icons.CIRCLE),
                    "    "
                )

            success, final_progress = self._learn_single_chapter(
                chapter, course_index, total_courses, current_chapter_index, total_chapters, completed_courses,
                finished_chapter_count
            )

            if success:
                # 章节完成后显示100%进度
                if course_index > 0 and total_courses > 0:
                    # 章节完成显示100%
                    chapter_progress_bar = UIFormatter.progress_bar(100, 100, 30)  # 当前章节完成100%
                    UIFormatter.print_formatted(
                        f"    {chapter_progress_bar} ✓ 章节完成: {chapter_name}",
                    )
                else:
                    UIFormatter.print_formatted(
                        UIFormatter.status(f"章节完成: {chapter_name}", "success", Icons.CHECK),
                        "      "
                    )
            else:
                UIFormatter.print_formatted(
                    UIFormatter.status(f"章节失败: {chapter_name} ({final_progress}%)", "error", Icons.CROSS),
                    "      "
                )
                return False

        UIFormatter.print_formatted(
            UIFormatter.status("视频学习完成", "success", Icons.SUCCESS),
            "    "
        )
        return True

    def _learn_single_chapter(self, chapter: Chapter, course_index: int = 0, total_courses: int = 0,
                              chapter_index: int = 0, total_chapters: int = 0, completed_courses: int = 0,
                              completed_chapters_in_current_course: int = 0) -> Tuple[bool, int]:
        """学习单个章节 - 返回成功状态和最终进度"""
        cpcwid = chapter.cpcwid

        try:
            self._ensure_study_time()
            self._visit_play_page(cpcwid)
            coursewareid = cpcwid

            watch_session = self._play_req(coursewareid)
            if not watch_session:
                return False, 0

            time.sleep(0.5)

            start_result = self._start_learning(coursewareid, watch_session)
            if not start_result:
                return False, 0

            reqt = start_result.get("reqt")
            progress = int(start_result.get("progress", 0))

            if not reqt:
                return False, progress
            chapter_progress_bar = UIFormatter.progress_bar(progress, 100, 30)
            UIFormatter.print_formatted(
                f"    {chapter_progress_bar} 第{chapter_index}/{total_chapters}章: {chapter.chaptername} ({progress}%)",
            )

            time.sleep(self.delay_time)
            finishit = 0

            # 持续学习
            while finishit == 0:
                self._ensure_study_time()
                loose_result = self._loose_learning(coursewareid, watch_session, reqt)
                if not loose_result:
                    return False, progress

                finishit = int(loose_result.get('finishit', 0))
                new_progress = int(loose_result.get('progress', 0))
                reqt = loose_result.get('reqt')

                if not reqt:
                    return False, progress

                # 更新章节内的学习进度显示 - 显示当前章节本身的学习进度
                if new_progress - progress > 0:
                    if course_index > 0 and total_courses > 0:
                        # 显示当前章节本身的学习进度（0-100%）
                        chapter_progress_bar = UIFormatter.progress_bar(new_progress, 100, 30)
                        UIFormatter.print_formatted(
                            f"    {chapter_progress_bar} 第{chapter_index}/{total_chapters}章: {chapter.chaptername} ({new_progress}%)",
                        )
                    else:
                        # 简单显示
                        UIFormatter.print_formatted(
                            UIFormatter.status(f"学习进度: {new_progress}%", "progress", Icons.CLOCK),
                            "        "
                        )
                    progress = new_progress

                time.sleep(self.delay_time)

            return True, 100

        except StudyWindowClosed:
            raise
        except Exception as e:
            self.logger.error(f"学习章节出错: {e}")
            return False, 0

    def _visit_play_page(self, cpcwid: str):
        """访问播放页面 - 保持原逻辑"""
        ex = '(.+\\d)\\D'
        courseid = re.findall(ex, cpcwid)[0]
        params = {'cpcwid': cpcwid, 'courseid': courseid}
        self.network.get('/zxpx/tec/play/player', params=params)

    def _play_req(self, coursewareid: str) -> Optional[str]:
        """播放请求 - 保持原逻辑"""
        data = {'_method': 'GET', 'coursewareid': coursewareid}

        try:
            response = self.network.post('/zxpx/tec/play/aj/playreq', data=data)
            response_json = response.json()

            if response_json.get('success'):
                return response_json['resData'].get('watchSession')
            else:
                UIFormatter.print_formatted(
                    UIFormatter.status(f"播放请求失败: {response_json.get('resMsg')}", "error"),
                    "      "
                )
                return None

        except Exception as e:
            self.logger.error(f"播放请求失败: {e}")
            return None

    def _start_learning(self, coursewareid: str, watch_session: str) -> Optional[dict]:
        """开始学习 - 保持原逻辑"""
        reqtdate = round(time.time() * 1000)
        ex = '(.+\\d)\\D'
        courseid = re.findall(ex, coursewareid)[0]

        data = {
            '_method': 'PUT',
            'courseid': courseid,
            'coursewareid': coursewareid,
            'watchSession': watch_session,
            'reqtdate': reqtdate,
            'startWatchTime': 0
        }

        try:
            response = self.network.post('/zxpx/tec/play/aj/start', data=data)
            response_json = response.json()

            if response_json.get('resMsg') is None:
                result = response_json['resData']
                result['currentTime'] = self.delay_time
                return result
            else:
                UIFormatter.print_formatted(
                    UIFormatter.status(f"开始学习失败: {response_json.get('resMsg')}", "error"),
                    "      "
                )
                return None

        except Exception as e:
            self.logger.error(f"开始学习失败: {e}")
            return None

    def _loose_learning(self, coursewareid: str, watch_session: str, reqt: str, current_time: int = 0) -> Optional[
        dict]:
        """持续学习 - 保持原逻辑"""
        reqtdate = round(time.time() * 1000)
        ex = '(.+\\d)\\D'
        courseid = re.findall(ex, coursewareid)[0]
        current_time += self.delay_time

        data = {
            '_method': 'PUT',
            'courseid': courseid,
            'coursewareid': coursewareid,
            'watchSession': watch_session,
            'reqtdate': reqtdate,
            'startWatchTime': current_time,
            'reqt': reqt
        }

        try:
            response = self.network.post('/zxpx/tec/play/aj/loose', data=data)
            response_json = response.json()

            if response_json.get('resMsg') is None:
                result = response_json['resData']
                result['currentTime'] = current_time + self.delay_time
                return result
            else:
                UIFormatter.print_formatted(
                    UIFormatter.status(f"持续学习失败: {response_json.get('resMsg')}", "error"),
                    "      "
                )
                return None

        except Exception as e:
            self.logger.error(f"持续学习失败: {e}")
            return None


class ExamService:
    """考试服务 - 统一输出风格"""

    def __init__(self, network_manager: NetworkManager, data_storage: DataStorage):
        self.network = network_manager
        self.storage = data_storage
        self.logger = setup_logger(self.__class__.__name__)

    def collect_questions(self, course: Course, username: str) -> bool:
        """收集题目 - 统一输出风格"""
        subject_title = course.subject_title
        ocid = course.ocid

        # 检查题库是否已完整
        if self.storage.check_question_bank_complete(subject_title):
            UIFormatter.print_formatted(
                UIFormatter.status("题库已完整，可以直接答题", "success", Icons.CHECK),
                "    "
            )
            return True

        # 获取章节信息
        chapter_repo = ChapterRepository(self.network)
        unfinished_chapters, finished_chapters, _ = chapter_repo.get_chapters_by_course(ocid)

        if len(unfinished_chapters) > 0:
            UIFormatter.print_formatted(
                UIFormatter.status("还有未学完的视频，无法收集题目", "warning", Icons.WARNING),
                "    "
            )
            return False

        if len(finished_chapters) == 0:
            UIFormatter.print_formatted(
                UIFormatter.status("没有已完成的章节", "warning", Icons.WARNING),
                "    "
            )
            return False

        UIFormatter.print_formatted(
            UIFormatter.subsection(f"开始收集题目", Icons.EXAM),
            "  "
        )

        # 访问播放页面获取用户名
        cpcwid = finished_chapters[0].cpcwid
        self._visit_play_page(cpcwid)

        # 获取试卷ID
        try:
            exid = self._parse_exam_id(ocid)
        except Exception as e:
            UIFormatter.print_formatted(
                UIFormatter.status(f"获取试卷ID失败: {e}", "error", Icons.CROSS),
                "    "
            )
            self.logger.error(f"获取试卷ID失败: {e}")
            return False

        # 加载已有数据
        Q_exist_df, A_exist_df = self.storage.load_question_data(subject_title)

        # 开始收集题目
        return self._collect_questions_loop(subject_title, exid, cpcwid, Q_exist_df, A_exist_df, username)

    def submit_final_exam(self, course: Course, username: str) -> bool:
        """提交最终考试 - 统一输出风格"""
        subject_title = course.subject_title
        ocid = course.ocid

        # 获取章节信息
        chapter_repo = ChapterRepository(self.network)
        unfinished_chapters, finished_chapters, _ = chapter_repo.get_chapters_by_course(ocid)

        if len(unfinished_chapters) > 0:
            UIFormatter.print_formatted(
                UIFormatter.status("还有未学完的视频，无法参加考试", "warning", Icons.WARNING),
                "    "
            )
            return False

        if len(finished_chapters) == 0:
            return False

        UIFormatter.print_formatted(
            UIFormatter.subsection(f"开始最终考试", Icons.EXAM),
            "  "
        )

        # 访问播放页面
        cpcwid = finished_chapters[0].cpcwid
        self._visit_play_page(cpcwid)

        # 获取试卷ID和答案
        try:
            exid = self._parse_exam_id(ocid)
            Q_exist_df, A_exist_df = self.storage.load_question_data(subject_title)

            if A_exist_df is None or A_exist_df.empty:
                UIFormatter.print_formatted(
                    UIFormatter.status("没有找到答案数据", "error", Icons.CROSS),
                    "    "
                )
                return False

            # 获取考卷
            exam_response = self._get_exam_paper(exid)
            saltkey, question_df = self._parse_exam(exam_response)

            if question_df is None or question_df.empty:
                # 重试一次
                self._visit_play_page(cpcwid)
                coursewareid = cpcwid
                watch_session = self._play_req(coursewareid)
                if watch_session:
                    self._start_learning_for_exam(coursewareid, watch_session)

                exam_response = self._get_exam_paper(exid)
                saltkey, question_df = self._parse_exam(exam_response)

            if question_df is None or question_df.empty:
                UIFormatter.print_formatted(
                    UIFormatter.status("无法获取考试题目", "error", Icons.CROSS),
                    "    "
                )
                return False

            # 生成答案并提交
            submit_answer_df, params = self._generate_answer_params(question_df, A_exist_df)

            UIFormatter.print_formatted(
                UIFormatter.status("正在提交考试答案", "progress", Icons.PROGRESS),
                "    "
            )

            # 交卷
            self._submit_exam(saltkey, exid, params)

            # 获取成绩
            feedback_text = self._get_exam_result(exid)
            score_text, score = self._parse_score(feedback_text)

            if score >= 60:
                UIFormatter.print_formatted(
                    UIFormatter.status(f"考试成功！{score_text}", "success", Icons.STAR),
                    "    "
                )
            else:
                UIFormatter.print_formatted(
                    UIFormatter.status(f"考试结果：{score_text}", "warning", Icons.WARNING),
                    "    "
                )

            # 保存考试结果
            self.storage.save_exam_result(subject_title, username, question_df,
                                          submit_answer_df, score, score_text)

            return True

        except Exception as e:
            UIFormatter.print_formatted(
                UIFormatter.status(f"最终考试失败: {e}", "error", Icons.CROSS),
                "    "
            )
            self.logger.error(f"最终考试失败: {e}")
            return False

    def _collect_questions_loop(self, subject_title: str, exid: str, cpcwid: str,
                                Q_exist_df: pd.DataFrame, A_exist_df: pd.DataFrame, username: str) -> bool:
        """收集题目循环 - 统一输出风格"""
        prio = 0.99
        prob = 0.995
        consec_no_new_questions = 0
        consec_no_new_questions_limit = 100
        i = 0

        UIFormatter.print_formatted(
            UIFormatter.status("开始题目收集循环", "progress", Icons.PROGRESS),
            "    "
        )

        while consec_no_new_questions < consec_no_new_questions_limit:
            i += 1
            UIFormatter.print_formatted(
                UIFormatter.status(f"第 {i} 次收集", "progress", Icons.CIRCLE),
                "      "
            )

            # 获取考卷
            exam_response = self._get_exam_paper(exid)
            saltkey, question_df = self._parse_exam(exam_response)

            if question_df is None or question_df.empty:
                # 看一次视频防止三次答题失败
                self._visit_play_page(cpcwid)
                coursewareid = cpcwid
                watch_session = self._play_req(coursewareid)
                if watch_session:
                    self._start_learning_for_exam(coursewareid, watch_session)

                exam_response = self._get_exam_paper(exid)
                saltkey, question_df = self._parse_exam(exam_response)

            if question_df is None or question_df.empty:
                continue

            # 扩展题目数据
            extended_Q_df = self._extend_dataframe(Q_exist_df, question_df)

            exist_num = Q_exist_df.shape[0] if Q_exist_df is not None else 0
            new_questions = extended_Q_df.shape[0] - exist_num

            UIFormatter.print_formatted(
                UIFormatter.status(f"新获得 {new_questions} 题，总量 {extended_Q_df.shape[0]} 题", "info", Icons.INFO),
                "        "
            )

            # 计算所需的连续未获得新题次数
            if question_df.shape[0] > 0:
                sample_size = question_df.shape[0]
                A = extended_Q_df.shape[0]
                consec_no_new_questions_limit = get_sucess_number(
                    sample_size=sample_size, x_in_log=sample_size, A=A, prio=prio, prob=prob
                )
                UIFormatter.print_formatted(
                    UIFormatter.status(f"需要连续 {consec_no_new_questions_limit} 次未获取新题目", "info", Icons.INFO),
                    "        "
                )

            if Q_exist_df is None or extended_Q_df.shape[0] != Q_exist_df.shape[0]:
                consec_no_new_questions = 0

                # 交白卷获取正确答案
                submit_answer_df, params = self._generate_answer_params(question_df)
                self._submit_exam(saltkey, exid, params)
                feedback_text = self._get_exam_result(exid)
                score_text, score = self._parse_score(feedback_text)

                UIFormatter.print_formatted(
                    UIFormatter.status(f"收集结果：{score_text}", "info", Icons.INFO),
                    "        "
                )

                # 解析正确答案
                right_answer_df = self._parse_right_answers(feedback_text)

                # 生成正确答案数据
                corrected_answer_df, _ = self._generate_answer_params(
                    submit_answer_df, right_answer_df, mode='check'
                )

                # 更新数据
                A_exist_df = self._extend_dataframe(A_exist_df, corrected_answer_df)
                Q_exist_df = extended_Q_df.copy()

                # 保存数据
                self.storage.save_question_data(subject_title, Q_exist_df, A_exist_df)

                # 如果意外及格，记录并返回
                if score >= 60:
                    self.storage.save_exam_result(subject_title, username, question_df,
                                                  submit_answer_df, score, score_text)
                    UIFormatter.print_formatted(
                        UIFormatter.status(f"意外及格！共跑了 {i} 次，得分 {score}", "warning", Icons.WARNING),
                        "      "
                    )
                    return False

            elif extended_Q_df.shape[0] == Q_exist_df.shape[0]:
                consec_no_new_questions += 1
                UIFormatter.print_formatted(
                    UIFormatter.status(
                        f"未找到新题目，连续第 {consec_no_new_questions}/{consec_no_new_questions_limit} 次", "progress",
                        Icons.CIRCLE),
                    "        "
                )

            time.sleep(5)

        UIFormatter.print_formatted(
            UIFormatter.status(f"题目收集完成！共跑了 {i} 次", "success", Icons.SUCCESS),
            "    "
        )

        # 保存汇总文件
        summary_text = f'当前题目数量 {Q_exist_df.shape[0]}，连续 {consec_no_new_questions_limit} 次未获取到新题目，有 {100 * prob}% 的可能性获取了 {100 * prio}% 的题目。'
        self.storage.save_summary_file(subject_title, Q_exist_df.shape[0], summary_text)

        return True

    # 保持所有原有的私有方法不变，只在关键地方统一输出
    def _parse_exam_id(self, ocid: str) -> str:
        """解析考试ID - 保持原逻辑"""
        params = {'ocid': ocid}
        response = self.network.get('/zxpx/hyper/courseDetail', params=params)
        ex = '=(EX.+?)&'
        exid = re.findall(ex, response.text)[0]
        return exid

    def _get_exam_paper(self, exid: str) -> requests.Response:
        """获取试卷 - 保持原逻辑"""
        params = {'exid': exid}
        return self.network.get('/zxpx/auc/courseExam', params=params)

    def _parse_exam(self, response: requests.Response) -> Tuple[str, Optional[pd.DataFrame]]:
        """解析试卷 - 保持原逻辑"""
        question_list = []

        try:
            tree = etree.HTML(response.text)

            # 获取saltkey
            saltkey = tree.xpath('//input[@name="saltkey"]/@value')[0]

            exam_type_tree_lst = tree.xpath('//div[@class="exam-subject-panel"]/div')

            for exam_type in exam_type_tree_lst:
                type_text = exam_type.xpath('./div[1]/text()')[0]
                ex = '(.+)（'
                question_type = re.findall(ex, type_text)[0]

                item_lst = exam_type.xpath('./div[2]/div')
                for item in item_lst:
                    title_lst = item.xpath('./div[@class="exam-subject-text-que"]/div[1]//text()')
                    title = ''.join([t.strip() for t in title_lst])

                    ex = '\\d+、'
                    title_text = re.sub(ex, '', title)

                    title_id = item.xpath('./div[@class="exam-subject-text-quecontent"]//input[1]/@name')[0]
                    option_value = item.xpath('./div[@class="exam-subject-text-quecontent"]//input[1]/@value')
                    option_text = item.xpath('./div[@class="exam-subject-text-quecontent"]//div/text()')
                    option_text = [x.strip() for x in option_text]

                    question = {
                        'type': question_type,
                        'title_text': title_text,
                        'title_id': title_id,
                        'option_value': option_value,
                        'option_text': option_text
                    }
                    question_list.append(question)

            question_list.sort(key=lambda item: item.get('type'))
            question_df = pd.DataFrame(question_list)
            return saltkey, question_df

        except Exception as e:
            try:
                response_json = response.json()
                UIFormatter.print_formatted(
                    UIFormatter.status(f"解析试卷失败: {response_json.get('resMsg')}", "error", Icons.CROSS),
                    "      "
                )
            except:
                self.logger.error(f"解析试卷失败: {e}")
            return '', None

    def _generate_answer_params(self, question_df: pd.DataFrame, answer_df: pd.DataFrame = None,
                                mode: str = '') -> Tuple[pd.DataFrame, str]:
        """生成答案参数 - 保持原逻辑"""
        index = 1

        if answer_df is None or answer_df.empty:
            # 返回白卷
            merged_df = question_df.copy()
            merged_df['option_value'] = merged_df['option_value'].apply(lambda x: x[0:index])
            merged_df['option_text'] = merged_df['option_text'].apply(lambda x: x[0:index])
        else:
            # 根据答案返回正确答案
            if mode == 'check':
                index = None

            columns = question_df.columns
            merged_df = pd.merge(question_df, answer_df, on=['title_text', 'type'],
                                 how='left', suffixes=('', '_answer'))

            # 填充缺失值
            merged_df['option_value'] = merged_df['option_value_answer'].fillna(
                merged_df['option_value'].apply(lambda x: x[0:index])
            )
            merged_df['option_text'] = merged_df['option_text_answer'].fillna(
                merged_df['option_text'].apply(lambda x: x[0:index])
            )

            merged_df = merged_df[columns]

        # 生成提交参数
        merged_df['params'] = merged_df.apply(
            lambda row: '&'.join([f'{row["title_id"]}={elem}' for elem in row['option_value'][0:]]),
            axis=1
        )
        params = '&' + '&'.join(merged_df['params'])
        merged_df.drop('params', axis=1, inplace=True)

        return merged_df, params

    def _submit_exam(self, saltkey: str, exid: str, params: str):
        """提交考试 - 保持原逻辑"""
        data = f'saltkey={saltkey}&exid={exid}{params}'
        self.network.post('/zxpx/auc/examination/regexexam', data=data)

    def _get_exam_result(self, exid: str) -> str:
        """获取考试结果 - 保持原逻辑"""
        params = {'exid': exid}
        response = self.network.get('/zxpx/auc/examination/subexam', params=params)
        return response.text

    def _parse_score(self, feedback_text: str) -> Tuple[str, int]:
        """解析分数 - 保持原逻辑"""
        try:
            tree = etree.HTML(feedback_text)
            score_text = tree.xpath('//div[@class="exam-message-question"]/text()')[0]
            score = int(re.search(r'\d+', score_text).group())
            return score_text, score
        except:
            return '', 0

    def _parse_right_answers(self, feedback_text: str) -> pd.DataFrame:
        """解析正确答案 - 保持原逻辑"""
        tree = etree.HTML(feedback_text)
        exam_type_tree_lst = tree.xpath('//div[@class="exam-subject-panel"]/div')
        right_answer_list = []

        for exam_type in exam_type_tree_lst:
            type_text = exam_type.xpath('./div[1]/text()')[0]
            ex = '(.+)（'
            question_type = re.findall(ex, type_text)[0]

            item_lst = exam_type.xpath('./div[2]/div')
            for item in item_lst:
                title_lst = item.xpath('./div[@class="exam-subject-text-que"]/div[1]//text()')
                title = ''.join([t.strip() for t in title_lst])
                ex = '\\d+、'
                title_text = re.sub(ex, '', title)

                right_answer_lst = item.xpath('./div[@class="exam-subject-text-quecontent"]/div[2]/text()')
                option_text = list(filter(
                    lambda i: len(i) > 0,
                    [x.strip().replace('正确答案：', '') for x in right_answer_lst]
                ))
                option_value = [x[0] if re.match('[A-F]', x) else '0' for x in option_text]

                answer = {
                    'type': question_type,
                    'title_text': title_text,
                    'title_id': '',
                    'option_value': option_value,
                    'option_text': option_text
                }
                right_answer_list.append(answer)

        right_answer_list.sort(key=lambda item: item.get('type'))
        return pd.DataFrame(right_answer_list)

    def _extend_dataframe(self, existing_df: pd.DataFrame, new_df: pd.DataFrame,
                          key_column: str = 'title_text') -> pd.DataFrame:
        """扩展DataFrame - 保持原逻辑"""
        if existing_df is None:
            existing_df = pd.DataFrame()
        if new_df is None:
            new_df = pd.DataFrame()

        updated_df = pd.concat([existing_df, new_df])
        updated_df.drop_duplicates(key_column, keep='first', inplace=True)
        updated_df.sort_values('type', inplace=True)

        return updated_df

    def _visit_play_page(self, cpcwid: str):
        """访问播放页面 - 保持原逻辑"""
        ex = '(.+\\d)\\D'
        courseid = re.findall(ex, cpcwid)[0]
        params = {'cpcwid': cpcwid, 'courseid': courseid}
        self.network.get('/zxpx/tec/play/player', params=params)

    def _play_req(self, coursewareid: str) -> Optional[str]:
        """播放请求 - 保持原逻辑"""
        data = {'_method': 'GET', 'coursewareid': coursewareid}

        try:
            response = self.network.post('/zxpx/tec/play/aj/playreq', data=data)
            response_json = response.json()

            if response_json.get('success'):
                return response_json['resData'].get('watchSession')
            return None
        except:
            return None

    def _start_learning_for_exam(self, coursewareid: str, watch_session: str):
        """为考试开始学习 - 保持原逻辑"""
        reqtdate = round(time.time() * 1000)
        ex = '(.+\\d)\\D'
        courseid = re.findall(ex, coursewareid)[0]

        data = {
            '_method': 'PUT',
            'courseid': courseid,
            'coursewareid': coursewareid,
            'watchSession': watch_session,
            'reqtdate': reqtdate,
            'startWatchTime': 0
        }

        try:
            self.network.post('/zxpx/tec/play/aj/start', data=data)
        except:
            pass


class CourseManager:
    """课程管理服务 - 统一输出风格"""

    def __init__(self, network_manager: NetworkManager):
        self.network = network_manager
        self.logger = setup_logger(self.__class__.__name__)

    def add_courses(self, rt: str = '', year: int = 0, credit: float = 0.0):
        """添加课程 - 统一输出风格"""
        course_repo = CourseRepository(self.network)

        UIFormatter.print_formatted(
            UIFormatter.section("开始批量添加课程", Icons.PLUS)
        )

        # 获取所有页面的课程
        total_course_lst = []
        UIFormatter.print_formatted(
            UIFormatter.status("正在获取课程列表", "progress", Icons.PROGRESS)
        )

        course_lst, max_pages = course_repo.get_course_list(rt=rt, year=year, page=1)
        total_course_lst.extend(course_lst)

        if max_pages == 0 and not total_course_lst:
            UIFormatter.print_formatted(
                UIFormatter.status(f"{year} 年没有找到可添加的课程", "warning", Icons.WARNING)
            )
            return

        for p in range(2, max_pages + 1):
            course_lst, _ = course_repo.get_course_list(rt=rt, year=year, page=p)
            total_course_lst.extend(course_lst)
            UIFormatter.print_formatted(
                UIFormatter.status(f"正在扫描第 {p}/{max_pages} 页", "progress", Icons.CIRCLE),
                "  "
            )

        # 筛选未学习的课程
        un_study_course_lst = [item for item in total_course_lst if item.get('text') == '进入选课']
        total_credit = sum(float(x.get('credit', 0)) for x in un_study_course_lst)

        UIFormatter.print_formatted(
            UIFormatter.status(f"可选课数量: {len(un_study_course_lst)}，总学时: {total_credit}", "info", Icons.INFO)
        )

        # 添加课程
        added_credit = 0
        added_num = 0

        UIFormatter.print_formatted(
            UIFormatter.subsection("开始添加课程", Icons.PLUS)
        )

        for item in un_study_course_lst:
            if added_credit >= credit:
                break

            ocid = item.get('ocid')
            data = {'ocid': ocid}

            try:
                response = self.network.post('/zxpx/auc/shopcart/good', data=data)
                response_json = response.json()

                if response_json.get('success'):
                    added_num += 1
                    added_credit += float(item.get("credit", 0))
                    UIFormatter.print_formatted(
                        UIFormatter.status(f'已添加: {item.get("title")} (学时: {item.get("credit")})', "success",
                                           Icons.CHECK),
                        "  "
                    )
                else:
                    UIFormatter.print_formatted(
                        UIFormatter.status(f'{item.get("title")}: {response_json.get("resMsg")}', "warning",
                                           Icons.WARNING),
                        "  "
                    )

            except Exception as e:
                UIFormatter.print_formatted(
                    UIFormatter.status(f"添加课程失败: {e}", "error", Icons.CROSS)
                )
                self.logger.error(f"添加课程失败: {e}")
                return

        # 显示添加结果
        stats = {
            "已添加课程数": added_num,
            "累计学时": added_credit,
            "目标学时": credit,
            "完成率": f"{(added_credit / credit * 100):.1f}" if credit > 0 else "100.0"
        }

        UIFormatter.print_formatted(
            UIFormatter.statistics_summary("课程添加统计", stats)
        )

    def cancel_all_courses(self):
        """取消所有课程 - 统一输出风格"""
        course_repo = CourseRepository(self.network)

        UIFormatter.print_formatted(
            UIFormatter.section("开始取消所有未开始课程", Icons.MINUS)
        )

        unstarted_courses = course_repo.get_unstarted_courses()

        if not unstarted_courses:
            UIFormatter.print_formatted(
                UIFormatter.status("没有找到未开始的课程", "info", Icons.INFO)
            )
            return

        UIFormatter.print_formatted(
            UIFormatter.status(f"找到 {len(unstarted_courses)} 门未开始课程", "info", Icons.INFO)
        )

        i = 0
        credit = 0

        try:
            while unstarted_courses:
                for course in unstarted_courses:
                    data = {"stucouid": course.cancel_id}

                    try:
                        response = self.network.post('/zxpx//auc/mycourse/cancelCourse', data=data)
                        response_json = response.json()

                        if response_json.get("success"):
                            UIFormatter.print_formatted(
                                UIFormatter.status(
                                    f'{response_json["resMsg"]}: {course.subject_title} ({course.subject_credit}学时)',
                                    "success", Icons.CHECK),
                                "  "
                            )
                            i += 1
                            credit += float(course.subject_credit)

                    except Exception as e:
                        UIFormatter.print_formatted(
                            UIFormatter.status(f"取消课程失败: {e}", "error", Icons.CROSS),
                            "  "
                        )
                        self.logger.error(f"取消课程失败: {e}")

                unstarted_courses = course_repo.get_unstarted_courses()

        except Exception as e:
            UIFormatter.print_formatted(
                UIFormatter.status(f"取消课程过程出错: {e}", "error", Icons.CROSS)
            )
            self.logger.error(f"取消课程过程出错: {e}")

        # 显示取消结果
        stats = {
            "已取消课程数": i,
            "释放学时": credit
        }

        UIFormatter.print_formatted(
            UIFormatter.statistics_summary("课程取消统计", stats)
        )


class LoginManager:
    """登录管理器 - 统一输出风格"""

    def __init__(self):
        self.UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36'
        self.logger = setup_logger(self.__class__.__name__)

    def login_zxpx(self, url_zxpx: str) -> Tuple[dict, dict]:
        """登录在线培训 - 统一输出风格"""
        headers = {
            'User-Agent': self.UA,
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }
        cookies = {}
        session = requests.session()

        # 生成随机JSESSIONID
        lst = ['A', 'B', 'C', 'D', 'E', 'F', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
        jsessionid = ''.join(random.choice(lst) for _ in range(32))
        cookies.update({'JSESSIONID': jsessionid})

        try:
            response = session.get(url=url_zxpx, headers=headers, cookies=cookies, verify=False)
            cookies.update(dict(response.history[0].cookies))
            return headers, cookies
        except Exception as e:
            UIFormatter.print_formatted(
                UIFormatter.status(f'登录失败: {e}', "error", Icons.CROSS)
            )
            self.logger.error(f'登录失败: {e}')
            raise LoginException(f'登录失败: {e}')


# ================ 主类 ================

class AutoStudyRefactored:
    """重构后的自动学习主类 - 统一输出风格"""

    def __init__(self, data_folder: Path, username: str = '我是谁？', url_zxpx: str = '',
                 study_time_window: Optional[Union[StudyTimeWindow, str, List[dict], List[Tuple[str, str]]]] = None):
        self.username = username
        self.data_folder = data_folder
        self.delay_time = 30
        self.study_time_window = study_time_window if isinstance(study_time_window, StudyTimeWindow) else StudyTimeWindow(study_time_window)
        self.logger = setup_logger(self.__class__.__name__)

        UIFormatter.print_formatted(
            UIFormatter.status(f'正在初始化 {username} 的学习环境', "progress", Icons.GEAR)
        )

        try:
            # 初始化登录
            UIFormatter.print_formatted(
                UIFormatter.status('正在登录认证', "progress", Icons.SHIELD)
            )
            login_manager = LoginManager()
            headers, cookies = login_manager.login_zxpx(url_zxpx)

            if not headers or not cookies:
                raise LoginException("登录失败：无法获取认证信息")

            UIFormatter.print_formatted(
                UIFormatter.status('登录成功，正在初始化服务', "progress", Icons.GEAR)
            )

            # 初始化服务
            self.network = NetworkManager(headers, cookies)
            self.storage = DataStorage(data_folder)
            self.course_repo = CourseRepository(self.network)
            self.video_service = VideoLearningService(self.network, self.delay_time, self.study_time_window)
            self.exam_service = ExamService(self.network, self.storage)
            self.course_manager = CourseManager(self.network)

            UIFormatter.print_formatted(
                UIFormatter.success(f'欢迎 {self.username}！初始化完成', Icons.STAR)
            )

        except Exception as e:
            UIFormatter.print_formatted(
                UIFormatter.error(f'初始化失败: {e}', Icons.CROSS)
            )
            self.logger.error(f'初始化失败: {e}')
            raise

    def all_in_one(self, finish_exam: bool = True):
        """一键学习所有课程 - 统一输出格式"""
        start_time = time.time()

        try:
            UIFormatter.print_formatted(UIFormatter.header("🎓 自动学习系统", "═", 70))

            # 显示模式
            mode_text = "📚 观看视频 + 📝 参加考试" if finish_exam else "📚 仅观看视频"
            UIFormatter.print_formatted(UIFormatter.info(f"学习模式: {mode_text}"))
            UIFormatter.print_formatted(UIFormatter.info(f"学员: {self.username}"))
            if self.study_time_window.enabled():
                UIFormatter.print_formatted(UIFormatter.info(f"允许学习时间: {self.study_time_window.describe()}"))
                self.study_time_window.ensure_allowed()

            # 获取课程列表
            UIFormatter.print_formatted(UIFormatter.section("获取课程信息", Icons.BOOK))
            unfinished_courses = self.course_repo.get_all_unfinished_courses()
            total_courses = len(unfinished_courses)

            if total_courses == 0:
                UIFormatter.print_formatted(
                    UIFormatter.success("所有课程都已完成！恭喜！", Icons.STAR)
                )
                return

            # 显示课程摘要
            UIFormatter.print_formatted(
                UIFormatter.info(f'找到 {total_courses} 门未完成课程')
            )

            # 简洁显示课程列表
            UIFormatter.print_formatted(UIFormatter.subsection("课程列表预览", Icons.FOLDER))
            for i, course in enumerate(unfinished_courses[:5]):
                course_title = course.subject_title
                if len(course_title) > 50:
                    course_title = course_title[:47] + "..."
                UIFormatter.print_formatted(
                    UIFormatter.numbered_item(i + 1, course_title),
                    "  "
                )

            if total_courses > 5:
                UIFormatter.print_formatted(
                    UIFormatter.status(f"... 还有 {total_courses - 5} 门课程", "info", Icons.DOT),
                    "  "
                )

            success_count = 0

            # 开始学习
            UIFormatter.print_formatted(UIFormatter.section("开始学习课程", Icons.ROCKET))

            for index, course in enumerate(unfinished_courses):
                self.study_time_window.ensure_allowed()
                subject_title = course.subject_title

                # 计算当前课程的初始进度
                chapter_repo = ChapterRepository(self.network)
                unfinished_chapters, finished_chapters, all_chapters = chapter_repo.get_chapters_by_course(course.ocid)
                total_chapters = len(all_chapters)
                finished_chapter_count = len(finished_chapters)

                # 课程初始进度 = 已完成章节 / 总章节
                initial_course_progress = finished_chapter_count / total_chapters if total_chapters > 0 else 0

                # 显示课程开始时的进度条
                overall_progress = (success_count + initial_course_progress) / total_courses
                course_progress = UIFormatter.progress_bar(int(overall_progress * 100), 100, 30)
                UIFormatter.print_formatted(
                    f"{course_progress} {UIFormatter.numbered_item(index + 1, subject_title, total_courses)}"
                )

                try:
                    # 观看视频 - 传递更多参数用于实时进度更新
                    video_success = self.video_service.learn_course_videos(
                        course, index + 1, total_courses, success_count, total_chapters, finished_chapter_count
                    )

                    if finish_exam and video_success:
                        # 收集题目
                        UIFormatter.print_formatted(
                            UIFormatter.subsection("收集考试题目", Icons.EXAM),
                            "  "
                        )
                        questions_collected = self.exam_service.collect_questions(course, self.username)

                        # 最终考试
                        if questions_collected:
                            UIFormatter.print_formatted(
                                UIFormatter.subsection("参加最终考试", Icons.EXAM),
                                "  "
                            )
                            exam_success = self.exam_service.submit_final_exam(course, self.username)
                            if exam_success:
                                success_count += 1
                                # 显示完成状态的课程进度 - 课程完成时显示100%
                                final_progress = UIFormatter.progress_bar(100, 100, 30)  # 课程完成显示100%
                                UIFormatter.print_formatted(
                                    f"{final_progress} {UIFormatter.success('课程学习完成', Icons.STAR)}"
                                )
                            else:
                                UIFormatter.print_formatted(
                                    UIFormatter.error('考试失败', Icons.CROSS),
                                    "  "
                                )
                        else:
                            UIFormatter.print_formatted(
                                UIFormatter.warning('题目收集失败', Icons.WARNING),
                                "  "
                            )
                    elif video_success:
                        success_count += 1
                        # 显示完成状态的课程进度 - 课程完成时显示100%
                        final_progress = UIFormatter.progress_bar(100, 100, 30)  # 课程完成显示100%
                        UIFormatter.print_formatted(
                            f"{final_progress} {UIFormatter.success('视频学习完成', Icons.CHECK)}"
                        )
                    else:
                        UIFormatter.print_formatted(
                            UIFormatter.error('视频学习失败', Icons.CROSS),
                            "  "
                        )

                except StudyWindowClosed:
                    raise
                except Exception as e:
                    UIFormatter.print_formatted(
                        UIFormatter.error(f'处理出错: {str(e)[:50]}...', Icons.FAILURE),
                        "  "
                    )
                    self.logger.error(f'处理课程失败: {e}')
                    continue

                # 显示分隔线
                UIFormatter.print_formatted(
                    UIFormatter.divider()
                )

            # 显示最终统计
            elapsed_time = time.time() - start_time
            hours = int(elapsed_time // 3600)
            minutes = int((elapsed_time % 3600) // 60)
            time_text = f"{hours}h{minutes}m" if hours > 0 else f"{minutes}m"

            success_rate = (success_count * 100) / total_courses if total_courses > 0 else 0

            stats = {
                "总课程数": total_courses,
                "完成课程数": success_count,
                "成功率": success_rate,
                "用时": time_text
            }

            UIFormatter.print_formatted(UIFormatter.header("📊 学习统计", "─", 50))
            UIFormatter.print_formatted(UIFormatter.statistics_summary("最终统计", stats))

            if success_count == total_courses:
                UIFormatter.print_formatted(
                    UIFormatter.success("🎉 所有课程学习完成！", Icons.STAR)
                )
            else:
                failed = total_courses - success_count
                UIFormatter.print_formatted(
                    UIFormatter.warning(f"还有 {failed} 门课程需要处理", Icons.WARNING)
                )

        except StudyWindowClosed:
            raise
        except Exception as e:
            UIFormatter.print_formatted(
                UIFormatter.error(f"自动学习过程出错: {e}", Icons.FAILURE)
            )
            self.logger.error(f'自动学习失败: {e}')
            raise

    def add_course(self, rt: str = '', year: int = 0, credit: float = 0.0):
        """添加课程"""
        self.course_manager.add_courses(rt, year, credit)

    def cancel_all_course(self):
        """取消所有课程"""
        self.course_manager.cancel_all_courses()


# ================ 用户管理和主程序 ================

def _encode_write(username: str = '', text: str = '', path: Path = Path('./autolearn.key')) -> bool:
    """编码写入用户信息 - 保持原逻辑"""
    lst = ['A', 'B', 'C', 'D', 'E', 'F', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    params = re.findall('params=(.+)', text)[0]
    rst = ''.join(random.choice(lst) + i for i in params)

    dic = {'username': username, 'params': rst}

    try:
        with open(path, 'w') as f:
            json.dump(obj=dic, fp=f, ensure_ascii=False)
        return True
    except:
        return False


def _decode_read(path: Path) -> Tuple[str, str]:
    """解码读取用户信息 - 保持原逻辑"""
    with open(path, 'r', encoding='utf-8') as f:
        line = json.load(f)

    params = line.get('params')[1::2]
    rst = 'https://m.mynj.cn:11188/zxpx/login?params=' + params

    return line['username'], rst


def _login(authCode: str = '') -> Tuple[str, str]:
    """通过authCode登录 - 统一输出风格"""
    UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36'
    headers = {
        'User-Agent': UA,
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br'
    }
    session = requests.session()
    cookies = {}

    # 登录 11097
    strEnc = None
    i = 1
    while strEnc is None and i <= 5:
        UIFormatter.print_formatted(
            UIFormatter.status(f'第 {i} 次登录尝试', "progress", Icons.PROGRESS)
        )
        url_1 = 'https://m.mynj.cn:11097/commlogin/'
        try:
            response = session.get(url=url_1, headers=headers, verify=False)
            cookies.update(dict(response.cookies))
        except Exception as e:
            UIFormatter.print_formatted(
                UIFormatter.status(f'登录请求失败: {e}', "error", Icons.CROSS)
            )

        data = {'formdata': '{"authCode":"' + authCode + '"}'}
        url_2 = 'https://m.mynj.cn:11097/plateform/jumpLogin/getTokenAndUserInfo'
        response = session.post(url=url_2, headers=headers, cookies=cookies, data=data, verify=False)
        strEnc = response.json().get("strEnc")
        i += 1
        time.sleep(1)

    if not strEnc:
        UIFormatter.print_formatted(
            UIFormatter.error('登录不成功！请重新获取 authCode', Icons.CROSS)
        )
        return '', ''

    UIFormatter.print_formatted(
        UIFormatter.success(f'获取到认证令牌: {strEnc[:20]}...', Icons.CHECK)
    )

    # 跳转到 11096 拿 cookie
    url_3 = f'https://m.mynj.cn:11096/njwsbs/index.do?method=showToken&token={strEnc}'
    response = session.get(url=url_3, headers=headers, cookies=cookies, verify=False)
    for history in response.history:
        cookies.update(dict(history.cookies))

    # 跳转到 11188 拿 cookie
    url_4 = 'https://m.mynj.cn:11188/zjjyweb/resource/menus.do'
    response = session.get(url=url_4, headers=headers, cookies=cookies, verify=False)
    co = response.headers['Set-Cookie']
    ex = 'JSESSIONID=(.+?);'
    cookies.update({'JSESSIONID': re.findall(ex, co)[0]})

    # 生成跳转到 11188 的网址
    url_5 = 'https://m.mynj.cn:11096/njwsbs/index.do?method=toZjjxjy'
    response = session.get(url=url_5, headers=headers, cookies=cookies, verify=False)

    # 拿到 username
    url_6 = 'https://m.mynj.cn:11188/zjjyweb/user/index.do'
    response = session.get(url=url_6, headers=headers, cookies=cookies, verify=False)
    tree = etree.HTML(response.text)
    username = tree.xpath('//body[@class="easyui-layout"]//a/font/text()')[0].strip()

    # 拿到最终的学习登录网址
    url_7 = 'https://m.mynj.cn:11188/zjjyweb/user/freelogin/to.do'
    response = session.get(url=url_7, headers=headers, cookies=cookies, verify=False)
    ex = "(?<!//)top.location.href='(.+)'"
    url_zxpx = re.findall(ex, response.text)[0]

    UIFormatter.print_formatted(
        UIFormatter.success(f'{username} 登录成功！', Icons.STAR)
    )
    return username, url_zxpx


def create_new_atl(path: Path) -> bool:
    """创建新的ATL文件 - 统一输出风格"""
    UIFormatter.print_formatted(UIFormatter.header("🔐 创建新用户", "═", 50))

    entry_url = 'https://m.mynj.cn:11097/'
    jump_url = 'https://m.mynj.cn:11097/plateform/rediectIndex/goods?authCode=XXXXXXX'

    UIFormatter.print_formatted(UIFormatter.section("获取认证码步骤", Icons.INFO))
    UIFormatter.print_formatted(UIFormatter.numbered_item(1, f"先进入 {entry_url}"))
    UIFormatter.print_formatted(UIFormatter.numbered_item(2, f"登陆后跳转到 {jump_url}"))
    UIFormatter.print_formatted(UIFormatter.numbered_item(3, '复制 "authCode=" 后面所有的字符 "XXXXXXX"'))
    UIFormatter.print_formatted(UIFormatter.numbered_item(4, '在下面粘贴第 3 步复制下来的 "XXXXXXX"'))

    authCode = input(UIFormatter.input_prompt("请输入authCode", icon=Icons.ARROW))

    UIFormatter.print_formatted(UIFormatter.section("正在验证认证码", Icons.SHIELD))
    username, url_zxpx = _login(authCode=authCode)

    if username and url_zxpx:
        if _encode_write(username=username, text=url_zxpx, path=path / f'{username}.atl'):
            UIFormatter.print_formatted(
                UIFormatter.success(f"新学员 {username}.atl 创建成功！", Icons.STAR)
            )
        else:
            UIFormatter.print_formatted(
                UIFormatter.error(f"新学员 {username}.atl 创建不成功！", Icons.CROSS)
            )
        return True
    else:
        return False


def add_course_menu() -> Tuple[str, int, float]:
    """添加课程菜单 - 统一输出风格"""
    quit_lst = ['q', 'Q']
    none_return = ('', 0, 0)
    type_dic = {
        '0': '',  # 全部
        '1': 'CT2017110000000074',  # 公需课
        '2': 'CT2017110000000075',  # 知识更新工程专题
    }

    UIFormatter.print_formatted(UIFormatter.header("📚 添加课程设置", "═", 50))

    while True:
        UIFormatter.print_formatted(UIFormatter.section("选择课程类型", Icons.BOOK))
        UIFormatter.print_formatted(UIFormatter.menu_item('0', '全部'))
        UIFormatter.print_formatted(UIFormatter.menu_item('1', '公需课'))
        UIFormatter.print_formatted(UIFormatter.menu_item('2', '知识更新工程专题'))
        UIFormatter.print_formatted(UIFormatter.menu_item('q', '退出'))

        choice = input(UIFormatter.input_prompt("请输入类型", "全部"))

        if choice == '':
            course_type = type_dic.get('0')
        elif choice in type_dic.keys():
            course_type = type_dic[choice]
        elif choice in quit_lst:
            return none_return
        else:
            UIFormatter.print_formatted(
                UIFormatter.warning('输入错误，请重新输入', Icons.WARNING)
            )
            continue

        while True:
            UIFormatter.print_formatted(UIFormatter.section("选择年份", Icons.CLOCK))
            now_year = datetime.datetime.today().year
            year_input = input(UIFormatter.input_prompt(f"年份 (2020 - {now_year})", str(now_year)))

            if year_input == '':
                year = now_year
                break
            elif year_input in quit_lst:
                return none_return
            else:
                try:
                    year = int(year_input)
                    if 2020 <= year <= now_year:
                        break
                    else:
                        UIFormatter.print_formatted(
                            UIFormatter.warning(f'年份必须在 2020-{now_year} 之间', Icons.WARNING)
                        )
                        continue
                except:
                    UIFormatter.print_formatted(
                        UIFormatter.warning('请输入有效的年份', Icons.WARNING)
                    )
                    continue

        while True:
            UIFormatter.print_formatted(UIFormatter.section("设置学分", Icons.STAR))
            credit_input = input(UIFormatter.input_prompt("要学习的总学分", "30"))

            if credit_input == '':
                credit = 30.0
                return course_type, year, credit
            elif credit_input in quit_lst:
                return none_return
            else:
                try:
                    credit = float(credit_input)
                    if credit > 0:
                        return course_type, year, credit
                    else:
                        UIFormatter.print_formatted(
                            UIFormatter.warning('学分必须大于0', Icons.WARNING)
                        )
                        continue
                except:
                    UIFormatter.print_formatted(
                        UIFormatter.warning('请输入有效的学分数', Icons.WARNING)
                    )
                    continue


def select_user_menu(user_folder: Path) -> Tuple[Optional[str], Optional[str]]:
    """选择用户菜单 - 统一输出风格"""
    if not user_folder.exists():
        os.makedirs(user_folder)

    while True:
        key_files = list(user_folder.glob('*.atl'))
        dic = {str(i): file for i, file in enumerate(key_files, start=1)}

        UIFormatter.print_formatted(UIFormatter.header("👤 用户选择", "═", 50))

        if dic:
            UIFormatter.print_formatted(UIFormatter.section("已有学员", Icons.FOLDER))
            for key, value in dic.items():
                try:
                    with open(value, 'r', encoding='utf-8') as f:
                        username = json.load(f).get('username')
                    UIFormatter.print_formatted(UIFormatter.menu_item(key, username))
                except Exception as e:
                    UIFormatter.print_formatted(UIFormatter.menu_item(key, f"{value.name} (读取失败)"))

            UIFormatter.print_formatted(UIFormatter.divider())
            UIFormatter.print_formatted(UIFormatter.menu_item('i', '插入新学员'))
            UIFormatter.print_formatted(UIFormatter.menu_item('q', '退出'))

            choice = input(UIFormatter.input_prompt("请选择学员编号"))

            if choice == "q" or choice == "Q":
                UIFormatter.print_formatted(UIFormatter.info('退出程序', Icons.INFO))
                return None, None
            elif choice == 'i' or choice == 'I':
                if create_new_atl(path=user_folder):
                    continue  # 创建成功后继续循环显示菜单
                else:
                    UIFormatter.print_formatted(
                        UIFormatter.error('创建新用户失败', Icons.CROSS)
                    )
                    continue
            elif choice in dic.keys():
                key_path = dic.get(choice)
                try:
                    username, url_zxpx = _decode_read(path=key_path)
                    UIFormatter.print_formatted(
                        UIFormatter.success(f'已选择用户: {username}', Icons.CHECK)
                    )
                    return username, url_zxpx
                except Exception as e:
                    UIFormatter.print_formatted(
                        UIFormatter.error(f'读取用户文件失败: {e}', Icons.CROSS)
                    )
                    continue
            else:
                UIFormatter.print_formatted(
                    UIFormatter.warning('输入错误，请重新输入', Icons.WARNING)
                )
                continue
        else:
            UIFormatter.print_formatted(UIFormatter.info('未找到任何用户文件，需要创建新用户', Icons.INFO))
            if create_new_atl(path=user_folder):
                continue  # 创建成功后继续循环显示菜单
            else:
                UIFormatter.print_formatted(
                    UIFormatter.error('创建新用户失败', Icons.CROSS)
                )
                return None, None


def select_process_menu() -> Optional[str]:
    """选择处理菜单 - 统一输出风格"""
    process_dic = {
        '1': 'auto_learn',
        '2': 'add_course',
        '3': 'cancel_course',
        'q': None,
        'Q': None
    }

    UIFormatter.print_formatted(UIFormatter.header("⚙️ 操作选择", "═", 50))

    while True:
        UIFormatter.print_formatted(UIFormatter.section("选择操作类型", Icons.GEAR))
        UIFormatter.print_formatted(UIFormatter.menu_item('1', '自动学习'))
        UIFormatter.print_formatted(UIFormatter.menu_item('2', '添加课程'))
        UIFormatter.print_formatted(UIFormatter.menu_item('3', '取消课程'))
        UIFormatter.print_formatted(UIFormatter.menu_item('q', '退出'))

        choice = input(UIFormatter.input_prompt("请选择操作", "1"))

        if choice == '':
            return process_dic['1']
        elif choice in process_dic:
            if choice == 'q' or choice == 'Q':
                UIFormatter.print_formatted(UIFormatter.info('退出程序', Icons.INFO))
            return process_dic[choice]
        else:
            UIFormatter.print_formatted(
                UIFormatter.warning('输入错误，请重新输入', Icons.WARNING)
            )


def select_exam() -> Optional[bool]:
    """选择是否考试 - 统一输出风格"""
    UIFormatter.print_formatted(UIFormatter.section("学习模式选择", Icons.EXAM))

    while True:
        UIFormatter.print_formatted(UIFormatter.menu_item('1', '自动看视频并答题 (推荐)'))
        UIFormatter.print_formatted(UIFormatter.menu_item('2', '仅看视频不答题'))
        UIFormatter.print_formatted(UIFormatter.menu_item('q', '退出'))

        choice = input(UIFormatter.input_prompt("请选择学习模式", "1"))

        if choice == '' or choice == '1':
            UIFormatter.print_formatted(
                UIFormatter.success('已选择：完整学习模式（视频+考试）', Icons.STAR)
            )
            return True
        elif choice == '2':
            UIFormatter.print_formatted(
                UIFormatter.info('已选择：仅观看视频模式', Icons.VIDEO)
            )
            return False
        elif choice == 'q' or choice == 'Q':
            UIFormatter.print_formatted(UIFormatter.info('退出程序', Icons.INFO))
            return None
        else:
            UIFormatter.print_formatted(
                UIFormatter.warning('输入错误，请重新输入', Icons.WARNING)
            )


def select_study_time_window() -> Optional[str]:
    """选择 CLI 学习时间窗"""
    default_window = '08:00-12:00,13:00-17:00,19:00-22:00'
    UIFormatter.print_formatted(UIFormatter.section("学习时间设置", Icons.CLOCK))
    UIFormatter.print_formatted(
        UIFormatter.info(f"直接回车使用默认时间：{default_window}")
    )
    UIFormatter.print_formatted(
        UIFormatter.info("支持跨天时间段，例如 22:00-01:00")
    )

    while True:
        value = input(UIFormatter.input_prompt("允许学习时间", default_window)).strip()
        if value == '':
            value = default_window
        if value in ('q', 'Q'):
            UIFormatter.print_formatted(UIFormatter.info('退出程序', Icons.INFO))
            return None
        try:
            window = StudyTimeWindow(value)
            UIFormatter.print_formatted(
                UIFormatter.success(f'已选择学习时间：{window.describe()}', Icons.CLOCK)
            )
            return value
        except ValueError as e:
            UIFormatter.print_formatted(
                UIFormatter.warning(str(e), Icons.WARNING)
            )


def main():
    """主函数 - 统一输出风格"""
    user_folder = Path('./users')
    data_folder = Path('./Data')

    try:
        UIFormatter.print_formatted(UIFormatter.header("🚀 自动学习系统", "═", 60))
        UIFormatter.print_formatted(
            UIFormatter.info("欢迎使用自动学习系统！", Icons.ROCKET)
        )

        # 选择用户
        username, url_zxpx = select_user_menu(user_folder=user_folder)
        if not username or not url_zxpx:
            UIFormatter.print_formatted(
                UIFormatter.warning('未选择用户，程序退出', Icons.WARNING)
            )
            return

        # 选择操作
        process_choice = select_process_menu()
        if not process_choice:
            return

        UIFormatter.print_formatted(
            UIFormatter.info(f'已选择操作: {process_choice}', Icons.CHECK)
        )

        if process_choice == 'auto_learn':  # 自动学习
            exam_flag = select_exam()
            if exam_flag is None:
                return
            study_time_window = select_study_time_window()
            if study_time_window is None:
                return

            UIFormatter.print_formatted(
                UIFormatter.section('正在初始化自动学习系统', Icons.GEAR)
            )
            auto_study = AutoStudyRefactored(
                data_folder=data_folder,
                username=username,
                url_zxpx=url_zxpx,
                study_time_window=study_time_window
            )
            UIFormatter.print_formatted(
                UIFormatter.section('开始自动学习', Icons.ROCKET)
            )
            auto_study.all_in_one(finish_exam=exam_flag)

        elif process_choice == 'add_course':  # 添加课程
            course_type, year, credit = add_course_menu()
            if course_type and year and credit:
                UIFormatter.print_formatted(
                    UIFormatter.section('正在初始化课程管理系统', Icons.GEAR)
                )
                auto_study = AutoStudyRefactored(
                    data_folder=data_folder,
                    username=username,
                    url_zxpx=url_zxpx
                )
                auto_study.add_course(rt=course_type, year=year, credit=credit)
            else:
                UIFormatter.print_formatted(
                    UIFormatter.info('操作已取消', Icons.INFO)
                )

        elif process_choice == 'cancel_course':  # 取消课程
            UIFormatter.print_formatted(
                UIFormatter.section('正在初始化课程管理系统', Icons.GEAR)
            )
            auto_study = AutoStudyRefactored(
                data_folder=data_folder,
                username=username,
                url_zxpx=url_zxpx
            )
            auto_study.cancel_all_course()

        UIFormatter.print_formatted(
            UIFormatter.success('程序执行完毕', Icons.STAR)
        )

    except KeyboardInterrupt:
        UIFormatter.print_formatted(
            UIFormatter.warning('用户中断程序', Icons.WARNING)
        )
    except LoginException as e:
        UIFormatter.print_formatted(
            UIFormatter.error(f'登录失败: {e}', Icons.CROSS)
        )
    except NetworkException as e:
        UIFormatter.print_formatted(
            UIFormatter.error(f'网络错误: {e}', Icons.CROSS)
        )
    except Exception as e:
        UIFormatter.print_formatted(
            UIFormatter.error(f'程序执行出错: {e}', Icons.CROSS)
        )
        logging.exception("程序异常")
        # 添加更详细的错误信息
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
