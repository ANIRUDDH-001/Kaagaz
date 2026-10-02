"""FastAPI app: REST API, plus Temporal workers running in the same process."""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import router
from app.config import get_settings
from app.ratelimit import HourlyLimiter

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def create_app(*, store=None, temporal=None, push=None, gemma=None, stt=None, tts=None,
               start_workers: bool = True) -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        from ai.gemma import make_gemma
        from ai.stt import make_stt
        from ai.tts import make_tts
        from app.db import connect_store
        from app.inputs import InputStore
        from flows.ai_activities import AIActivities
        from flows.push import WebPushSender
        from flows.temporal import ai_task_queue, connect_temporal
        from flows.worker import ai_worker, reminder_worker, run_for

        app.state.settings = settings
        app.state.store = store or connect_store(settings)
        if store is None:
            await app.state.store.ensure_indexes()
        app.state.temporal = temporal or await connect_temporal(settings)
        app.state.push = push or WebPushSender(settings.vapid_private_key, settings.vapid_subject)
        app.state.inputs = InputStore(settings.upload_dir)
        app.state.ai_queue = ai_task_queue()
        app.state.limiter = HourlyLimiter(limit=15)              # Gemma calls per household
        app.state.global_limiter = HourlyLimiter(limit=200)      # Gemma calls, all demo households
        app.state.ip_limiter = HourlyLimiter(limit=30)           # Gemma calls per address
        app.state.household_ip_limiter = HourlyLimiter(limit=10) # new households per address
        app.state.tts_limiter = HourlyLimiter(limit=40)          # server voice per household
        app.state.tts_global_limiter = HourlyLimiter(limit=200)  # server voice, all demo households
        app.state.tts = tts if tts is not None else make_tts(settings, app.state.store)
        app.state.workers = []
        runner = None
        if start_workers:
            acts = AIActivities(app.state.inputs, app.state.store, gemma or make_gemma(settings),
                                stt or make_stt(settings))
            app.state.workers = [reminder_worker(app.state.temporal, app.state.store, app.state.push),
                                 ai_worker(app.state.temporal, acts)]
            runner = asyncio.create_task(run_for(app.state.workers, None))

        async def sweep_forever():
            while True:
                await asyncio.sleep(300)
                app.state.inputs.sweep()

        sweeper = asyncio.create_task(sweep_forever())
        yield
        sweeper.cancel()
        if runner:
            await asyncio.gather(*(w.shutdown() for w in app.state.workers), return_exceptions=True)
            await asyncio.gather(runner, return_exceptions=True)

    app = FastAPI(title="Kaagaz", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.frontend_origin.split(",") if o.strip()], allow_methods=["*"],
                       allow_headers=["Authorization", "Content-Type"])

    @app.get("/api/health")
    async def health():
        return {"ok": True, "mode": settings.app_mode, "llm": settings.llm_backend,
                "stt": settings.stt_backend, "tts": settings.tts_backend,
                "push_key": settings.vapid_public_key}

    @app.middleware("http")
    async def revalidate_web_files(request, call_next):
        response = await call_next(request)
        if not request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-cache"   # ETag check each time: a new deploy is seen at once
        return response

    app.include_router(router)
    if WEB_DIR.exists():
        # Locally one process serves everything; on Render the static site serves web/.
        app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")

    return app


app = create_app()
