# 开发进度

> **重要：Claude 必须自主维护本文件。** 每次完成重要改动或遇到问题后，在对应章节记录。每条记录必须附上 git commit ID。

## 已完成功能

### 阶段 1：基础设施
- [x] 项目初始化 (pyproject.toml, .gitignore, .env)
- [x] SQLAlchemy async + SQLite 数据库
- [x] ORM 模型: Task, Instance, LogEntry, Worktree
- [x] Pydantic schemas
- [x] Task CRUD API + 优先级队列

### 阶段 2：Claude Code 集成
- [x] StreamParser — NDJSON stream-json 逐行解析
- [x] InstanceManager — 子进程生命周期管理
- [x] Instance API (CRUD, run, stop, logs)
- [x] 子进程启动前 unset CLAUDECODE 环境变量

### 阶段 3：Git Worktree
- [x] WorktreeManager — create, merge (--no-ff), remove, cleanup
- [x] Worktree ORM 模型及与实例执行的集成

### 阶段 4：Ralph Loop
- [x] 自动取活循环：取最高优先级任务 → 执行 → 循环
- [x] Plan Mode：只读分析 → plan_review → 审批 → 执行
- [x] API: start/stop/status per instance

### 阶段 5：WebSocket
- [x] WebSocketBroadcaster — channel-based pub/sub
- [x] WebSocket 端点 subscribe/unsubscribe
- [x] 实时日志推送和状态更新
- [x] Task channel 广播 (`task:{id}`)

### 阶段 6：React 前端
- [x] Vite + React + Tailwind CSS v4
- [x] LoginPage token 认证
- [x] Dashboard — 统计栏 + InstanceGrid + 日志弹窗
- [x] TasksPage — TaskForm + 筛选标签 + TaskList
- [x] InstanceGrid — 创建/删除/停止 + Ralph Loop 开关
- [x] InstanceLog — WebSocket 实时日志查看器
- [x] useWebSocket hook (指数退避重连)

### 阶段 7：语音输入
- [x] WhisperClient — OpenAI Whisper API
- [x] Voice API (POST /api/voice/transcribe)
- [x] VoiceButton 组件 (MediaRecorder API)
- [x] 集成到 TaskForm 的标题和描述字段

### 阶段 8：PWA
- [x] manifest.json + service worker
- [x] Apple meta tags (iOS 主屏幕)
- [x] PWA 图标 (SVG)

### 阶段 9：Plan Mode UI
- [x] PlanPanel 组件 — 查看/审批/拒绝计划
- [x] Plan approve/reject API
- [x] 任务状态: plan_review (紫色标识)

### 阶段 10：认证 + 远程访问
- [x] TokenAuthMiddleware (Bearer token + query param)
- [x] Login API
- [x] 前端认证流程 (登录门控, 401 自动登出)
- [x] ngrok / Cloudflare Tunnel 隧道支持
- [x] 生产模式: 后端服务前端静态文件

### 阶段 11：多轮对话
- [x] 从 stream-json 提取 session_id (system/init + result 事件)
- [x] session_id + last_cwd 存储在 Task 模型上
- [x] InstanceManager 支持 `--resume` 标志
- [x] Chat API (POST /api/tasks/{id}/chat, GET .../chat/history)
- [x] ChatView 组件 — 聊天气泡 UI + WebSocket 实时流
- [x] Follow-up 时自动查找空闲 instance
- [x] IME 组合输入处理 (防止中文输入法 Enter 发送)
- [x] 过滤空的 partial streaming 消息

### 阶段 12：任务生命周期重构
- [x] GlobalDispatcher — 全局调度器，替代 per-instance RalphLoop
- [x] 9 步任务生命周期: pending → in_progress → executing → merging → completed
- [x] worktree 创建前 git fetch origin，基于远程分支
- [x] 完成后 rebase + merge --ff-only + push (带重试 + merge lock)
- [x] conflict 状态 + 冲突解决端点
- [x] Project 模型 (name, git_url, local_path) + 自动 clone
- [x] Task.project_id 关联 Project，dispatcher 自动解析为 target_repo
- [x] 修复 dequeue() 排序 bug (desc → asc)
- [x] 前端: 项目选择器、新状态颜色、Dispatcher 全局开关
- **Commit**: c1407e4

### 阶段 13：Claude Code 完全自主 + 本地项目支持
- [x] Project 模型：git_url 改为 nullable，新增 has_remote 字段
- [x] 项目创建支持两种模式：clone 已有仓库（has_remote=True）和本地 git init（has_remote=False）
- [x] 新项目自动生成 CLAUDE.md（含 9 步自主任务生命周期模板）
- [x] Dispatcher 简化：去掉 merge/push/conflict 逻辑，Claude Code 自主完成 git 操作
- [x] 去掉 merging/conflict 状态、resolve-conflict 端点
- [x] TaskForm 重构：创建任务时可直接新建项目（输入名称 + 可选 remote URL）
- [x] 去掉 targetRepo 手动填路径方式，统一通过 project_id 关联
- **Commit**: 231a0b7

### 阶段 14：全面补齐测试覆盖
- [x] 整合 conftest.py 共享 fixture（app/client/session_factory）
- [x] 新增 102 个测试（52 → 154 总计）
- [x] 覆盖所有 API 端点：system、auth、projects、instances、chat 补全
- [x] 覆盖所有服务层：dispatcher、instance_manager、worktree_manager、ralph_loop、ws_broadcaster、whisper_client
- [x] 修复 chat.py 中多余的 `db.begin()` 导致事务冲突 bug
- [x] 修复 chat.py 中 last_cwd 指向已清理 worktree 的 bug（添加 os.path.isdir 回退）
- **Commit**: (待提交)

