import os
import sys
from pydantic import BaseModel, Field
from typing import List

# Wir müssen sicherstellen, dass wir das Root-Verzeichnis finden
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from crewai import Agent, Task, Crew, Process
from langchain.tools import tool
from config.settings import settings
from src.rag_system.orchestration.factory import get_rag_pipeline
from src.llm_backend.manager import LLMManager
from crewai.tools import BaseTool
import json

# Initialisiere Pipelines
rag_pipeline = get_rag_pipeline()
os.environ["OPENAI_API_BASE"] = "http://localhost:11434/v1"
os.environ["OPENAI_API_KEY"] = "NA"
my_llm = f"openai/{settings.local_model}"

# =============================================================================
# 🛠️ TEIL 0: DATENMODELL (JSON STRUKTUR)
# =============================================================================

# Hier definieren wir, wie das JSON für das Frontend aussehen MUSS.
class FrontendResponse(BaseModel):
    title: str = Field(..., description="Eine kurze, prägnante Überschrift für die Antwort.")
    summary: str = Field(..., description="Eine Zusammenfassung der Antwort in 2-3 Sätzen.")
    key_facts: List[str] = Field(..., description="Eine Liste von 3-5 wichtigen Fakten (Bulletpoints).")
    confidence_score: int = Field(..., description="Eine Zahl von 0 bis 100, wie sicher sich der Agent ist.")

# =============================================================================
# 🛠️ TEIL 1: TOOLS
# =============================================================================

class RagSearchTool(BaseTool):
    name: str = "Frage das RAG System"
    description: str = "Benutze dieses Werkzeug, um Informationen zu suchen. Das Argument 'question' muss ein einfacher String mit der Suchfrage sein."

    def _run(self, question: str) -> str:
        docs = rag_pipeline.retrieve(question)
        context_str = "\n\n".join([f"Quelle: {doc.metadata.get('source', 'Unknown')}\nInhalt: {doc.content}" for doc in docs])
        return f"Hier sind relevante Informationen aus der Datenbank:\n\n{context_str}"

search_tool = RagSearchTool()

# =============================================================================
# � TEIL 2b: LOGGING (NEU!)
# =============================================================================

# Hier speichern wir ALLES, was passiert
execution_logs = []

def step_callback(step_output):
    """
    Diese Funktion wird NACH jedem Schritt eines Agenten aufgerufen.
    Wir speichern das Ergebnis in unserer Log-Liste.
    """
    # Wir untersuchen, was 'step_output' ist (meist ein Tuple oder Objekt)
    # CrewAI liefert hier oft rohe Infos. Wir formatieren es grob.
    execution_logs.append({
        "agent": "Unknown (Step Callback)", # In neueren CrewAI Versionen schwieriger direkt zuzuordnen
        "details": str(step_output)
    })

# =============================================================================
# �🤖 TEIL 2: AGENTEN
# =============================================================================

def create_agents():
    researcher = Agent(
        role='Senior Researcher',
        goal='Finde detaillierte Antworten',
        backstory="Du bist ein Experte für Recherche.",
        verbose=True,
        allow_delegation=False,
        tools=[search_tool],
        llm=my_llm,
        step_callback=step_callback # 👈 Hier hängen wir den Logger ein!
    )

    formatter = Agent(
        role='Data Formatter',
        goal='Formatiere Antworten in perfektes JSON',
        backstory="""
        Du bist ein API-Spezialist. Deine einzige Aufgabe ist es,
        unstrukturierte Texte in saubere JSON-Objekte zu verwandeln.
        Du hältst dich strikt an vorgegebene Schemas.
        """,
        verbose=True,
        allow_delegation=False,
        llm=my_llm,
        step_callback=step_callback # 👈 Hier auch!
    )
    
    return researcher, formatter

# =============================================================================
# 📋 TEIL 3: AUFGABEN (TASKS)
# =============================================================================

def create_tasks(challenge_input, agent_researcher, agent_formatter):
    # Aufgabe 1: Recherche
    task_research = Task(
        description=f"Recherchiere umfassend zu: '{challenge_input}'",
        expected_output="Ein detaillierter Textbericht.",
        agent=agent_researcher
    )

    # Aufgabe 2: Formatierung (JSON)
    task_format = Task(
        description="""
        Nimm den Bericht aus Task 1 und wandle ihn in das geforderte JSON-Format um.
        Achte darauf, dass alle Felder (title, summary, key_facts, confidence_score) gefüllt sind.
        """,
        expected_output="Ein valides JSON Objekt gemäß FrontendResponse Schema.",
        agent=agent_formatter,
        context=[task_research],
        output_pydantic=FrontendResponse # HIER PASSIERT DIE MAGIE! 🪄
    )
    
    return task_research, task_format

# =============================================================================
# 🚀 AUSFÜHRUNG
# =============================================================================

def run_challenge_json(challenge_input: str):
    researcher, formatter = create_agents()
    t_research, t_format = create_tasks(challenge_input, researcher, formatter)
    
    crew = Crew(
        agents=[researcher, formatter],
        tasks=[t_research, t_format],
        process=Process.sequential,
        verbose=True
    )

    print(f"\n🎬 STARTE JSON-CHALLENGE FÜR: '{challenge_input}'")
    result = crew.kickoff()
    
    # --- NEU: Zugriff auf die einzelnen Ergebnisse ---
    print("\n\n" + "="*50)
    print("📝 RAW OUTPUT: SENIOR RESEARCHER")
    print("-" * 50)
    print(t_research.output.raw_output)
    print("="*50)

    print("\n\n" + "="*50)
    print("🤖 RAW OUTPUT: DATA FORMATTER (JSON)")
    print("-" * 50)
    # Das ist das rohe Ergebnis des Formatters (der String, der das JSON enthält)
    print(t_format.output.raw_output)
    print("="*50)

    # --- NEU: Das vollständige Execution Log ---
    print("\n\n" + "="*50)
    print("📜 COMPLETE EXECUTION TRACE (ALL STEPS)")
    print("-" * 50)
    # Wir geben das Log als formatiertes JSON aus
    print(json.dumps(execution_logs, indent=2, default=str))
    print("="*50)

    return result.pydantic.model_dump_json(indent=2)

if __name__ == "__main__":
    challenge_input = "Was ist Retrieval Augmented Generation?"
    
    json_output = run_challenge_json(challenge_input)
    # Final output already printed above via task introspection

