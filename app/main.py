"""FastAPI app: REST API, plus Temporal workers running in the same process."""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings


def create_app(*, store=None, temporal=None, push=None, gemma=None, stt=None, tts=None,
               start_workers: bool = True) -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        from app.db import connect_store
        from flows.push import WebPushSender
        from flows.temporal import connect_temporal
        from flows.worker import reminder_worker, run_for

        app.state.settings = settings
        app.state.store = store or connect_store(settings)
        if store is None:
            await app.state.store.ensure_indexes()
        app.state.temporal = temporal or await connect_temporal(settings)
        app.state.push = push or WebPushSender(settings.vapid_private_key, settings.vapid_subject)
        app.state.workers = []
        runner = None
        if start_workers:
            app.state.workers.append(reminder_worker(app.state.temporal, app.state.store, app.state.push))
            runner = asyncio.create_task(run_for(app.state.workers, None))
        yield
        if runner:
            await asyncio.gather(*(w.shutdown() for w in app.state.workers), return_exceptions=True)
            await asyncio.gather(runner, return_exceptions=True)

    app = FastAPI(title="Kaagaz", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin], allow_methods=["*"],
                       allow_headers=["Authorization", "Content-Type"])

    @app.get("/api/health")
    async def health():
        return {"ok": True, "mode": settings.app_mode, "llm": settings.llm_backend,
                "stt": settings.stt_backend, "tts": settings.tts_backend,
                "push_key": settings.vapid_public_key}

    return app


app = create_app()
