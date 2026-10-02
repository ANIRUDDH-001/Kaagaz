"""Temporal Cloud connection and task queue names."""
import os
import socket
import uuid
from datetime import timedelta
from functools import lru_cache

from temporalio.client import Client

TASK_QUEUE = "kaagaz"   # reminders: polled by Render and by GitHub Actions
# Upper bound on processing one upload (5 Gemma attempts of <= 300 s plus backoff). If the process
# holding the upload dies, Temporal closes the workflow after this instead of leaving it stranded.
PROCESS_TIMEOUT = timedelta(minutes=30)


@lru_cache
def ai_task_queue() -> str:
    # Uploads sit on this process's disk, so only this process may process them. A shared queue
    # would let Render pick up the private-mode laptop's upload (or an old deploy's) and fail it.
    # The random part keeps a restarted container that reuses a pid off the old queue.
    return f"kaagaz-ai-{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"


async def connect_temporal(settings) -> Client:
    if not settings.temporal_address:
        raise RuntimeError("TEMPORAL_ADDRESS is not set")
    if settings.temporal_api_key:
        return await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace,
                                    api_key=settings.temporal_api_key, tls=True)
    return await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
