"""Creates the FastAPI app, registers routers and error handlers."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import engine
from app.models import Base


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Create the database tables when the API starts."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="HealthTrack API",
    description="Patient symptom tracker: log symptoms, retrieve them by date and see insights.",
    version="0.1.0",
    lifespan=lifespan,
)
