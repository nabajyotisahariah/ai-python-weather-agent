from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/health", summary="Health Check", description="Returns the current health status of the API.", tags=["System"], response_model_exclude_none=True)
async def health_check():
    """
    Health check endpoint to verify the API is running.
    Returns a simple JSON response indicating the health status.
    """
    return {"status": "ok"}
