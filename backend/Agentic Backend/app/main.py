from fastapi import FastAPI

app = FastAPI(
    title="SELVIA API",
    description="Software Engineering Learning & Virtual Intelligence Assistant",
    version="0.1.0",
)


@app.get("/")
async def root():
    return {
        "name": "SELVIA",
        "status": "running"
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}