### 文档
- [x] README.md
- [x] CLAUDE.md
- [x] TEST.md
- [x] PROGRESS.md

---

## 问题记录

> 格式：问题 → 原因 → 解决 → 预防措施 → commit ID

### 前端空白页
- **问题**: 打开网页一片空白，控制台报错 `does not provide an export named 'Instance'`
- **原因**: Vite 会去除 type-only exports，`import { Instance } from '../../api/client'` 失败
- **解决**: 类型用 `import type { X }` 单独导入，值用 `import { api }` 导入
- **预防**: 前端所有类型导入必须用 `import type`，已写入 CLAUDE.md 约定
- **Commit**: c1407e4

### 优先级排序反了
- **问题**: P1 任务在 P0 之前执行
- **原因**: 代码用了 `Task.priority.desc()`，而约定是数字越小优先级越高
- **解决**: 改为 `Task.priority.asc()`
- **预防**: 已在 CLAUDE.md 注明「优先级数字越小越高，排序用 `.asc()`」
- **Commit**: c1407e4

### 多轮对话 resume 失败
- **问题**: Follow-up 消息报错 `No conversation found with session ID`
- **原因**: Claude Code 的 session 文件按 cwd 路径存储，follow-up 时 cwd 变了导致找不到 session
- **解决**: 在 Task 模型上新增 `last_cwd` 字段，launch 时记录，resume 时使用相同 cwd
- **预防**: 已在 CLAUDE.md 注明「resume 必须使用和原始 session 相同的 cwd」
- **Commit**: c1407e4

### session_id 应绑定 Task 而非 Instance
- **问题**: 最初将 session_id 放在 Instance 上，导致 Instance 切换任务后丢失之前任务的 session
- **原因**: Instance 是 worker 会轮换处理多个 task，session 应该跟着 task 走
- **解决**: 将 session_id 和 last_cwd 从 Instance 模型迁移到 Task 模型
- **预防**: 已在 CLAUDE.md 注明「session_id 和 last_cwd 在 Task 上，不是 Instance」
- **Commit**: c1407e4

### Chat 消息显示重复
- **问题**: 用户发的 follow-up 消息和 Claude 回复都显示两遍
- **原因1**: 用户消息 — 前端乐观添加 + WebSocket 广播各一次
- **原因2**: 助手消息 — Claude Code 的 stream-json 会发多条 message 事件，部分 content 为 null（流式 chunk），有内容的和空的都被渲染了
- **解决**: WebSocket 监听忽略 `user_message` 事件；过滤 content 为 null 的 `message`/`result` 事件
- **预防**: 前端接收 WebSocket 消息时注意去重和过滤无效数据
- **Commit**: c1407e4

### 前端构建 TS 报错未使用变量
- **问题**: `npm run build` 因未使用的 import 报 TS6133 错误
- **原因**: 重构时移除了功能但没清理对应的 import
- **解决**: 删除未使用的 import (`Play`, `api`, `useCallback`)
- **预防**: 重构后检查相关文件的 import 是否需要清理
- **Commit**: c1407e4

### 未遵守 CLAUDE.md 规范
- **问题**: 多次改代码时未遵守 CLAUDE.md 要求的测试规范和文件维护规则——改代码前没先跑测试、改完没更新 README.md/TEST.md/PROGRESS.md
- **原因**: 专注实现功能忽略了流程规范
- **解决**: 补跑测试确认全绿，补更新三个文档
- **预防**: 每次改代码严格按流程：1) 先跑测试 2) 改代码 3) 再跑测试 4) 更新四个文档
- **Commit**: 231a0b7

### Chat 完整显示 Claude Code 交互内容
- **问题**: Chat 界面只显示精简内容，工具调用只有名字没有具体代码改动
- **原因**: Chat API 没返回 `tool_input`/`tool_output` 字段，前端也没渲染
- **解决**: Chat API 补全返回字段、ChatMessage 类型加字段、MessageBubble 完整渲染工具内容（带折叠）
- **Commit**: e810760

### Chat 退出 bug + Plan approve 无反应
- **问题1**: 进入 Chat 后退出，页面不断返回 Chat 界面
- **原因**: `TasksPage` 的 `refresh` 回调依赖 `chatTask` state，导致 `setChatTask(null)` 后旧闭包里的 `chatTask` 引用又把它设回去
- **解决**: 用 `useRef` 保存 `chatTask` 引用，`refresh` 不再依赖 `chatTask` state
- **问题2**: PlanPanel 的 approve/reject 按钮按了没反应
- **原因**: 用了原生 `fetch` 而不是 `api` 客户端，没带 `Authorization` header，401 被静默忽略
- **解决**: 改用 `api.approvePlan()` / `api.rejectPlan()`，在 `client.ts` 新增这两个方法
- **附加**: 修复了 conftest.py 模型未导入导致单文件跑测试时 `no such table` 的问题；新增 10 个 chat/plan API 测试
- **Commit**: 2a7cd89

---

## 已知问题

- 数据库 Schema 变更需删除 `claude_manager.db` 重建（暂无迁移）
- `total_cost_usd` 仅在 Claude Code stream-json result 事件报告时更新
- WebSocket 重连期间可能有短暂的实时日志缺失

## 未来计划

- [ ] Alembic 数据库迁移
- [ ] 任务依赖 (B 等待 A 完成)
- [ ] 费用统计面板 (图表)
- [ ] 实例资源监控 (CPU/内存)
- [ ] 批量导入任务 (CSV/JSON)
- [ ] 任务模板
- [ ] 通知系统 (完成/失败提醒)
- [ ] 深色/浅色主题切换
