# Auto Learn Web

这个 Web 版本把原来的 CLI 脚本 `my_auto_learn.py` 包成 FastAPI 服务，保留原来的 `users/` 用户文件和 `Data/` 题库目录。页面文件在 `static/index.html`，后端 API 在 `app.py`。

## 本地运行

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 28000
```

打开 `http://localhost:28000`。

输入 `authCode` 保存学员时，系统会自动登录解析学员姓名，并生成 `users/学员名.atl`；保存成功后页面会自动刷新学员列表并选中新学员。

## 多学员任务

现在支持多个学员同时运行任务。规则是：

- 同一个学员只能有一个正在运行的任务。
- 不同学员可以同时启动任务。
- 页面会按学员显示任务状态；选择不同学员可以查看对应日志。
- 学员概览只显示当前阶段和当前大课程，不细分到每个章节。
- 停止任务只会停止当前选中的学员任务。
- 选择学员后可以修改“学习时间窗”，点击“更新时间窗”即可对该学员生效；正在运行的学习任务会在几秒内读取新设置。
- 每个学员的学习时间窗独立保存，切换学员时页面会自动加载该学员自己的时间窗。
- 题库写入按课程加了文件锁，降低多个学员同时写同一门课程题库时的数据冲突风险。

## Docker 运行

```bash
docker build -t auto-learn-web .
docker run -d --name auto-learn-web \
  -p 28000:28000 \
  -v "$PWD/users:/app/users" \
  -v "$PWD/Data:/app/Data" \
  auto-learn-web
```

反代时转发到容器的 `28000` 端口即可。

## Docker Compose

```bash
docker compose up -d --build
```

默认映射到宿主机 `28000` 端口，并挂载：

```text
./users    -> /app/users
./Data     -> /app/Data
./.runtime -> /app/.runtime
```

其中 `.runtime` 保存每个学员独立的学习时间窗等运行时设置。

## 学习时间窗

在页面的“学习时间窗”输入：

```text
08:00-12:00,19:00-22:30
```

留空表示不限制时间。支持跨天时间段，例如：

```text
22:00-01:00
```

勾选“保持等待”后，如果当前不在学习时间内，任务会等待到下一个时间窗再继续；如果学习过程中超出时间窗，会暂停，下一次进入时间窗后重新扫描未完成课程继续学习。

## 注意

`users/*.atl` 中包含登录参数。部署到公网前建议通过反代增加访问控制，例如 Nginx Basic Auth、内网访问或 SSO。
