from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.server import router
from src.core.storage import Storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("promptforge")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.storage = Storage()
    logger.info("=" * 50)
    logger.info("  PromptForge v1.0.0")
    logger.info("  Professional Prompt Engineering Toolkit")
    logger.info("=" * 50)
    logger.info("Server starting up...")
    logger.info("API docs available at http://localhost:8000/docs")
    logger.info("Dashboard available at http://localhost:8000")
    logger.info("=" * 50)
    try:
        yield
    finally:
        storage = getattr(app.state, "storage", None)
        if storage is not None:
            storage.close()
        logger.info("Server shutting down...")


app = FastAPI(
    title="PromptForge",
    description="Professional Prompt Engineering Toolkit - Template management, A/B testing, evaluation and optimization",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(router, prefix="/api")

# Mount static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")


@app.get("/")
async def root():
    """Serve the main dashboard page."""
    return FileResponse("web/templates/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
