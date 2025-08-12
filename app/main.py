from fastapi import FastAPI
from app.api.endpoints.review import router as review_router
from app.core.logging import setup_logger  
import traceback
import sys

logger = setup_logger()  

app = FastAPI(title="Autonomous Github PR Code Review Agent")

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 FastAPI application started")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 FastAPI application shutting down")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print("❗ Internal server error:")
    traceback.print_exc(file=sys.stdout)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
    )

app.include_router(review_router, prefix="/api")
