from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

import logging

from app.utils.logger import setup_logging
from app.config import settings
from app.tools.mcp.weather_tools import (
    get_weather,
    get_weather_forecast,
)

setup_logging()

logging.info(
    f"Starting Weather Assistant API {settings.environment}"
)

# ---------------------------------------------------------
# MCP Server
# ---------------------------------------------------------

mcp = FastMCP(
    "AI Weather MCP Server",
    stateless_http=True,
    instructions="""
    Weather MCP server for retrieving current weather and forecast information.

    Use get_weather for current weather conditions.
    Use get_weather_forecast for forecast information.
    """,
)

# ---------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------

logging.info("MCP Tools initialize")

mcp.tool()(get_weather)
mcp.tool()(get_weather_forecast)

# ---------------------------------------------------------
# Transport Security
# ---------------------------------------------------------

transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[
        "34.131.252.169",
        "34.131.252.169:*",
        "localhost",
        "localhost:*",
        "127.0.0.1",
        "127.0.0.1:*",
    ],
    allowed_origins=[
        "http://34.131.252.169",
        "http://localhost",
        "http://localhost:*",
        "http://127.0.0.1",
        "http://127.0.0.1:*",
    ],
)

# ---------------------------------------------------------
# MCP HTTP Application
# ---------------------------------------------------------

logging.info("MCP listening")

# app = mcp.streamable_http_app(
#     transport_security=transport_security
# )
app = mcp.streamable_http_app()