from fastapi import APIRouter, Depends, HTTPException
import logging

from app.guardrails.hitl_guardrails import (
    needs_location_clarification,
    requires_action_approval,
)
from app.guardrails.input_guardrails import GuardrailViolation, validate_query
from app.schema.hitl import HITLResponse, HITLStatus
from app.schema.weather import AgentResponse, WeatherRequest
from app.services.hitl_service import HITLService, get_hitl_service
from app.services.weather_service import (
    CityNotFoundError,
    WeatherProviderError,
)
from app.services.interface.weather_agent_interface import WeatherAgentInterface
from app.services.weather_agent_service import WeatherAgentService
from app.utils.response import generic_api_response

router = APIRouter()

logger = logging.getLogger(__name__)

weather_agent_service: WeatherAgentInterface = WeatherAgentService()

def get_weather_agent_service() -> WeatherAgentInterface:
    return weather_agent_service

@router.post("/weather/agent", summary="Weather Agent (POST)", description="Returns the current Weather & forecast of the API using a JSON body.", tags=["System"], response_model_exclude_none=True)
async def post_weather_forecast_route(
    request: WeatherRequest,
    service: WeatherAgentInterface = Depends(get_weather_agent_service),
) -> AgentResponse:
    """Return the current weather & weather forecast for a city using a POST request."""
    query_val = request.query if request.query is not None else request.city
    
    try:
        query_val = validate_query(query_val)
        user_id = "default_user".lower()  # Replace with actual user ID if available
        session_id = request.session_id.lower() if request.session_id is not None else None # Replace with actual session ID if available

        if(session_id is None or len(session_id) <= 5):
            logger.warning("User ID or Session ID is None or invalid. Using default values.")
            raise HTTPException("Session ID is None or invalid")
    
        logger.info("Fetching current weather for city (POST): %s", query_val)
        return await service.process_weather_query(query_val, session_id=session_id, user_id=user_id)

    except GuardrailViolation as exc:
        return generic_api_response(400, "fail", str(exc))
    except CityNotFoundError as exc:
        return generic_api_response(404, "fail", str(exc))
    except HTTPException as exc:
        return generic_api_response(400, "fail", str(exc))
    except Exception as exc:
        logger.error("Unexpected error: %s", str(exc))
        return generic_api_response(400, "fail", str(exc))

@router.post("/weather/agent/hitl", response_model=HITLResponse)
async def post_weather_agent_hitl_route(
    request: WeatherRequest,
    service: WeatherAgentInterface = Depends(
        get_weather_agent_service
    ),
    hitl: HITLService = Depends(get_hitl_service),
) -> HITLResponse:
    try:
 
        query = request.query or request.city
        if not query:
            raise HTTPException(
                status_code=422,
                detail="A weather query or city is required.",
            )

        query = validate_query(query)

        # Replace these placeholders with authenticated identity
        # and a server-validated session.
        user_id = "default_user"
        session_id = request.session_id.lower() if request.session_id else None

        if not session_id or len(session_id) <= 5:
            raise HTTPException(
                status_code=400,
                detail="A valid session ID is required.",
            )

        context = await service.get_context(
            session_id=session_id,
            user_id=user_id,
        )

        # 1. Require human authorization for consequential actions.
        if requires_action_approval(query):
            pending = await hitl.create_pending_request(
                query=query,
                user_id=user_id,
                session_id=session_id,
                status=HITLStatus.PENDING_APPROVAL,
                message="This action requires human approval.",
            )

            return HITLResponse(
                status=HITLStatus.PENDING_APPROVAL,
                request_id=pending["request_id"],
                message=pending["message"],
            )

        # 2. Ask for missing information before invoking agents.
        if needs_location_clarification(query, context):
            pending = await hitl.create_pending_request(
                query=query,
                user_id=user_id,
                session_id=session_id,
                status=HITLStatus.PENDING_CLARIFICATION,
                message="I need your location to answer accurately.",
                question="Which city should I use?",
            )

            return HITLResponse(
                status=HITLStatus.PENDING_CLARIFICATION,
                request_id=pending["request_id"],
                message=pending["message"],
                clarification_question=pending[
                    "clarification_question"
                ],
            )

        # 3. Normal weather request: no human approval needed.
        result = await service.process_weather_query_hitl(
            query,
            session_id=session_id,
            user_id=user_id,
        )

        return HITLResponse(
            status=HITLStatus.COMPLETED,
            message="Weather request completed.",
            result=str(result),
        )
    except HTTPException:
        raise
    except RuntimeError as exc:
        logger.error("HITL storage is unavailable: %s", str(exc))
        return generic_api_response(503, "fail", "HITL storage is unavailable.")
    except Exception:
        logger.exception("Error processing HITL request")
        return generic_api_response(500, "fail", "Internal server error.")

@router.post("/weather/agent/langgraph", summary="Weather Agent (POST)", description="Returns the current Weather & forecast of the API using a JSON body.", tags=["System"], response_model_exclude_none=True)
async def post_weather_forecast_route_langgraph(
    request: WeatherRequest,
    service: WeatherAgentInterface = Depends(get_weather_agent_service),
) -> AgentResponse:
    """Return the current weather & weather forecast for a city using a POST request."""
    query_val = request.query if request.query is not None else request.city
    
    try:
        query_val = validate_query(query_val)
    
        logger.info("Fetching current weather for city (POST): %s", query_val)
        return await service.process_weather_langgraph_query(query_val)

    except GuardrailViolation as exc:
        return generic_api_response(400, "fail", str(exc))
    except CityNotFoundError as exc:
        return generic_api_response(404, "fail", str(exc))
    except WeatherProviderError as exc:
        return generic_api_response(502, "fail", str(exc))
