# Weather Assistant API

A FastAPI service that retrieves current weather data from [wttr.in](https://wttr.in) and can produce natural-language weather summaries through CrewAI, LangGraph, AutoGen, or Google ADK.

## Features

- Current weather data for a city
- CrewAI-generated weather summaries
- LangGraph-generated weather summaries
- AutoGen-generated weather summaries
- Google ADK-generated weather summaries
- Health-check endpoint
- Pydantic request and response schemas
- CORS enabled for API clients
- Redis caching for current weather and generated weather reports
- Interactive API documentation through FastAPI

## Requirements

- Python 3.11 or newer
- Redis 7 or newer for caching
- An OpenAI API key for the CrewAI, LangGraph, and AutoGen endpoints
- A Google API key for the Google ADK endpoint

## Setup

Create and activate a virtual environment in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
pip install -r requirements.txt
```

Create a `.env` file from the example:

```powershell
Copy-Item .env.example .env
```

Update `.env` with your model provider keys and weather settings:

```env
OPENAI_API_KEY=your-api-key
OPENAI_API_MODEL=gpt-4o-mini
GOOGLE_API_KEY=your-google-api-key
GOOGLE_ADK_MODEL=gemini-2.0-flash
WEATHER_API_URL=https://wttr.in
WEATHER_TIMEOUT_SECONDS=10
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL_SECONDS=300
```

Current weather responses and CrewAI, LangGraph, AutoGen, and Google ADK reports
are cached in Redis for the configured TTL. Cache entries are separated by city
and provider. If Redis is unavailable, the API continues by calling the weather
or agent provider directly.

For local API development, start Redis separately and keep
`REDIS_URL=redis://localhost:6379/0`. Docker Compose starts Redis automatically
and configures the API to use the internal `redis` hostname.

## Run the API

Start the development server with Uvicorn:

```powershell
uvicorn app.main:app --reload
```

You can also start the API directly:

```powershell
python app/main.py
```

Start the API and Redis together with Docker Compose:

```powershell
docker compose up --build
```

The API is available at `http://localhost:8000` when started directly, or at
`http://localhost` when started with Docker Compose.

Interactive documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Run tests

Activate the virtual environment and run the test suite from the project root:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

Run tests with detailed output:

```powershell
python -m pytest -v
```

Run a specific test:

```powershell
python -m pytest tests/test_api.py::test_autogen_weather_returns_agent_response -q
```

## Endpoints

### Health check

```http
GET /api/v1/health
```

Example response:

```json
{
	"status": "ok"
}
```

### Current weather

```http
GET /api/v1/weather?city=delhi
```

Example response:

```json
{
	"city": "delhi",
	"temperature": "36",
	"feels_like": "36",
	"humidity": "24",
	"description": "Sunny",
	"wind_speed": "7"
}
```

PowerShell example:

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/weather?city=delhi"
```

### CrewAI weather summary

```http
GET /api/v1/weather/crewai?city=delhi
```

Example response:

```json
{
	"status": "ok",
	"message": "The current weather in Delhi is as follows: ..."
}
```

PowerShell example:

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/weather/crewai?city=delhi"
```

### LangGraph weather summary

```http
GET /api/v1/weather/langgraph?city=delhi
```

PowerShell example:

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/weather/langgraph?city=delhi"
```

### AutoGen weather summary

```http
GET /api/v1/weather/autogen?city=delhi
```

PowerShell example:

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/weather/autogen?city=delhi"
```

### Google ADK weather summary

```http
GET /api/v1/weather/google-adk?city=delhi
```

PowerShell example:

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/weather/google-adk?city=delhi"
```

## Project structure

```text
app/
├── agents/              # CrewAI, LangGraph, AutoGen, and Google ADK agents
├── route/               # FastAPI route handlers
├── schema/              # Pydantic request and response models
├── services/            # Service interface and weather implementation
├── tools/               # Weather tools shared by the agent integrations
├── config.py            # Environment-backed settings
├── main.py              # FastAPI application
└── utils/               # Logging and Redis cache helpers
```

## Error responses

- `404`: city was not found
- `422`: invalid or missing `city` query parameter
- `502`: weather provider or AI service is unavailable
