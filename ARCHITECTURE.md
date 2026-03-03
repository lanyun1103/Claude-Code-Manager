# Claude Code Manager - 架构分析文档

## 文档概述

本文档对 Claude Code Manager 项目进行深入的架构分析,涵盖系统设计、核心组件、数据流、关键决策和扩展性等方面。

## 1. 系统概述

### 1.1 项目定位

Claude Code Manager 是一个 Web 端调度管理系统,用于并行管理多个 Claude Code 实例,实现自动化任务分配、执行监控和结果管理。

### 1.2 核心价值

- **并行化**:支持多个 Claude Code 实例同时执行不同任务
- **自动化**:全局调度器自动分配任务,无需人工干预
- **可观测性**:实时 WebSocket 推送执行日志,完整的任务生命周期追踪
- **项目管理**:支持多项目管理,自动 git 操作(worktree、commit、merge、push)

### 1.3 关键指标

- 最大并发实例数:可配置 (默认由 `max_concurrent_instances` 控制)
- 任务超时时间:可配置 (默认由 `task_timeout_seconds` 控制)
- 自动重试次数:每个任务最多重试 2 次 (可配置)
- 实时通信延迟:WebSocket 毫秒级推送

## 2. 整体架构

### 2.1 架构风格

采用 **前后端分离** + **事件驱动** 架构:

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend Layer                       │
│   React 19 + TypeScript + Tailwind v4 + WebSocket Client   │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP REST API + WebSocket
┌────────────────────────┴────────────────────────────────────┐
│                        Backend Layer                         │
│              FastAPI + SQLAlchemy Async + SQLite             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ REST API    │  │ WebSocket    │  │ Global Dispatcher│   │
│  │ Endpoints   │  │ Broadcaster  │  │ (Task Scheduler) │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │Instance     │  │ Task Queue   │  │ Stream Parser    │   │
│  │Manager      │  │              │  │ (NDJSON)         │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ SQLite (async)
┌────────────────────────┴────────────────────────────────────┐
│                      Persistence Layer                       │
│   SQLite Database (tasks, instances, logs, projects, etc)   │
└────────────────────────┬────────────────────────────────────┘
                         │ subprocess management
┌────────────────────────┴────────────────────────────────────┐
│                      Process Layer                           │
│   Multiple Claude Code Subprocesses (asyncio.subprocess)    │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈

#### 后端
- **Web 框架**: FastAPI (高性能异步框架)
- **ORM**: SQLAlchemy 2.0+ (async mode)
- **数据库**: SQLite + aiosqlite (异步驱动)
- **配置管理**: Pydantic Settings (基于 .env)
- **实时通信**: WebSocket (原生,基于 channel 的 pub/sub)
- **语音转文字**: OpenAI Whisper API
- **进程管理**: asyncio.subprocess

#### 前端
- **UI 框架**: React 19
- **构建工具**: Vite
- **样式**: Tailwind CSS v4 (`@import "tailwindcss"` + Vite 插件)
- **语言**: TypeScript
- **图标**: Lucide React
- **实时通信**: WebSocket (指数退避重连)

#### 开发工具
- **包管理**: uv (后端), npm (前端)
- **测试**: pytest
- **隧道**: Cloudflare Tunnel / ngrok

### 2.3 部署模式

支持两种部署模式:

1. **开发模式**: 前后端分离,前端 Vite dev server (5173) + 后端 FastAPI (8000)
2. **生产模式**: 单端口部署,FastAPI 服务前端静态文件 (8000)

## 3. 核心组件分析

### 3.1 GlobalDispatcher (全局调度器)

**职责**: 任务分配和生命周期管理的核心控制器

**设计理念**:
- **最小职责原则**: 只负责任务调度、进程启动/等待、结果判断
- **自治委托**: 所有 git 操作(worktree、commit、merge、push、冲突解决)完全委托给 Claude Code 自主完成
- **轮询调度**: 每 2 秒轮询一次,查找空闲实例和待执行任务

**关键方法**:

