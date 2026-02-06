import os
import sys

# Wir müssen sicherstellen, dass wir das Root-Verzeichnis finden, um unsere eigenen Module zu importieren
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from crewai import Agent, Task, Crew, Process
from langchain.tools import tool
from config.settings import settings
from src.rag_system.orchestration.factory import get_rag_pipeline
from crewai.tools import BaseTool

# Initialisiere die Pipeline einmal global
rag_pipeline = get_rag_pipeline()

# Konfiguration für Ollama (Lokal)
os.environ["OPENAI_API_BASE"] = "http://localhost:11434/v1"
os.environ["OPENAI_API_KEY"] = "NA"
my_llm = f"openai/{settings.local_model}"

# =============================================================================
# 🛠️ TEIL 1: TOOLS (WERKZEUGE)
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
# 🤖 TEIL 2: AGENTEN KONFIGURATION
# =============================================================================

def create_agents():
    # 1. Der Forscher
    researcher = Agent(
        role='Senior Researcher',
        goal='Finde detaillierte Antworten auf komplexe Fragen',
        backstory="""
        Du bist ein erfahrener Forscher, der es liebt, tief in Themen einzutauchen.
        Du gibst dich nicht mit oberflächlichen Antworten zufrieden. Dein Ziel ist es,
        Fakten zu sammeln und Zusammenhänge zu verstehen.
        """,
        verbose=True,
        allow_delegation=False,
        tools=[search_tool],
        llm=my_llm
    )

    # 2. Der Schreiber
    writer = Agent(
        role='Tech Writer',
        goal='Verfasse verständliche und prägnante Zusammenfassungen',
        backstory="""
        Du bist ein technischer Redakteur. Deine Stärke liegt darin, komplexe
        Informationen so aufzubereiten, dass sie jeder versteht. Du liebst klare
        Sätze und logische Strukturen.
        """,
        verbose=True,
        allow_delegation=False,
        llm=my_llm
    )
    
    return researcher, writer


# =============================================================================
# 📋 TEIL 3: AUFGABEN (TASKS)
# =============================================================================

def create_tasks(challenge_input, agent_researcher, agent_writer):
    # Aufgabe 1: Recherchieren
    task_research = Task(
        description=f"""
        Nutze das RAG System, um die folgende Frage umfassend zu beantworten: 
        '{challenge_input}'.
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
# 🚀 TEIL 4: FLOW CONTROL & AUSFÜHRUNG
# =============================================================================

def run_challenge(challenge_input: str):
    researcher, writer = create_agents()
    t_research, t_write = create_tasks(challenge_input, researcher, writer)
    
    crew = Crew(
        agents=[researcher, writer],
        tasks=[t_research, t_write],
        process=Process.sequential,
        verbose=True
    )

    print(f"\n🎬 STARTE CREW FÜR FRAGE: '{challenge_input}'")
    result = crew.kickoff()
    return result


if __name__ == "__main__":
    # --- CHALLENGE 2: RAG EXPLAINED ---
    challenge_input = "Erkläre Retrieval Augmented Generation (RAG)."
    expected_points = ["Kombination von Retrieval und Generierung", "Faktenwissen aus externer Quelle", "Reduziert Halluzinationen"]

    print(f"\n📋 CHALLENGE 2: {challenge_input}\n")

    final_answer = run_challenge(challenge_input)
    
    print("\n" + "="*50)
    print(f"✅ FINAL ANSWER:")
    print("-" * 50)
    print(final_answer)
    print("-" * 50)
    print(f"👀 WATCH OUT FOR: {expected_points}")
    print("="*50 + "\n\n")