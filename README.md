# Weather Assistant API

A FastAPI service that retrieves current weather data from [wttr.in](https://wttr.in) and can produce a natural-language weather summary through CrewAI.

## Features

- Current weather data for a city
- CrewAI-generated weather summaries
- Health-check endpoint
- Pydantic request and response schemas
- CORS enabled for API clients
- Interactive API documentation through FastAPI

## Requirements

- Python 3.11 or newer
- An OpenAI API key for the CrewAI endpoint

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

Update `.env` with your OpenAI API key:

```env
OPENAI_API_KEY=your-api-key
OPENAI_API_MODEL=gpt-4o-mini
WEATHER_API_URL=https://wttr.in
WEATHER_TIMEOUT_SECONDS=10
```

## Run the API

Start the development server:

```powershell
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`.

Interactive documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

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

## Project structure

```text
app/
├── agents/crewai/       # CrewAI agent and crew factory
├── route/               # FastAPI route handlers
├── schema/              # Pydantic request and response models
├── services/            # Service interface and weather implementation
├── tools/crewai/        # CrewAI weather tool
├── config.py            # Environment-backed settings
├── main.py              # FastAPI application
└── utils/               # Logging helpers
```

## Error responses

- `404`: city was not found
- `422`: invalid or missing `city` query parameter
- `502`: weather provider or CrewAI service is unavailable
