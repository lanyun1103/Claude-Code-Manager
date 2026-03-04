# Claude Code Manager

Web 端调度和管理多个 Claude Code 实例并行工作。灵感来自胡渊鸣的文章「我给 10 个 Claude Code 打工」。

## 功能

- **全局调度器** — 启动时自动创建 worker、自动分配任务，无需手动操作
- **Claude Code 完全自主** — Claude Code 自主完成 worktree 创建、commit、fetch、merge、push、冲突解决和清理，Dispatcher 只负责分配任务和判断成败
- **9 步任务生命周期** — 领取 → 创建工作区 → 实现 → 提交 → merge + 测试 → 合并到 main → 标记完成 → 清理 → 经验沉淀
- **项目管理** — 支持 clone 已有仓库（有 remote）和本地 git init（无 remote），创建任务时可直接新建项目
- **任务队列** — 创建任务，按优先级自动调度（数字越小优先级越高）
- **多实例并行** — 同时运行多个 Claude Code 实例，各自处理不同任务
- **Git Worktree** — 每个实例在独立的 worktree 中工作，互不干扰
- **多轮对话** — 任务完成后可通过 Chat 界面继续追问，自动 `--resume` 同一 session
- **实时日志** — WebSocket 推送，实时查看每个实例的执行过程
- **Plan Mode** — 敏感任务先生成计划，人工审批后再执行
- **语音输入** — 通过 OpenAI Whisper API 语音转文字创建任务
- **PWA** — 手机浏览器 Add to Home Screen，原生 App 体验
- **Android App** — 通过 Capacitor 打包原生 APK，App 内可配置远程服务器地址
- **主题切换** — 支持浅色/深色主题，偏好持久化
- **Token 认证** — Bearer Token 保护所有 API，安全远程访问
- **远程访问** — 通过 ngrok / Cloudflare Tunnel 隧道暴露到公网

## 任务生命周期

Dispatcher 只负责分配任务和判断成败，Claude Code 自主完成整个工作流：

1. **领取任务** — Dispatcher dequeue，status=in_progress
2. **创建工作区** — Claude Code 自主创建 git worktree，status=executing
3. **实现功能** — Claude Code 在 worktree 中编写代码
4. **提交代码** — Claude Code 自主 `git add` + `git commit`
5. **Merge + 测试** — Claude Code 自主 `git fetch origin && git merge origin/main` + 运行测试
6. **合并到 main** — Claude Code 自主 rebase + merge + push（有冲突自行解决）
7. **标记完成** — Claude Code 更新文档
8. **清理** — Claude Code 自主清理 worktree 和 task 分支
9. **经验沉淀** — Claude Code 在 PROGRESS.md 记录经验

**状态流转：**
```
pending → in_progress → executing → completed
                           ↓
                        (fail)
                           ↓
                        pending (retry)
```

## 技术栈

| 层 | 技术 |
|---|------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy (async), SQLite |
| Frontend | React, Vite, Tailwind CSS v4, TypeScript |
| 实时通信 | WebSocket |
| 语音 | OpenAI Whisper API |
| 远程 | ngrok / Cloudflare Tunnel |

## 项目结构

```
claude-manager/
├── backend/
│   ├── api/            # REST + WebSocket 路由
│   ├── middleware/      # Token 认证中间件
│   ├── models/          # SQLAlchemy ORM (task, instance, project, log_entry, worktree)
│   ├── schemas/         # Pydantic 请求/响应模型
│   ├── services/        # 核心业务逻辑
│   │   ├── dispatcher.py        # 全局调度器 (9 步任务生命周期)
│   │   ├── instance_manager.py  # Claude Code 子进程管理
│   │   ├── ralph_loop.py        # 自动取活循环 (legacy)
│   │   ├── stream_parser.py     # NDJSON stream-json 解析
│   │   ├── task_queue.py        # 优先级任务队列
│   │   ├── worktree_manager.py  # Git worktree 管理 + rebase + push
│   │   ├── ws_broadcaster.py    # WebSocket 广播
│   │   └── whisper_client.py    # 语音转文字
│   └── main.py          # FastAPI 入口
├── frontend/
│   ├── public/          # PWA manifest, service worker, icons
│   └── src/
│       ├── api/         # HTTP + WebSocket 客户端
│       ├── components/  # Chat, Instances, Tasks, PlanReview, Voice
│       ├── config/      # server (远程服务器配置), theme (主题切换)
│       ├── hooks/       # useWebSocket
│       └── pages/       # Dashboard, TasksPage, LoginPage, ServerConfigPage
├── scripts/
│   ├── dev.sh           # 一键启动开发环境
│   └── tunnel.sh        # ngrok 隧道
├── pyproject.toml
└── .env
```

## 快速开始

### 前置条件

- macOS（Claude Code 部署在本机）
- Python 3.11+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) — Python 包管理器
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) 已安装

### 安装

```bash
git clone https://github.com/zjw49246/Claude-Code-Manager.git && cd Claude-Code-Manager

# 后端依赖（使用 uv）
uv sync

# 前端依赖
cd frontend && npm install && cd ..

# 配置
cp .env.example .env
# 编辑 .env，设置：
#   AUTH_TOKEN=你的访问密码
#   OPENAI_API_KEY=sk-...（语音功能需要）
#   WORKSPACE_DIR=~/Projects（项目工作区根目录）
```

### 启动

```bash
# 一键启动
./scripts/dev.sh

# 或分别启动
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
cd frontend && npx vite --host &
```

