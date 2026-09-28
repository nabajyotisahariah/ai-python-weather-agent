# AI Weather Agent - MCP (Model Context Protocol) Integration

*Please refer to the main [README.md](README.md) file before exploring this document.*

---

## 🚀 Project Journey So Far

Before diving into the Model Context Protocol (MCP) integration, here is a quick summary of the capabilities covered in previous phases:

### Phase 1: Agent Framework Orchestration
Our weather capability can be orchestrated using multiple advanced agent frameworks:
* 🤖 **CrewAI:** `http://localhost:8000/api/v1/weather/crewai?city=What is the temp in Delhi`
* 🦜 **LangGraph:** `http://localhost:8000/api/v1/weather/langgraph?city=What is the temp in Delhi`
* ⚙️ **AutoGen:** `http://localhost:8000/api/v1/weather/autogen?city=What is the temp in Delhi`
* ☁️ **Google ADK:** `http://localhost:8000/api/v1/weather/google-adk?city=What is the temp in Delhi`

### Phase 2: Cloud Deployment
The application has been successfully deployed on **GCP Kubernetes**. The architecture is designed for portability, allowing easy deployment across other environments such as Azure, AWS (ECS), or GCP EC2.

### Phase 3: Monitoring & Observability
We integrated **Langfuse** as our primary tool for monitoring and observability, ensuring deep insights into agent operations. **LangSmith** is also supported as an alternative backend.

---

## 🔌 Phase 4: Exploring MCP in the Weather Application

In this phase, we explore the **Model Context Protocol (MCP)** implementation within our weather application. MCP standardizes how AI models interact with tools and data sources.

Below are examples of how to interact with our local MCP server using `curl`. In upcoming iterations, we will connect these MCP endpoints using **n8n** by deploying them on GCP Kubernetes.

### 1. Start the Development Server

Begin by launching the MCP server from the project root directory:

```powershell
uvicorn app.weather-mcp:app --host 0.0.0.0 --port 8100 --reload
```

### 2. Initialize the MCP Server

First, establish a connection to the MCP server. This step negotiates the protocol version and retrieves the server's capabilities.

**Request:**
```bash
curl -i http://localhost:8100/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "MCP-Protocol-Version: 2025-06-18" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-06-18",
      "capabilities": {},
      "clientInfo": {
        "name": "curl-client",
        "version": "1.0"
      }
    }
  }'
```

**Response:**
```http
HTTP/1.1 200 OK
Date: Mon, 28 Sep 2026 03:20:09 GMT
Server: uvicorn
Cache-Control: no-cache, no-transform
Connection: keep-alive
Content-Type: text/event-stream
X-Accel-Buffering: no
Transfer-Encoding: chunked

event: message
data: {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-06-18","capabilities":{"experimental":{},"prompts":{"listChanged":false},"resources":{"subscribe":false,"listChanged":false},"tools":{"listChanged":false}},"serverInfo":{"name":"AI Weather MCP Server","version":"1.28.1"},"instructions":"\n    Weather MCP server for retrieving current weather and forecast information.\n\n    Use get_weather for current weather conditions.\n    Use get_weather_forecast for weather forecast information.\n    "}}
```

### 3. List Available Tools

Once initialized, you can query the server for a list of available tools. *(Note: Depending on your setup, you may need to pass an `Mcp-Session-Id` header returned from initialization).*

**Request:**
```bash
curl -i http://localhost:8100/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "MCP-Protocol-Version: 2025-06-18" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }'
```

**Response:**
```http
HTTP/1.1 200 OK
Date: Mon, 28 Sep 2026 03:22:04 GMT
Server: uvicorn
Cache-Control: no-cache, no-transform
Connection: keep-alive
Content-Type: text/event-stream
X-Accel-Buffering: no
Transfer-Encoding: chunked

event: message
data: {"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"get_weather","description":"\n    Get current weather information for a city.\n\n    Args:\n        city: City name such as London, Delhi, New York or Tokyo.\n\n    Returns:\n        Current weather information.\n    ","inputSchema":{"properties":{"city":{"title":"City","type":"string"}},"required":["city"],"title":"get_weatherArguments","type":"object"},"outputSchema":{"additionalProperties":true,"title":"get_weatherDictOutput","type":"object"}},{"name":"get_weather_forecast","description":"\n    Get weather forecast for a city.\n\n    Args:\n        city: City name such as London, Delhi, New York or Tokyo.\n        days: Number of forecast days, from 1 to 7.\n\n    Returns:\n        Weather forecast information.\n    ","inputSchema":{"properties":{"city":{"title":"City","type":"string"},"days":{"default":3,"title":"Days","type":"integer"}},"required":["city"],"title":"get_weather_forecastArguments","type":"object"},"outputSchema":{"properties":{"result":{"items":{"additionalProperties":true,"type":"object"},"title":"Result","type":"array"}},"required":["result"],"title":"get_weather_forecastOutput","type":"object"}}]}}
```

### 4. Call a Tool

Finally, execute a specific tool on the MCP server. In this example, we call the `get_weather` tool for the city of Delhi.

**Request:**
```bash
curl -i http://localhost:8100/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "MCP-Protocol-Version: 2025-06-18" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "get_weather",
      "arguments": {
        "city": "Delhi"
      }
    }
  }'
```

**Response:**
```http
HTTP/1.1 200 OK
Date: Mon, 28 Sep 2026 03:23:11 GMT
Server: uvicorn
Cache-Control: no-cache, no-transform
Connection: keep-alive
Content-Type: text/event-stream
X-Accel-Buffering: no
Transfer-Encoding: chunked

event: message
data: {"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text","text":"{\n  \"city\": \"Delhi\",\n  \"weather\": {\n    \"city\": \"Delhi\",\n    \"temperature\": \"24\",\n    \"feels_like\": \"26\",\n    \"humidity\": \"74\",\n    \"description\": \"Partly Cloudy \",\n    \"wind_speed\": \"7\"\n  }\n}"}],"structuredContent":{"city":"Delhi","weather":{"city":"Delhi","temperature":"24","feels_like":"26","humidity":"74","description":"Partly Cloudy ","wind_speed":"7"}},"isError":false}}
```