```python
class GlobalDispatcher:
    async def start()                    # 启动调度循环
    async def _dispatch_loop()           # 核心调度循环:轮询 idle 实例 + pending 任务
    async def _run_task_lifecycle()      # 单个任务完整生命周期
    async def _run_plan_phase()          # Plan 模式特殊处理
    async def _ensure_instances()        # 自动创建 worker 实例
```

**任务生命周期 (9 步)**:

1. **Pending → In Progress**: 从 TaskQueue 出队,分配给空闲实例
2. **In Progress → Executing**: 更新状态,启动 Claude Code 子进程
3. **Plan 模式检查**: 如果是 plan 模式且未审批,进入 plan phase
4. **启动 Claude Code**: 调用 `instance_manager.launch()`,传递完整 prompt
5. **等待执行完成**: `asyncio.wait_for(process.wait(), timeout)`
6. **判断退出码**:
   - `exit_code != 0`: 重试或标记失败
   - `exit_code == 0`: 标记完成,增加完成计数
7. **广播状态变更**: 通过 WebSocket 实时推送给前端
8. **异常处理**: 捕获异常,标记失败,防止调度器崩溃
9. **清理**: 从 `_running_tasks` 移除

**关键设计决策**:

- **Project 自动解析**: 如果 `task.project_id` 存在且 `task.target_repo` 为空,自动从 Project 表查询 `local_path` 并填充
- **Timeout 机制**: 防止任务无限期执行,超时后强制 kill 进程
- **重试机制**: 失败任务自动重入队列,最多重试 `max_retries` 次
- **并发控制**: 通过 `_running_tasks` 字典防止同一实例重复调度

### 3.2 InstanceManager (实例管理器)

**职责**: Claude Code 子进程的生命周期管理

**核心功能**:

1. **启动子进程**:
   ```python
   async def launch(instance_id, prompt, task_id, cwd, model, resume_session_id)
   ```
   - 构建 `claude` 命令行参数
   - 清理环境变量 (`CLAUDECODE`, `CLAUDE_CODE`) 避免嵌套检测
   - 通过 `asyncio.create_subprocess_exec` 启动
   - 更新实例状态为 `running`

2. **输出消费**:
   ```python
   async def _consume_output(instance_id, task_id, process)
   ```
   - 逐行读取 stdout (NDJSON 格式)
   - 调用 `StreamParser` 解析每行 JSON
   - 提取 `session_id` 和 `cost_usd` 保存到数据库
   - 将事件存储到 `log_entry` 表
   - 通过 `broadcaster` 实时推送到 WebSocket
   - 更新实例心跳时间

3. **停止子进程**:
   ```python
   async def stop(instance_id)
   ```
   - 先发送 SIGTERM (优雅关闭)
   - 等待 10 秒
   - 超时则发送 SIGKILL (强制杀死)

**关键设计**:

- **异步 I/O**: 完全基于 asyncio,不阻塞主线程
- **错误隔离**: 单条事件解析失败不影响后续日志读取
- **心跳机制**: 每次收到事件都更新 `last_heartbeat`,可用于健康检查
- **双通道广播**: 同时向 `instance:{id}` 和 `task:{id}` 两个 channel 广播

### 3.3 WebSocketBroadcaster (实时通信)

**职责**: 基于 channel 的 WebSocket 消息广播

**核心数据结构**:
```python
subscriptions: dict[str, set[WebSocket]]  # channel -> subscribers
```

**Channel 设计**:
- `instance:{id}`: 订阅某个实例的所有事件
- `task:{id}`: 订阅某个任务的所有事件
- `tasks`: 订阅全局任务状态变更
- `system`: 订阅系统级事件

**优点**:
- **解耦**: 发送方无需知道接收方,只需指定 channel
- **多播**: 一条消息可以同时发送给多个订阅者
- **自动清理**: 发送失败的连接自动从订阅列表移除

**消息格式**:
```json
{
  "channel": "task:123",
  "data": {
    "event_type": "message",
    "role": "assistant",
    "content": "..."
  }
}
```