访问 http://localhost:5173，输入 `AUTH_TOKEN` 登录。

启动后 Dispatcher 会自动创建 worker 实例并开始调度。

### 远程访问（ngrok）

```bash
# 安装 ngrok
brew install ngrok
ngrok config add-authtoken YOUR_NGROK_TOKEN

# 生产模式：构建前端静态文件，由后端统一服务
cd frontend && npm run build && cd ..
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

# 启动隧道
ngrok http 8000
```

用 ngrok 给出的 https URL 从手机访问。

### Android App 打包

```bash
cd frontend

# 安装 Capacitor（已在 package.json 中）
npm install

# 构建 + 同步 + 打包 APK
npm run build
npx cap sync android
JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home" \
  android/gradlew -p android assembleDebug

# APK 位于 android/app/build/outputs/apk/debug/app-debug.apk
```

首次打开 App 在登录页展开 "Server URL" 输入服务器地址（如 Cloudflare Tunnel URL），然后输入 Token 登录。

## 使用流程

### 基本流程

1. **Tasks** — 创建任务，选择已有项目或新建项目（可选填 remote URL），填写 Prompt 和优先级
2. **Dispatcher** 自动分配任务到空闲 worker → Claude Code 自主完成所有工作（含 worktree 创建和清理） → 取下一个
4. 点击任务的 **Chat** 按钮，可以对已完成的任务继续追问

### Plan Mode

创建任务时选择 Mode = `plan`：
1. Claude Code 先以只读模式分析代码，生成执行计划
2. 任务进入 `plan_review` 状态，在 Tasks 页面显示计划内容
3. 点击 Approve 批准后，任务重新入队执行

### 语音输入

任务创建表单的标题和描述字段旁有 🎙 按钮，点击后录音，松开自动转文字填入。

## API

| 模块 | 端点 | 说明 |
|------|------|------|
| Projects | `GET/POST /api/projects` | 项目列表/创建 |
| | `GET/PUT/DELETE /api/projects/{id}` | 项目详情/更新/删除 |
| | `POST /api/projects/{id}/reclone` | 重新 clone |
| Tasks | `GET/POST /api/tasks` | 任务列表/创建 |
| | `GET/PUT/DELETE /api/tasks/{id}` | 任务详情/更新/删除 |
| | `POST /api/tasks/{id}/cancel` | 取消任务 |
| | `POST /api/tasks/{id}/retry` | 重试任务 |
| | `POST /api/tasks/{id}/plan/approve` | 批准计划 |
| | `POST /api/tasks/{id}/chat` | 发送追问消息 |
| | `GET /api/tasks/{id}/chat/history` | 获取对话历史 |
| Instances | `GET/POST /api/instances` | 实例列表/创建 |
| | `DELETE /api/instances/{id}` | 删除实例 |
| | `POST /api/instances/{id}/stop` | 停止实例 |
| | `POST /api/instances/{id}/run` | 手动执行 |
| | `GET /api/instances/{id}/logs` | 获取日志 |
| Dispatcher | `GET /api/dispatcher/status` | 调度器状态 |
| | `POST /api/dispatcher/start` | 启动调度器 |
| | `POST /api/dispatcher/stop` | 停止调度器 |
| Voice | `POST /api/voice/transcribe` | 语音转文字 |
| WebSocket | `ws://host/ws` | 实时推送（subscribe channel） |
| Auth | `POST /api/auth/login` | Token 登录 |
| System | `GET /api/system/health` | 健康检查 |
| | `GET /api/system/stats` | 统计信息 |

所有 API（除 health 和 login）需要 `Authorization: Bearer <token>` 头。

## 配置

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `AUTH_TOKEN` | (必填) | API 认证 Token |
| `OPENAI_API_KEY` | (可选) | 语音功能所需 |
| `DATABASE_URL` | `sqlite+aiosqlite:///./claude_manager.db` | 数据库连接 |
| `WORKSPACE_DIR` | `~/Projects` | 项目 clone 目标目录 |
| `MAX_CONCURRENT_INSTANCES` | `5` | 最大并发 worker 数 |
| `AUTO_START_DISPATCHER` | `true` | 启动时自动开始调度 |
| `MERGE_PUSH_RETRIES` | `3` | rebase + push 最大重试次数 |
| `AUTO_PUSH_TO_ORIGIN` | `true` | 完成后是否自动 push |
| `TASK_TIMEOUT_SECONDS` | `1800` | 单个任务最长执行时间（秒），超时后 kill 进程 |

## 架构要点

- **GlobalDispatcher**：只负责分配任务、启动 Claude Code、判断成败。所有 git 操作（worktree 创建/清理、commit/merge/push/冲突解决）全由 Claude Code 自主完成
- **Claude Code 集成**：通过 `claude -p [prompt] --dangerously-skip-permissions --output-format stream-json --verbose` 非交互模式调用，Claude Code 读项目 CLAUDE.md 决定 git 操作
- **进程超时保护**：任务执行超过 `TASK_TIMEOUT_SECONDS`（默认 30 分钟）后自动 kill，防止进程挂死
- **多轮对话**：session_id 绑定在 Task 上，follow-up 时使用 `--resume <session_id>` 续接会话
- **进程管理**：`asyncio.create_subprocess_exec` 启动，必须 unset `CLAUDECODE` 环境变量避免嵌套检测
- **停止机制**：SIGTERM → 等待 10s → SIGKILL
