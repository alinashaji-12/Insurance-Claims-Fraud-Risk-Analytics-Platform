"""ClaimGuard AI — FastAPI application entrypoint."""

from fastapi import FastAPI

app = FastAPI(
    title="ClaimGuard AI",
    description="Insurance Claims Fraud & Risk Analytics Platform",
    version="0.1.0",
)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "ClaimGuard AI API"}
