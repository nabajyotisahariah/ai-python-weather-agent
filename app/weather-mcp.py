from mcp.server.fastmcp import FastMCP
import logging
from app.utils.logger import setup_logging
from app.config import settings

from app.tools.mcp.weather_tools import (
    get_weather,
    get_weather_forecast,
)


setup_logging()
logging.info(f"Starting Weather Assistant API {settings.environment}")

mcp = FastMCP(
    "AI Weather MCP Server",
    stateless_http=True,
    instructions="""
    Weather MCP server for retrieving current weather and forecast information.

    Use get_weather for current weather conditions.
    Use get_weather_forecast for forecast information.
    """,
)

logging.info("MCP Tools initialize")
mcp.tool()(get_weather)
mcp.tool()(get_weather_forecast)

logging.info("MCP listening")
app = mcp.streamable_http_app()