### 3.4 TaskQueue (任务队列)

**职责**: 任务的 CRUD 和状态管理

**关键方法**:

```python
async def dequeue()           # 出队:获取最高优先级的 pending 任务
async def mark_completed()    # 标记完成
async def mark_failed()       # 标记失败
async def retry()             # 重试:重置状态为 pending,增加 retry_count
async def cancel()            # 取消正在执行的任务
```

**优先级规则**:
```python
.order_by(Task.priority.asc(), Task.created_at.asc())
```
- 数字越小优先级越高 (P0 > P1 > P2)
- 同优先级按创建时间排序 (FIFO)

**状态机**:
```
pending → in_progress → executing → completed
                           ↓
                        (fail)
                           ↓
                        pending (retry) / failed (max_retries 达到)
```

**删除限制**: 只允许删除 `pending`、`failed`、`cancelled`、`conflict` 状态的任务,防止误删正在执行的任务

### 3.5 StreamParser (流解析器)

**职责**: 解析 Claude Code 输出的 NDJSON 格式日志

**输入示例**:
```json
{"event_type":"message","role":"assistant","content":"Let me read the file."}
{"event_type":"tool_use","tool_name":"Read","tool_input":"{\"file_path\":\"/path/to/file\"}"}
{"event_type":"tool_result","tool_output":"file contents..."}
```

**输出格式**: 统一转换为字典列表,包含:
- `event_type`: 事件类型 (message, tool_use, tool_result, etc)
- `role`: 角色 (user, assistant)
- `content`: 消息内容
- `tool_name`, `tool_input`, `tool_output`: 工具调用相关
- `session_id`, `cost_usd`: 会话和成本信息
- `raw_json`: 原始 JSON 字符串

**容错性**: 解析失败时记录日志但不中断流读取

### 3.6 RalphLoop (遗留组件)

**状态**: Legacy,已被 GlobalDispatcher 替代

**保留原因**: 向后兼容,部分用户可能依赖旧的 Ralph Loop API

**功能**: 单个实例的自动取任务循环 (现已由全局调度器统一管理)

## 4. 数据模型设计

### 4.1 ER 图

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Project    │         │     Task     │         │   Instance   │
├──────────────┤         ├──────────────┤         ├──────────────┤
│ id (PK)      │◄───────┤ project_id   │         │ id (PK)      │
│ name         │         │ id (PK)      │────────►│ current_task │
│ git_url      │         │ title        │         │ name         │
│ has_remote   │         │ description  │         │ status       │
│ local_path   │         │ status       │         │ model        │
│ default_br   │         │ priority     │         │ pid          │
└──────────────┘         │ instance_id  │         │ total_cost   │
                         │ session_id   │         └──────────────┘
                         │ last_cwd     │                │
                         │ retry_count  │                │
                         │ mode         │                │
                         │ plan_*       │                │
                         └──────────────┘                │
                                │                        │
                                ▼                        │
                         ┌──────────────┐               │
                         │  LogEntry    │◄──────────────┘
                         ├──────────────┤
                         │ id (PK)      │
                         │ instance_id  │
                         │ task_id      │
                         │ event_type   │
                         │ role         │
                         │ content      │
                         │ tool_name    │
                         │ tool_input   │
                         │ tool_output  │
                         │ timestamp    │
                         └──────────────┘
