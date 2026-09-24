# Weather Assistant API

FastAPI service for current weather data and AI-generated weather summaries. Weather data is retrieved from [wttr.in](https://wttr.in), while summaries can be generated with CrewAI, LangGraph, AutoGen, or Google ADK.

The API uses Redis as an optional cache and exposes OpenAPI documentation through FastAPI.

## Features

- Current weather by city
- AI weather summaries through four agent integrations
- Redis caching for weather data and generated reports
- Health-check endpoint
- Pydantic request and response validation
- CORS support for API clients
- Structured logging and provider error handling
- Interactive Swagger UI and ReDoc documentation

## Requirements

- Python 3.11 or newer
- Redis 7 or newer for caching
- An OpenAI API key for CrewAI, LangGraph, and AutoGen
- A Google API key for Google ADK
- Docker Desktop, if running Redis or the API container with Docker

## Local Setup

Create and activate a virtual environment in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create the local environment file:

```powershell
Copy-Item .env.example .env
```

Update `.env` with valid provider credentials:

```env
environment=development
OPENAI_API_KEY=your-openai-api-key
OPENAI_API_MODEL=gpt-4o-mini
GOOGLE_API_KEY=your-google-api-key
GOOGLE_ADK_MODEL=gemini-3.5-flash-lite
WEATHER_API_URL=https://wttr.in
WEATHER_TIMEOUT_SECONDS=10
```

`OPENAI_API_KEY` is required in development. `GOOGLE_API_KEY` is required when using the Google ADK endpoint. Redis defaults to `redis://localhost:6379/0`; set `REDIS_URL` when Redis is running elsewhere.

## Start Redis

The Compose file starts Redis only:

```powershell
docker compose up -d redis
```

Stop Redis when it is no longer needed:

```powershell
docker compose down
```

The API can also run without Redis. In that case, requests bypass the cache and call the upstream weather or agent provider directly.

## Run the API

Start the development server from the project root:

```powershell
uvicorn app.main:app --reload
```

Alternatively:

```powershell
python app/main.py
```

The API is available at `http://localhost:8000`.

Documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Run with Docker

Build the image:

```powershell
docker build -t weather-assistant-api .
```

Run the API using the local environment file:

```powershell
docker run --rm --env-file .env -p 8000:8000 weather-assistant-api
```

When the API runs inside a container, `REDIS_URL` must point to a Redis host reachable from that container. For example, use `redis` when both services run on the same Docker network.

## Run Tests

Run the complete test suite from the project root:

```powershell
python -m pytest -q
```

Run tests with verbose output:

```powershell
python -m pytest -v
```

Run one test:

```powershell
python -m pytest tests/test_api.py::test_autogen_weather_returns_agent_response -q
```

## API Endpoints

All application endpoints use the `/api/v1` prefix. The `city` query parameter is required for weather endpoints.

### Health check

```http
GET /api/v1/health
```

Response:

```json
{
  "status": "ok"
}
```

### Current weather

```http
GET /api/v1/weather?city=Delhi
```

PowerShell:

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/weather?city=Delhi"
```

Example response:

```json
{
  "city": "Delhi",
  "temperature": "25",
  "feels_like": "26",
  "humidity": "60",
  "description": "Sunny",
  "wind_speed": "10"
}
```

### AI weather summaries

The following endpoints return an object with `status` and `message` fields:

```http
GET /api/v1/weather/crewai?city=Delhi
GET /api/v1/weather/langgraph?city=Delhi
GET /api/v1/weather/autogen?city=Delhi
GET /api/v1/weather/google-adk?city=Delhi
```

PowerShell example:

```powershell
Invoke-RestMethod "http://localhost:8000/api/v1/weather/autogen?city=Delhi"
```

Example response:

```json
{
  "status": "ok",
  "message": "The current weather in Delhi is ...",
  "isCached": false
}
```

## Error Responses

- `404`: the weather provider could not find the requested city
- `422`: the `city` query parameter is missing or invalid
- `502`: the weather or AI provider is unavailable
- `500`: an unexpected application error occurred

Provider failures are logged and returned as safe API responses instead of exposing internal exceptions.

## Project Structure

```text
app/
├── agents/              # CrewAI, LangGraph, AutoGen, and Google ADK agents
├── route/               # FastAPI route handlers
├── schema/              # Pydantic request and response models
├── services/            # Weather service and service interface
├── tools/               # Agent weather tools
├── config.py            # Environment-backed settings
├── main.py              # FastAPI application
└── utils/               # Logging and Redis cache helpers
helm-config/             # Kubernetes Helm chart
tests/                   # API and service tests
```

## Kubernetes

The `helm-config` directory contains the Helm chart for deploying the API. Update the image repository, tag, ingress host, and runtime secrets in the chart values before deploying to a cluster.

```powershell
helm upgrade --install weather-agent .\helm-config
```
