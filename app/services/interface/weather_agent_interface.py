from abc import ABC, abstractmethod
from app.schema.weather import AgentResponse


class WeatherAgentInterface(ABC):

    @abstractmethod
    async def process_weather_query(self, query: str) -> AgentResponse:
        """
        Process a natural language weather query using an AI agent.
        
        Args:
            query (str): The user's natural language request.
            
        Returns:
            AgentResponse: The structured response from the agent.
        """
        pass