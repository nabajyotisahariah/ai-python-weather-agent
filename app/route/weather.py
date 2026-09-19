import os

import httpx
from fastapi import APIRouter, HTTPException, Query


router = APIRouter()


@router.get("/weather")
async def get_weather(
	city: str = Query(..., min_length=1, description="City to get weather for"),
):
	"""Return the current weather for a city using OpenWeatherMap."""
	api_key = os.getenv("OPENWEATHER_API_KEY")
	if not api_key:
		raise HTTPException(status_code=500, detail="OPENWEATHER_API_KEY is not configured")

	url = "https://api.openweathermap.org/data/2.5/weather"
	params = {"q": city, "appid": api_key, "units": "metric"}

	try:
		async with httpx.AsyncClient() as client:
			response = await client.get(url, params=params, timeout=10.0)
	except httpx.HTTPError as exc:
		raise HTTPException(status_code=502, detail="Weather service unavailable") from exc

	if response.status_code == 404:
		raise HTTPException(status_code=404, detail="City not found")
	if response.status_code != 200:
		raise HTTPException(status_code=502, detail="Weather service returned an error")

	data = response.json()
	return {
		"city": data["name"],
		"country": data["sys"]["country"],
		"temperature": data["main"]["temp"],
		"feels_like": data["main"]["feels_like"],
		"humidity": data["main"]["humidity"],
		"description": data["weather"][0]["description"],
		"wind_speed": data["wind"]["speed"],
	}
