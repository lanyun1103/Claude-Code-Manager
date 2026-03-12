import asyncio
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db, async_session
from backend.models.project import Project
from backend.models.global_settings import GlobalSettings
from backend.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from backend.services.git_config import merge_git_config, settings_to_dict

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).order_by(Project.name))
    return list(result.scalars().all())


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(body: ProjectCreate, db: AsyncSession = Depends(get_db)):
    # Check duplicate name
    existing = await db.execute(select(Project).where(Project.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Project '{body.name}' already exists")

    workspace = os.path.expanduser(settings.workspace_dir)
    local_path = os.path.join(workspace, body.name)
    has_remote = body.git_url is not None and body.git_url.strip() != ""

    project = Project(
        name=body.name,
        git_url=body.git_url if has_remote else None,
        has_remote=has_remote,
        default_branch=body.default_branch,
        local_path=local_path,
        status="pending",
        git_author_name=body.git_author_name,
        git_author_email=body.git_author_email,
        git_credential_type=body.git_credential_type,
        git_ssh_key_path=body.git_ssh_key_path,
        git_https_username=body.git_https_username,
        git_https_token=body.git_https_token,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    global_cfg = await db.get(GlobalSettings, 1)
    git_config = merge_git_config(_extract_git_config(project), settings_to_dict(global_cfg))
    if has_remote:
        asyncio.create_task(_clone_repo(project.id, body.git_url, local_path, body.name, body.default_branch, git_config))
    else:
        asyncio.create_task(_init_local_repo(project.id, local_path, body.name, body.default_branch, git_config))

    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int, body: ProjectUpdate, db: AsyncSession = Depends(get_db)
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    updates = body.model_dump(exclude_unset=True)
    # Auto-sync has_remote when git_url is set
    if "git_url" in updates and updates["git_url"] and "has_remote" not in updates:
        updates["has_remote"] = True
    for key, value in updates.items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)

    # Apply git config to local repo immediately if any git fields changed
    git_fields = {"git_author_name", "git_author_email", "git_credential_type",
                  "git_ssh_key_path", "git_https_username", "git_https_token"}
    if git_fields & updates.keys() and project.local_path and os.path.isdir(project.local_path):
        await _apply_git_config(project.local_path, _extract_git_config(project))

    return project


@router.delete("/{project_id}")
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    await db.delete(project)
    await db.commit()
    return {"ok": True}


@router.post("/{project_id}/reclone")
async def reclone_project(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if not project.has_remote:
        raise HTTPException(400, "Cannot reclone a local project")
    project.status = "pending"
    project.error_message = None
    await db.commit()
    global_cfg = await db.get(GlobalSettings, 1)
    git_config = merge_git_config(_extract_git_config(project), settings_to_dict(global_cfg))
    asyncio.create_task(_clone_repo(project_id, project.git_url, project.local_path, project.name, project.default_branch, git_config))
    return {"ok": True}


def _extract_git_config(project) -> dict:
    """Extract git config fields from a Project instance into a plain dict."""
    return {
        "git_author_name": project.git_author_name,
        "git_author_email": project.git_author_email,
        "git_credential_type": project.git_credential_type,
        "git_ssh_key_path": project.git_ssh_key_path,
        "git_https_username": project.git_https_username,
        "git_https_token": project.git_https_token,
    }


async def _apply_git_config(local_path: str, git_config: dict):
    """Write per-repo git config after clone/init so commits use the correct identity."""
    async def _git_config(key: str, value: str):
        proc = await asyncio.create_subprocess_exec(
            "git", "config", key, value,
            cwd=local_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

    if git_config.get("git_author_name"):
        await _git_config("user.name", git_config["git_author_name"])
    if git_config.get("git_author_email"):
        await _git_config("user.email", git_config["git_author_email"])

    ctype = git_config.get("git_credential_type")
    if ctype == "ssh" and git_config.get("git_ssh_key_path"):
        key_path = git_config["git_ssh_key_path"]
        ssh_cmd = f"ssh -i {key_path} -o StrictHostKeyChecking=no"
        await _git_config("core.sshCommand", ssh_cmd)
    elif ctype == "https" and git_config.get("git_https_token"):
        # Store credentials in the repo's local credential store so git push/pull can auth.
        # We write a plaintext .git/credentials file and point credential.helper at it.
        import pathlib
        creds_path = pathlib.Path(local_path) / ".git" / "credentials"
        username = git_config.get("git_https_username") or "oauth2"
        token = git_config["git_https_token"]
        # Build credential lines for both https and http schemes
        creds_content = f"https://{username}:{token}@github.com\nhttp://{username}:{token}@github.com\n"
        creds_path.write_text(creds_content)
        await _git_config("credential.helper", f"store --file {creds_path}")


def _generate_claude_md(project_name: str, git_url: str | None, default_branch: str) -> str:
    """Generate a CLAUDE.md template for a new project."""
    remote_info = git_url if git_url else "无（纯本地项目）"
    return f"""# {project_name} — 项目指南

> **重要：Claude 必须自主维护本文件。** 架构或约定变化时更新，保持简洁。

## Git 信息

- Remote: {remote_info}
- 默认分支: {default_branch}

## 任务生命周期

你收到任务后，按以下 9 步流程自主完成：

1. **领取任务** — 你已被分配任务，阅读本文件和项目代码理解上下文
2. **创建工作区**:
   - `git fetch origin`（如有 remote）
   - `git worktree add -b task-<简短描述> .claude-manager/worktrees/task-<简短描述> origin/{default_branch}`
   - 进入 worktree 目录工作（后续所有操作在 worktree 中）
   - 如果 worktree 创建失败，直接在当前分支工作
3. **实现功能** — 编写代码，确保可运行
4. **提交代码** — `git add` + `git commit`，commit message 简洁描述改动
5. **Merge + 测试**:
   - `git fetch origin && git merge origin/{default_branch}`（集成最新代码，如有 remote）
   - 运行测试（如有测试命令）
6. **自动合并到 {default_branch}**（如有 remote）:
   - `git fetch origin {default_branch}`
   - `git rebase origin/{default_branch}`，如果冲突则自行 resolve
   - 如果成功：`git checkout {default_branch} && git merge <task-branch> && git push origin {default_branch}`
   - 如果这一步有任何失败，退回到步骤 5 重试
   - （纯本地项目跳过本步）
7. **标记完成** — 更新文档（必须在清理之前，防止进程被杀时状态丢失）
8. **清理** — 回到项目根目录:
   - `git worktree remove .claude-manager/worktrees/<worktree名>`
   - `git branch -D <task-branch>`
   - 如有 remote: `git push origin --delete <task-branch>`
9. **经验沉淀** — 在 PROGRESS.md 记录经验教训（可选）

### 冲突处理

rebase 发生冲突时：
1. 查看冲突文件: `git diff --name-only --diff-filter=U`
2. 逐个解决冲突
3. `git add <resolved-files> && git rebase --continue`
4. 如果无法解决: `git rebase --abort`，退回步骤 5

### 状态判断

- 通过 `git remote -v` 判断是否有 remote
- 有 remote → 必须完成步骤 6（merge + push）
- 无 remote → 跳过步骤 5 的 fetch、步骤 6 和步骤 8 的远程分支删除

## 文件维护规则

> **以下文件都由 Claude Code 自主维护，每次功能变更后必须同步更新。**

- **CLAUDE.md**（本文件）：架构、约定、关键路径变化时更新，只改变化的部分，保持简洁
- **README.md**：面向用户的文档，功能、使用流程变化时同步更新，保持与实际代码一致
- **TEST.md**：测试指南，新增功能时同步添加测试用例和文档
- **PROGRESS.md**：见下方「经验教训沉淀」

## 测试规范

**开发时必须主动使用测试，不是事后补充！**

- **改代码前**：先跑测试，确认基线全绿
- **改代码后**：再跑一遍确认无回归
- **新增功能**：同步新增测试用例，更新 TEST.md
- **修 bug**：先写复现 bug 的测试（红），修复后确认变绿

## 经验教训沉淀

每次遇到问题或完成重要改动后，要在 PROGRESS.md 中记录：
- 遇到了什么问题
- 如何解决的
- 以后如何避免
- **必须附上 git commit ID**

**同样的问题不要犯两次！**

## 注意事项

- 在 worktree 中工作时，不要切换到其他分支
- 完成任务后确保代码可运行、测试通过
"""


async def _clone_repo(project_id: int, git_url: str, local_path: str, project_name: str, default_branch: str, git_config: dict | None = None):
    """Clone a git repo in the background."""
    async with async_session() as db:
        await db.execute(
            update(Project).where(Project.id == project_id).values(status="cloning")
        )
        await db.commit()

    try:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        if os.path.isdir(local_path):
            # Already exists, just fetch
            proc = await asyncio.create_subprocess_exec(
                "git", "fetch", "--all",
                cwd=local_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"git fetch failed: {stderr.decode()}")
        else:
            proc = await asyncio.create_subprocess_exec(
                "git", "clone", git_url, local_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"git clone failed: {stderr.decode()}")

        # Apply per-repo git config (author identity + credentials)
        if git_config:
            await _apply_git_config(local_path, git_config)

        # Generate CLAUDE.md if not exists
        claude_md_path = os.path.join(local_path, "CLAUDE.md")
        if not os.path.exists(claude_md_path):
            with open(claude_md_path, "w") as f:
                f.write(_generate_claude_md(project_name, git_url, default_branch))

        async with async_session() as db:
            await db.execute(
                update(Project).where(Project.id == project_id).values(status="ready")
            )
            await db.commit()

    except Exception as e:
        async with async_session() as db:
            await db.execute(
                update(Project)
                .where(Project.id == project_id)
                .values(status="error", error_message=str(e)[:1000])
            )
            await db.commit()


async def _init_local_repo(project_id: int, local_path: str, project_name: str, default_branch: str, git_config: dict | None = None):
    """Initialize a local git repo (no remote)."""
    async with async_session() as db:
        await db.execute(
            update(Project).where(Project.id == project_id).values(status="cloning")
        )
        await db.commit()

    try:
        os.makedirs(local_path, exist_ok=True)

        if not os.path.isdir(os.path.join(local_path, ".git")):
            # git init
            proc = await asyncio.create_subprocess_exec(
                "git", "init", "-b", default_branch,
                cwd=local_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"git init failed: {stderr.decode()}")

            # Apply per-repo git config before first commit so author is correct
            if git_config:
                await _apply_git_config(local_path, git_config)

            # Generate CLAUDE.md
            claude_md_path = os.path.join(local_path, "CLAUDE.md")
            with open(claude_md_path, "w") as f:
                f.write(_generate_claude_md(project_name, None, default_branch))

            # Initial commit
            proc = await asyncio.create_subprocess_exec(
                "git", "add", "CLAUDE.md",
                cwd=local_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            proc = await asyncio.create_subprocess_exec(
                "git", "commit", "-m", "Initial commit with CLAUDE.md",
                cwd=local_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"git commit failed: {stderr.decode()}")

        async with async_session() as db:
            await db.execute(
                update(Project).where(Project.id == project_id).values(status="ready")
            )
            await db.commit()

    except Exception as e:
        async with async_session() as db:
            await db.execute(
                update(Project)
                .where(Project.id == project_id)
                .values(status="error", error_message=str(e)[:1000])
            )
            await db.commit()
