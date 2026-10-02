from crewai import Agent, Crew, Process, Task
from app.tools.crewai.faq import search_faq

def build_faq_crew(question: str) -> Crew:
    faq_agent = Agent(
        role="FAQ Assistant",
        goal="Provide accurate answers to questions based on the FAQ data",
        backstory="""
        You are an expert FAQ assistant.
        You retrieve information from the FAQ document
        and explain it clearly to users.
        """,
        tools=[search_faq],
        verbose=True,
    )
    faq_task = Task(
        description=f"""
        Answer the following question using the FAQ information: {question}.

        Use the search_faq tool to retrieve the relevant information from the FAQ data.
        """,
        expected_output="""
        A clear and accurate answer based on the FAQ data.
        """,
        agent=faq_agent,
    )
    return Crew(
        agents=[faq_agent],
        tasks=[faq_task],
        process=Process.sequential,
        verbose=True,
    )
