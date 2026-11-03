"""Creates the FastAPI app, registers routers and error handlers."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import insights, symptoms
from app.db import engine
from app.errors import register_error_handlers
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

register_error_handlers(app)
app.include_router(symptoms.router)
app.include_router(insights.router)
