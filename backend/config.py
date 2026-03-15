from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./claude_manager.db"
    openai_api_key: str = ""
    auth_token: str = ""
    max_concurrent_instances: int = 5
    claude_binary: str = "claude"
    default_model: str = "opus"
    host: str = "0.0.0.0"
    port: int = 8000
    workspace_dir: str = "~/Projects"
    auto_start_dispatcher: bool = True
    merge_push_retries: int = 3
    auto_push_to_origin: bool = True
    task_timeout_seconds: int = 1800  # 30 minutes
    git_ssh_key_path: str = ""  # Instance-level SSH key, fallback when project has none

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
