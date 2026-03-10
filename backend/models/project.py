from datetime import datetime

from sqlalchemy import Integer, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    git_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    has_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    local_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, cloning, ready, error
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    show_in_selector: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
