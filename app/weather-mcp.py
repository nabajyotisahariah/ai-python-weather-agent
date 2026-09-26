from mcp.server.fastmcp import FastMCP

from app.tools.mcp.weather_tools import (
    get_weather,
    get_weather_forecast,
)


mcp = FastMCP(
    "AI Weather MCP Server",
    instructions="""
    Weather MCP server for retrieving current weather and forecast information.

    Use get_weather for current weather conditions.
    Use get_weather_forecast for weather forecast information.
    """,
    stateless_http=True,
)


# Register MCP tools
mcp.tool()(get_weather)
mcp.tool()(get_weather_forecast)


# Streamable HTTP ASGI application
app = mcp.streamable_http_app()