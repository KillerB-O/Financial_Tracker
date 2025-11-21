from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.v0.routers import  auth as auth_router
from.core.config import SQLALCHEMY_DATABASE_URL,settings
from contextlib import asynccontextmanager
from app.db.__init__db import init_db


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

app.include_router(auth_router.router)

@app.get('/')
async def home():
    return "Hello Welcome To my Website"

@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.PROJECT_NAME}