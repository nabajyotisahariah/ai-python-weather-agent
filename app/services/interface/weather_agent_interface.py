from abc import ABC, abstractmethod
from app.schema.weather import AgentResponse


class WeatherAgentInterface(ABC):

    @abstractmethod
    async def process_weather_query(self, query: str, session_id: str, user_id: str) -> AgentResponse:
        """
        Process a natural language weather query using an AI agent.
        
        Args:
            query (str): The user's natural language request.
            session_id (str): The user's session ID.
            user_id (str): The user's ID.
            
        Returns:
            AgentResponse: The structured response from the agent.
        """
        pass


    @abstractmethod
    async def process_weather_langgraph_query(self, query: str) -> AgentResponse:
        """
        Process a natural language weather query using an AI agent.
        
        Args:
            query (str): The user's natural language request.
            
        Returns:
            AgentResponse: The structured response from the agent.
        """
        pass

    @abstractmethod
    async def process_weather_hitl(
        self,
        query: str,
        session_id: str,
        user_id: str,
        clarification_id: str | None = None,
    ) -> AgentResponse:
        """
        Process a natural language weather query using an AI agent.
        
        Args:
            query (str): The user's natural language request.
            session_id (str): The user's session ID.
            user_id (str): The user's ID.
            
        Returns:
            AgentResponse: The structured response from the agent.
        """
        pass