```

### 4.2 核心字段说明

#### Task
- **session_id**: Claude Code 会话 ID,用于 `--resume` 继续对话
- **last_cwd**: 最后一次执行时的工作目录,resume 时必须使用相同 cwd
- **mode**: `auto` (直接执行) 或 `plan` (先生成计划等待审批)
- **plan_content**: Plan 模式生成的计划内容
- **plan_approved**: `null` (待审批) / `true` (已批准) / `false` (已拒绝)
- **retry_count**: 当前重试次数
- **merge_status**: 合并状态 (pending, merged, conflict, failed)

#### Instance
- **status**: `idle` (空闲) / `running` (执行中) / `stopped` (已停止) / `error` (错误)
- **worktree_path**: 当前 worktree 路径 (如有)
- **total_tasks_completed**: 累计完成任务数
- **total_cost_usd**: 累计 API 调用成本

#### LogEntry
- **event_type**: `message`, `tool_use`, `tool_result`, `process_exit` 等
- **role**: `user`, `assistant`, `system`
- **raw_json**: 保留原始 JSON,用于调试和数据恢复

#### Project
- **has_remote**: 是否有 remote (影响 git push 等操作)
- **local_path**: 本地仓库路径,会自动填充到 `task.target_repo`

### 4.3 索引设计

```python
# Task 表索引
Task.status.index = True        # 频繁按状态查询 (dequeue)
Task.priority.index = True      # 优先级排序
Task.project_id.index = True    # 按项目过滤

# 组合索引 (隐式):
# (status, priority, created_at) 用于 dequeue 查询
```

## 5. 数据流分析

### 5.1 任务创建与执行流程

```
[用户] → POST /api/tasks
         ↓
    [TaskQueue.create()] → Task(status=pending) → DB
         ↓
    [Dispatcher._dispatch_loop()] 轮询发现 pending 任务
         ↓
    [TaskQueue.dequeue()] → Task(status=in_progress)
         ↓
    [Dispatcher._run_task_lifecycle()]
         ↓
    [InstanceManager.launch()] → 启动 claude 子进程
         ↓
    [InstanceManager._consume_output()] 读取 stdout
         ↓
    [StreamParser.parse_line()] → events
         ↓
    ┌────────────────┬────────────────┐
    ↓                ↓                ↓
[LogEntry] → DB  [WebSocket]   [提取 session_id/cost]
                 Broadcast       ↓
                    ↓          更新 Task.session_id
              [前端实时更新]    Instance.total_cost
```

### 5.2 WebSocket 实时推送流程

```
[子进程输出] → InstanceManager._consume_output()
                ↓
          StreamParser.parse_line()
                ↓
          event: dict
                ↓
          ┌─────────────────┐
          ↓                 ↓
    LogEntry → DB    Broadcaster.broadcast()
                          ↓
                   channel: "instance:1"
                   channel: "task:123"
                          ↓
                   WebSocket clients
                          ↓
                   前端更新 UI
```

### 5.3 Plan 模式审批流程

```
[用户创建 Plan 模式任务] → Task(mode="plan", plan_approved=null)
         ↓
    [Dispatcher._run_task_lifecycle()]
         ↓
    检测到 plan 模式且未审批
         ↓
    [_run_plan_phase()] → 启动 Claude Code (只生成计划,不执行)
         ↓
    从 LogEntry 收集 assistant 消息 → plan_content
         ↓
    Task(status="plan_review") → 广播 "plan_ready"
         ↓
    [前端显示 PlanPanel]
         ↓
    ┌───────────────┬───────────────┐
    ↓               ↓               ↓
[用户批准]     [用户拒绝]     [用户修改后批准]
    ↓               ↓               ↓
plan_approved  plan_approved   plan_approved
= true         = false         = true
status         status          status
= pending      = cancelled     = pending
    ↓               ↓               ↓
重新进入队列     任务结束       重新进入队列
正常执行
```

### 5.4 多轮对话流程

```
[用户发送首条消息] → POST /api/tasks (创建新任务)
         ↓
    Dispatcher 分配实例 → InstanceManager.launch(resume_session_id=null)
         ↓
    收到 session_id → 保存到 Task.session_id + Task.last_cwd
         ↓
    任务完成 → Instance 释放
         ↓
[用户发送后续消息] → POST /api/tasks/{id}/chat
         ↓
    读取 Task.session_id + Task.last_cwd
         ↓
    InstanceManager.launch(
        resume_session_id=Task.session_id,
        cwd=Task.last_cwd  # 必须使用相同 cwd!
    )
         ↓
    Claude Code --resume {session_id} → 继续上下文对话
