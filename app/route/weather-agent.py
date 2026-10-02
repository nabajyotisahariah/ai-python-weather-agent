from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/weather-agent", summary="Weather Agent", description="Returns the current Weather & forecast of the API.", tags=["System"], response_model_exclude_none=True)
async def weather_agent():
    """
    Health check endpoint to verify the API is running.
    Returns a simple JSON response indicating the health status.
    """
    return {"status": "ok"}
