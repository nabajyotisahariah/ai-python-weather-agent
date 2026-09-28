import asyncio
from app.services.weather_service import WeatherService

async def main():
    service = WeatherService()
    res = await service.get_langgraph_weather_report("noida")
    print(res)

asyncio.run(main())
