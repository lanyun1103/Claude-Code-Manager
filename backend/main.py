import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import settings
from backend.database import init_db, async_session
from backend.api.tasks import router as tasks_router
from backend.api.instances import router as instances_router, dispatcher_router
from backend.api.system import router as system_router
from backend.api.ws import router as ws_router
from backend.api.voice import router as voice_router
from backend.api.auth import router as auth_router
from backend.api.chat import router as chat_router
from backend.api.projects import router as projects_router
from backend.api.settings import router as settings_router
from backend.middleware.auth import TokenAuthMiddleware
from backend.services.ws_broadcaster import WebSocketBroadcaster
from backend.services.instance_manager import InstanceManager
from backend.services.ralph_loop import RalphLoop
from backend.services.dispatcher import GlobalDispatcher

# Global singletons
broadcaster = WebSocketBroadcaster()
instance_manager = InstanceManager(db_factory=async_session, broadcaster=broadcaster)
ralph_loop = RalphLoop(
    db_factory=async_session,
    instance_manager=instance_manager,
    broadcaster=broadcaster,
)
dispatcher = GlobalDispatcher(
    db_factory=async_session,
    instance_manager=instance_manager,
    broadcaster=broadcaster,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    if settings.auto_start_dispatcher:
        await dispatcher.start()
    yield
    await dispatcher.stop()


app = FastAPI(title="Claude Code Manager", version="0.1.0", lifespan=lifespan)

app.add_middleware(TokenAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks_router)
app.include_router(instances_router)
app.include_router(system_router)
app.include_router(ws_router)
app.include_router(voice_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(projects_router)
app.include_router(settings_router)
app.include_router(dispatcher_router)

# Serve frontend static files in production
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve index.html for all non-API routes (SPA fallback)."""
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIST / "index.html"))
