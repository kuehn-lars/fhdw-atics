import os
import sys

# Wir müssen sicherstellen, dass wir das Root-Verzeichnis finden, um unsere eigenen Module zu importieren
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from crewai import Agent, Task, Crew, Process
from langchain.tools import tool
from config.settings import settings
from src.rag_system.orchestration.factory import get_rag_pipeline
from src.llm_backend.manager import LLMManager
from crewai.tools import BaseTool

# --- NEU: Native CrewAI Tools ---
from crewai_tools import ScrapeWebsiteTool, FileReadTool

# Initialisiere die Pipeline einmal global
rag_pipeline = get_rag_pipeline()

# Konfiguration für Ollama (Lokal)
os.environ["OPENAI_API_BASE"] = "http://localhost:11434/v1"
os.environ["OPENAI_API_KEY"] = "NA"
my_llm = f"openai/{settings.local_model}"

# =============================================================================
# 🛠️ TEIL 1: TOOLS (WERKZEUGE)
# =============================================================================

# 1. Unser bekanntes RAG Tool
class RagSearchTool(BaseTool):
    name: str = "Frage das RAG System"
    description: str = "Benutze dieses Werkzeug, um Informationen aus der lokalen Datenbank zu suchen. Das Argument 'question' muss ein einfacher String mit der Suchfrage sein."

    def _run(self, question: str) -> str:
        docs = rag_pipeline.retrieve(question)
        context_str = "\n\n".join([f"Quelle: {doc.metadata.get('source', 'Unknown')}\nInhalt: {doc.content}" for doc in docs])
        return f"Hier sind relevante Informationen aus der Datenbank:\n\n{context_str}"

rag_tool = RagSearchTool()

# 2. Native CrewAI Website Scraper (NEU!)
# Info: Dieses Tool kann den Text einer beliebigen URL auslesen.
scrape_tool = ScrapeWebsiteTool()

# 3. Native File Reader (NEU!)
# Info: Dieses Tool kann lokale Dateien lesen.
file_tool = FileReadTool()


# =============================================================================
# 🤖 TEIL 2: AGENTEN KONFIGURATION
# =============================================================================

def create_agents():
    # 1. Der Internet-Rechercheur (nutzt das Scrape Tool)
    web_researcher = Agent(
        role='Internet Researcher',
        goal='Finde aktuelle Informationen im Internet',
        backstory="""
        Du bist ein Experte für Online-Recherche. Du nutzt Webseiten, um Informationen zu finden,
        die vielleicht noch nicht in unserer lokalen Datenbank sind.
        """,
        verbose=True,
        allow_delegation=False,
        tools=[scrape_tool], # Hier nutzen wir das native Tool!
        llm=my_llm
    )
    
    # 2. Der Datenbank-Rechercheur (nutzt unser RAG Tool)
    db_researcher = Agent(
        role='Database Expert',
        goal='Finde gesichertes Wissen in der lokalen Datenbank',
        backstory="""
        Du vertraust nur den geprüften Dokumenten in unserer Datenbank. 
        Du prüfst, was wir intern zu einem Thema wissen.
        """,
        verbose=True,
        allow_delegation=False,
        tools=[rag_tool],
        llm=my_llm
    )

    # 3. Der Analyst (vergleicht beides)
    analyst = Agent(
        role='Information Analyst',
        goal='Vergleiche interne und externe Informationen',
        backstory="""
        Du analysierst die Ergebnisse der beiden Rechercheure. Deine Aufgabe ist es,
        Widersprüche zu finden und eine fundierte Antwort zu geben.
        """,
        verbose=True,
        allow_delegation=False,
        llm=my_llm
    )
    
    return web_researcher, db_researcher, analyst


# =============================================================================
# 📋 TEIL 3: AUFGABEN (TASKS)
# =============================================================================

def create_tasks(challenge_input, agent_web, agent_db, agent_analyst):
    # Aufgabe 1: Web Suche (Beispiel URL wird im Input erwartet oder wir geben sie vor)
    task_web = Task(
        description=f"""
        Gehe auf die Webseite 'https://en.wikipedia.org/wiki/Retrieval-augmented_generation' (oder eine ähnliche Quelle)
        und suche nach einer Definition für: '{challenge_input}'.
        Fasse die wichtigsten Punkte zusammen.
        """,
        expected_output="Eine Zusammenfassung der Online-Informationen.",
        agent=agent_web
    )

    # Aufgabe 2: Datenbank Suche
    task_db = Task(
        description=f"""
        Suche in unserer lokalen Datenbank nach Informationen zu: '{challenge_input}'.
        Nutze dafür das RAG System.
        """,
        expected_output="Eine Zusammenfassung der internen Datenbank-Informationen.",
        agent=agent_db
    )
    
    # Aufgabe 3: Vergleich
    task_compare = Task(
        description="""
        Vergleiche die Informationen aus dem Internet (Task 1) mit denen aus der Datenbank (Task 2).
        Gibt es Unterschiede? Ergänzen sie sich?
        Erstelle eine finale Antwort auf die ursprüngliche Frage.
        """,
        expected_output="Ein Vergleichsbericht und eine finale Antwort.",
        agent=agent_analyst,
        context=[task_web, task_db]
    )
    
    return task_web, task_db, task_compare


# =============================================================================
# 🚀 TEIL 4: FLOW CONTROL & AUSFÜHRUNG
# =============================================================================

def run_challenge(challenge_input: str):
    web, db, analyst = create_agents()
    t_web, t_db, t_compare = create_tasks(challenge_input, web, db, analyst)
    
    crew = Crew(
        agents=[web, db, analyst],
        tasks=[t_web, t_db, t_compare],
        process=Process.sequential,
        verbose=True
    )

    print(f"\n🎬 STARTE CREW MIT NATIVEN TOOLS FÜR: '{challenge_input}'")
    result = crew.kickoff()
    return result


if __name__ == "__main__":
    # --- CHALLENGE 4: TOOLS DEMO ---
    challenge_input = "Retrieval Augmented Generation"
    
    print(f"\n📋 CHALLENGE 4: {challenge_input}\n")
    final_answer = run_challenge(challenge_input)
    
    print("\n" + "="*50)
    print(f"✅ FINAL ANSWER:")
    print("-" * 50)
    print(final_answer)
    print("="*50 + "\n\n")
