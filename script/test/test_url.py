import httpx
import asyncio

async def test_api():
    url = "http://localhost:8000/api/v1/weather/agent?query=What is the delhi's todays weather & weather forecast"
    print("Testing URL:", url)
    # Actually just parsing the URL like FastAPI would:
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    print("Parsed query string:", qs)

asyncio.run(test_api())