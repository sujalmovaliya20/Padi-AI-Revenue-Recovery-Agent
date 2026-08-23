"""Health-check & hello-world endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/")
async def root():
    return {"message": "Revenue Recovery Agent API is running 🚀"}


@router.get("/health")
async def health_check():
    return {"status": "healthy"}
