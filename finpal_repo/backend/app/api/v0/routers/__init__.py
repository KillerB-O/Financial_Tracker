from fastapi import APIRouter
from . import auth, users, transaction
from .sms import router as sms_router
from .recommendations import router as recommendations_router
from .challenges import router as challenges_router

# Create main API router
api_router = APIRouter()

# Include all routers with their prefixes
api_router.include_router(auth.router)  # /auth
api_router.include_router(users.router)  # /users
api_router.include_router(transaction.router)  # /transactions
api_router.include_router(sms_router)  # /sms
api_router.include_router(recommendations_router)  # /recommendations
api_router.include_router(challenges_router)  # /challenges

# Export for use in main app
__all__ = ["api_router"]