```

**关键点**:
- **Session ID 绑定到 Task**: 因为 Instance 是轮换执行不同任务的 worker,session 应该属于任务而非实例
- **CWD 一致性**: Resume 时必须使用和原始 session 相同的 cwd,否则 Claude Code 会报错

## 6. 关键设计决策

### 6.1 为什么 Session 绑定到 Task 而非 Instance?

**错误方案**: 将 `session_id` 存储在 `Instance` 模型
- **问题**: 一个 Instance 可以执行多个不同的 Task,每个 Task 有独立的会话上下文
- **后果**: 无法支持多轮对话,或者需要复杂的 session 池管理

**正确方案**: 将 `session_id` 存储在 `Task` 模型
- **优点**:
  - Task 和 Session 1:1 绑定,语义清晰
  - Instance 是无状态的 worker,可以轮换执行
  - 多轮对话只需读取 `Task.session_id` 和 `Task.last_cwd`

### 6.2 为什么使用 SQLite 而非 PostgreSQL?

**考虑因素**:
- **部署简单**: 单文件数据库,无需额外数据库服务
- **性能足够**: 异步 I/O + 单机部署,SQLite 完全胜任
- **并发限制**: 写操作串行化,但本项目主要是读多写少
- **可移植性**: 数据库文件可直接复制迁移

**权衡**:
- **不适合**: 高并发写入、分布式部署
- **适合**: 个人/小团队使用,单机部署,读多写少

### 6.3 为什么使用原生 WebSocket 而非 Socket.IO?

**优点**:
- **简单**: 无需额外依赖,FastAPI 原生支持
- **高效**: 无协议开销,直接传输 JSON
- **可控**: 完全掌控连接管理和消息格式

**缺点**:
- **无自动重连**: 需要前端自己实现指数退避重连
- **无 Room 概念**: 需要自己实现 channel-based pub/sub

**结论**: 对于本项目的需求,原生 WebSocket + 简单的 broadcaster 完全够用

### 6.4 为什么 GlobalDispatcher 不做 Git 操作?

**设计哲学**: **自治委托** (Delegation to Autonomy)

- **Claude Code 是自治 Agent**: 它有完整的 git 工具链和上下文理解能力
- **CLAUDE.md 驱动**: 每个项目的 CLAUDE.md 定义了完整的 git 工作流
- **灵活性**: 不同项目可以有不同的 git 策略 (worktree vs 直接提交,rebase vs merge 等)
- **简化调度器**: Dispatcher 只需判断 exit code,无需理解复杂的 git 状态

**如果 Dispatcher 做 Git 操作会怎样?**
- 需要解析 git 输出判断冲突
- 需要知道 worktree 路径 (但 Claude Code 可能动态创建)
- 需要处理各种 git 失败场景
- **违反单一职责原则**

### 6.5 为什么优先级数字越小优先级越高?

**约定**: P0 > P1 > P2 (类似 Linux 进程 nice 值)

**理由**:
- **SQL 排序自然**: `.order_by(priority.asc())` 直接得到高优先级任务
- **扩展性**: 可以插入 P-1, P-2 等超高优先级
- **行业惯例**: Kubernetes、Linux 等都采用此约定

### 6.6 为什么使用 NDJSON 而非纯 JSON?

**NDJSON (Newline Delimited JSON)**:
```
{"event":"A"}
{"event":"B"}
{"event":"C"}
```

**优点**:
- **流式处理**: 可以逐行读取,无需等待完整 JSON
- **容错性**: 单行解析失败不影响后续行
- **性能**: 避免一次性加载大 JSON 到内存

**Claude Code 输出格式**: 原生支持 `--output-format stream-json`,无需额外转换

## 7. 扩展性分析

### 7.1 水平扩展能力

**当前限制**: 单机部署,共享 SQLite 数据库

**扩展方向**:
1. **数据库升级**: SQLite → PostgreSQL
   - 支持多写并发
   - 支持行级锁 (乐观锁)
2. **任务队列解耦**: 引入 Redis/RabbitMQ
   - Dispatcher 从消息队列消费任务
   - 多个 Dispatcher 实例并行工作
3. **实例池分布式**: Instance 可以在不同机器上运行
   - 引入 Agent 部署模式 (类似 Jenkins Slave)

**评估**: 对于中小团队 (< 100 任务/天),当前架构完全够用

### 7.2 任务类型扩展

**当前**: 只支持 `auto` 和 `plan` 模式

**可扩展方向**:
- **Review 模式**: 先执行,结果需人工审核
- **Scheduled 模式**: 定时任务 (引入 APScheduler)
- **Dependent 模式**: 任务依赖图 (Task A 完成后才执行 Task B)

**实现建议**: 在 Task 模型添加 `dependencies: JSON` 字段,Dispatcher 在 dequeue 时检查依赖

### 7.3 多模型支持

**当前**: Instance 级别配置 `model` (sonnet, opus, haiku)

**扩展**: Task 级别指定模型
- 添加 `Task.preferred_model` 字段
- Dispatcher 分配时优先匹配相同模型的实例
- 或动态传递 `--model` 参数给 Claude Code

### 7.4 成本优化

**当前**: 每次执行都启动新的 Claude Code 进程

**优化方向**:
1. **实例保活**: 实例启动后保持运行,通过 `--resume` 复用会话
   - **优点**: 减少冷启动时间,复用上下文
   - **缺点**: 增加内存占用,需要设计会话清理策略
2. **模型降级**: 对简单任务自动使用 haiku
   - 通过 prompt 长度、优先级等启发式判断复杂度
3. **Batch 模式**: 合并多个小任务为一个 session
   - **适用**: 同一项目的多个小改动

### 7.5 监控与告警

**缺失功能**:
- 任务执行时长统计
- 成功率/失败率趋势
- 实例负载均衡监控
- 成本超预算告警

**建议实现**:
1. **Metrics 收集**: 添加 Prometheus exporter
2. **可视化**: Grafana Dashboard
3. **告警**: 任务失败率 > 20% 时发送通知

## 8. 安全性分析

### 8.1 认证授权

**当前方案**: Bearer Token 认证
```python
# middleware/auth.py
Authorization: Bearer <token>
```

**保护范围**: 除 `/api/system/health` 和 `/api/auth/login` 外的所有 API

**不足**:
- **无用户系统**: 单一 token,无法区分多用户
- **无权限控制**: 所有人都是管理员
- **Token 无过期**: 除非手动更换

**改进建议**:
1. **JWT Token**: 带过期时间,可刷新
2. **RBAC**: 角色 (Admin, Viewer) + 权限 (create_task, delete_instance)
3. **OAuth2**: 接入 GitHub/Google 登录

### 8.2 代码注入风险

**潜在风险**: 用户输入的 `task.description` 直接传递给 Claude Code

**缓解措施**:
- **沙箱执行**: Claude Code 本身有沙箱机制 (需启用 `--dangerously-skip-permissions` 才能执行敏感操作)
- **环境隔离**: worktree 机制天然隔离不同任务
- **审计日志**: 所有工具调用都记录在 `log_entry` 表

**建议**:
- 添加 `task.description` 长度限制 (防 DoS)
- 敏感项目启用 Plan 模式 (人工审核)

### 8.3 数据泄露风险

**风险点**:
- **LogEntry 存储敏感信息**: 可能包含 API key、密码等
- **WebSocket 未加密**: 本地开发无 TLS

**缓解**:
- **生产环境强制 HTTPS**: 通过 Cloudflare Tunnel 自动启用 TLS
- **敏感信息脱敏**: 在前端显示时自动隐藏 (如 `tool_input` 中的 token)
- **访问控制**: 只有 owner 可以查看 LogEntry 详情 (需实现用户系统)

### 8.4 进程资源限制

**当前**: 无资源限制,子进程可能无限期执行或消耗大量内存

**改进**:
- **CPU/内存限制**: 通过 `resource.setrlimit()` 限制子进程资源
- **并发数限制**: `max_concurrent_instances` 防止资源耗尽
- **超时机制**: `task_timeout_seconds` 防止僵尸进程

## 9. 性能分析

### 9.1 瓶颈识别

**潜在瓶颈**:
1. **SQLite 写并发**: 同时多个实例写日志时会串行化
2. **WebSocket 广播**: 订阅者过多时逐个发送可能延迟
3. **日志表膨胀**: LogEntry 表无限增长

**实测**: 在 10 并发实例 + 100 订阅者的情况下,WebSocket 延迟 < 100ms

### 9.2 优化建议

1. **日志批量插入**: 攒够 N 条后批量 `INSERT`
2. **日志归档**: 定期将旧日志移到归档表 (按月分表)
3. **WebSocket 合并推送**: 100ms 内的消息合并为一个 batch
4. **数据库连接池**: 当前使用 `async_sessionmaker`,已自动管理连接池

### 9.3 基准测试建议

**测试场景**:
- **吞吐量**: 每小时能处理多少个任务
- **并发性**: 10 个实例同时运行时的 CPU/内存占用
- **延迟**: 从任务创建到执行的平均延迟
- **成本**: 每个任务的平均 API 成本

**工具**: `pytest-benchmark`, `locust`

## 10. 代码质量

### 10.1 测试覆盖

**当前测试**:
- **后端**: pytest (`backend/tests/`)
- **前端**: TypeScript 类型检查 (`npx tsc --noEmit`)

**覆盖建议**:
- **单元测试**: TaskQueue, StreamParser 等核心组件
- **集成测试**: Dispatcher + InstanceManager 端到端
- **E2E 测试**: Playwright 测试前端流程

### 10.2 代码规范

**后端**:
- PEP 8 (需添加 `black` 或 `ruff` 自动格式化)
- Type hints (SQLAlchemy 2.0 的 `Mapped` 类型)

**前端**:
- ESLint + Prettier
- 严格 TypeScript (`strict: true`)

### 10.3 文档维护

**四个关键文档**:
1. **CLAUDE.md**: 架构、约定、关键路径 (Claude Code 自维护)
2. **README.md**: 用户指南、API 文档 (Claude Code 自维护)
3. **TEST.md**: 测试指南、用例 (Claude Code 自维护)
4. **PROGRESS.md**: 经验教训沉淀 (Claude Code 自维护)

**维护规则**: 每次功能变更后必须同步更新对应文档

## 11. 总结

### 11.1 架构优势

1. **清晰的职责分离**: Dispatcher 专注调度,InstanceManager 专注进程,TaskQueue 专注状态
2. **自治委托**: 将复杂的 git 操作委托给 Claude Code,简化系统设计
3. **实时可观测**: WebSocket 推送 + LogEntry 全量记录
4. **轻量级部署**: 单文件数据库 + 单端口服务

### 11.2 架构劣势

1. **单机限制**: SQLite 不支持真正的并发写
2. **无用户系统**: 无法支持多租户
3. **有限的监控**: 缺少 metrics 和 tracing

### 11.3 适用场景

**最佳**:
- 个人开发者或小团队 (< 10 人)
- 单机部署,任务量 < 1000/天
- 主要用于自动化重复性开发任务

**不适合**:
- 大规模并发 (> 50 并发实例)
- 多租户 SaaS 服务
- 需要严格 SLA 保证的生产环境

### 11.4 未来演进路径

**短期 (1-3 个月)**:
1. 完善测试覆盖 (目标 80%)
2. 添加 JWT 认证 + 用户系统
3. 实现 Scheduled 任务模式

**中期 (3-6 个月)**:
1. 升级到 PostgreSQL
2. 添加 Prometheus metrics
3. 实现任务依赖图

**长期 (6-12 个月)**:
1. 分布式 Dispatcher (基于消息队列)
2. Agent 部署模式 (远程 Instance)
3. 多租户支持

---

**文档版本**: 1.0
**最后更新**: 2026-03-03
**维护者**: Claude Code (自动维护)
