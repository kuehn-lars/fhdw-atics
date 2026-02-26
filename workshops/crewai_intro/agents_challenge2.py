import os
import sys

# Wir müssen sicherstellen, dass wir das Root-Verzeichnis finden, um unsere eigenen Module zu importieren
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from crewai import Agent, Task, Crew, Process
from langchain.tools import tool
from config.settings import settings
from src.rag_system.orchestration.factory import get_rag_pipeline
from src.llm_backend.manager import LLMManager

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
        # Hier rufen wir unsere existierende RAG Pipeline auf
        return rag_pipeline.query(query, use_rag=True)

# Erstelle eine Instanz des Tools
rag_tool = RagSearchTool()


# =============================================================================
# 🤖 TEIL 2: AGENTEN (DIE EXPERTEN)
# =============================================================================

def create_agents():
    # Agent 1: Der Researcher
    agent_researcher = Agent(
        role='Senior Researcher',
        goal='Finde präzise Informationen zu komplexen Themen im RAG System.',
        backstory="""
        Du bist ein Experte in der Informationsbeschaffung. Deine Stärke ist es, 
        gezielte Fragen an das RAG System zu stellen und die wichtigsten Fakten 
        herauszufiltern. Du bist sehr gründlich und gibst dich nicht mit 
        oberflächlichen Antworten zufrieden.
        """,
        tools=[rag_tool],
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
        ein Schüler versteht. Du nimmst die Fakten vom Researcher und bringst 
        sie in eine klare, strukturierte Form. Dein Schreibstil ist motivierend 
        und präzise.
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
    # Aufgabe 1: Recherche
    task_research = Task(
        description=f"""
        Nutze das RAG System, um die folgende Frage umfassend zu beantworten: 
        '{question}'.
        Sammle alle wichtigen Fakten, Definitionen und Hintergründe.
        """,
        expected_output="Eine detaillierte Liste von Fakten und Informationen zur Frage.",
        agent=agent_researcher
    )

    # Aufgabe 2: Schreiben
    task_write = Task(
        description="""
        Nimm die Informationen aus der Recherche (Task 1) und schreibe eine 
        perfekte Antwort für einen Schüler. Die Antwort soll präzise, lehrreich
        und gut lesbar sein.
        """,
        expected_output="Ein kurzer, verständlicher Erklärtext (ca. 3-5 Sätze).",
        agent=agent_writer,
        context=[task_research]
    )
    
    return task_research, task_write


# =============================================================================
# ⚙️  CHALLENGE KONFIGURATION
# =============================================================================
challenges = [
    {
        "id": 1,
        "input": "Was ist ein Vector Store?",
        "expected_key_points": ["Datenbank für Vektoren/Embeddings", "Ermöglicht Ähnlichkeitssuche", "Wichtig für RAG"]
    },
    {
        "id": 2,
        "input": "Erkläre Retrieval Augmented Generation (RAG).",
        "expected_key_points": ["Kombination von Retrieval und Generierung", "Faktenwissen aus externer Quelle", "Reduziert Halluzinationen"]
    },
    {
        "id": 3,
        "input": "Welche Häuser gibt es in Hogwarts und wofür stehen sie?",
        "expected_key_points": ["Gryffindor (Mut)", "Hufflepuff (Treue)", "Ravenclaw (Weisheit)", "Slytherin (List)"]
    }
]

# CHALLENGE_INPUT wird vom API-Router genutzt
CHALLENGE_INPUT = challenges[1]["input"]


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