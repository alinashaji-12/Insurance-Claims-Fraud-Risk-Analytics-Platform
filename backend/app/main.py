"""ClaimGuard AI — FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import claims, network, stats
from app.core.config import get_settings
from app.core.database import init_db
from app.seed import seed_demo_if_empty

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    # Free-tier SQLite is wiped on redeploy/spin-down; load small committed demo.
    seed_demo_if_empty()
    yield


app = FastAPI(
    title="ClaimGuard AI",
    description="Insurance Claims Fraud & Risk Analytics Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(claims.router)
app.include_router(network.router)
app.include_router(stats.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "ClaimGuard AI API"}
