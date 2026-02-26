import os
import sys

# Wir müssen sicherstellen, dass wir das Root-Verzeichnis finden, um unsere eigenen Module zu importieren
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from crewai import Agent, Task, Crew, Process
from langchain.tools import tool
from config.settings import settings
from src.rag_system.orchestration.factory import get_rag_pipeline
from src.llm_backend.manager import LLMManager

# CrewAI Native Tools importieren
from crewai_tools import ScrapeWebsiteTool, FileReadTool, WebsiteSearchTool

# Initialisiere die Pipeline einmal global
rag_pipeline = get_rag_pipeline()

# Initialisiere das LLM für die Agenten
os.environ["OPENAI_API_BASE"] = "http://localhost:11434/v1"
os.environ["OPENAI_API_KEY"] = "NA"
my_llm = f"openai/{settings.local_model}"


# =============================================================================
# 🛠️ TEIL 1: TOOLS (WERKZEUGE)
# =============================================================================

from crewai.tools import BaseTool

class RagSearchTool(BaseTool):
    name: str = "Frage das RAG System"
    description: str = "Nutzt das lokale RAG System, um nach Informationen zu suchen."

    def _run(self, query: str) -> str:
        return rag_pipeline.query(query, use_rag=True)

# Instanzen der Tools
rag_tool = RagSearchTool()
scrape_tool = ScrapeWebsiteTool()
web_search_tool = WebsiteSearchTool()
file_tool = FileReadTool()


# =============================================================================
# 🤖 TEIL 2: AGENTEN (DIE EXPERTEN)
# =============================================================================

def create_agents():
    # Agent 1: Der Researcher
    agent_researcher = Agent(
        role='Senior Researcher',
        goal='Finde präzise Informationen mit allen verfügbaren Tools.',
        backstory="""
        Du bist ein Experte in der Informationsbeschaffung. Du nutzt nicht nur das 
        RAG System, sondern kannst auch Webseiten scrapen oder Dateien lesen, 
        wenn es nötig ist.
        """,
        tools=[rag_tool, scrape_tool, web_search_tool, file_tool],
        llm=my_llm,
        verbose=True,
        allow_delegation=False
    )

    # Agent 2: Der Schreiber
    agent_writer = Agent(
        role='Tech Writer',
        goal='Erstelle verständliche und lehrreiche Zusammenfassungen.',
        backstory="""
        Du kannst komplexe technische Sachverhalte so erklären, dass sie auch 
        ein Schüler versteht.
        """,
        llm=my_llm,
        verbose=True,
        allow_delegation=False
    )
    
    return agent_researcher, agent_writer


# =============================================================================
# 📋 TEIL 3: AUFGABEN (DIE MISSION)
# =============================================================================

def create_tasks(question, agent_researcher, agent_writer):
    # Aufgabe 1: Recherche mit Tools
    task_research = Task(
        description=f"""
        Beantworte die folgende Frage: '{question}'.
        Nutze das RAG System zuerst. Wenn du dort nichts findest, versuche 
        relevante Informationen im Web zu finden oder in lokalen Dateien nachzusehen.
        """,
        expected_output="Umfassende Faktenliste aus verschiedenen Quellen.",
        agent=agent_researcher
    )

    # Aufgabe 2: Zusammenfassung
    task_write = Task(
        description="""
        Erstelle eine perfekte Antwort für einen Schüler basierend auf der Recherche.
        """,
        expected_output="Ein kurzer, verständlicher Erklärtext.",
        agent=agent_writer,
        context=[task_research]
    )
    
    return task_research, task_write


# =============================================================================
# ⚙️  CHALLENGE KONFIGURATION
# =============================================================================
challenges = [
    {
        "id": 4,
        "input": "Retrieval Augmented Generation",
        "expected_key_points": ["RAG", "LLM", "Vektoren", "Recherche"]
    }
]

# CHALLENGE_INPUT wird vom API-Router genutzt
CHALLENGE_INPUT = challenges[0]["input"]


# =============================================================================
# 🚀 TEIL 4: FLOW CONTROL & AUSFÜHRUNG
# =============================================================================

def run_challenge(challenge_input: str):
    """
    Baut die Crew und führt sie aus.
    """
    researcher, writer = create_agents()
    t_research, t_write = create_tasks(challenge_input, researcher, writer)
    
    crew = Crew(
        agents=[researcher, writer],
        tasks=[t_research, t_write],
        process=Process.sequential,
        verbose=True
    )

    result = crew.kickoff()
    return result


if __name__ == "__main__":
    c_input = CHALLENGE_INPUT
    run_challenge(c_input)
