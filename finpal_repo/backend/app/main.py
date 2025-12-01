from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.v0.routers import  api_router
from.core.config import SQLALCHEMY_DATABASE_URL,settings
from contextlib import asynccontextmanager
from app.db.__init__db import init_db
from datetime import datetime,timezone
from fastapi.responses import JSONResponse


@asynccontextmanager
async def lifespan(app:FastAPI):
    #startup
    init_db()
    print("Database initialized")
    yield

    #shutdown
    print("Shutting down FinPal backend...")


app=FastAPI(lifespan=lifespan,title="Finpal Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


app.include_router(api_router,prefix='')

@app.get("/")
async def root():
    return {
        "message": "FinPal API - Privacy-first Financial Wellness",
        "version": "1.0.0",
        "status": "healthy",
        "docs": "/docs",
        "endpoints": {
            "authentication": "/api/v0/auth",
            "users": "/api/v0/users",
            "transactions": "/api/v0/transactions",
            "sms": "/api/v0/sms",
            "recommendations": "/api/v0/recommendations",
            "challenges": "/api/v0/challenges"
        }
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.DEBUG else "An error occurred"
        }
    )
