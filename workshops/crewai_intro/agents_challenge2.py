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
# Wir nutzen den OpenAI-Compatible Endpoint von Ollama via CrewAI LiteLLM Integration
os.environ["OPENAI_API_BASE"] = "http://localhost:11434/v1"
os.environ["OPENAI_API_KEY"] = "NA"
my_llm = f"openai/{settings.local_model}"

# =============================================================================
# ⚙️  KONFIGURATION – Das hier im Skript anpassen!
# =============================================================================
CHALLENGE_INPUT = "Erkläre Retrieval Augmented Generation (RAG)."

# =============================================================================
# 🛠️ TEIL 1: TOOLS (WERKZEUGE)
# =============================================================================
# Hier definieren wir die Fähigkeiten, die unsere Agenten nutzen können.

from crewai.tools import BaseTool

class RagSearchTool(BaseTool):
    name: str = "Frage das RAG System"
    description: str = "Benutze dieses Werkzeug, um Informationen zu suchen. Das Argument 'question' muss ein einfacher String mit der Suchfrage sein."

    def _run(self, question: str) -> str:
        # Wir rufen hier nur die relevanten Dokumente ab
        docs = rag_pipeline.retrieve(question)
        
        # Wir formatieren die Dokumente zu einem String für den Agenten
        context_str = "\n\n".join([f"Quelle: {doc.metadata.get('source', 'Unknown')}\nInhalt: {doc.content}" for doc in docs])
        
        return f"Hier sind relevante Informationen aus der Datenbank:\n\n{context_str}"

# Instanz des Tools erstellen
search_tool = RagSearchTool()

# 💡 HIER KÖNNT IHR WEITERE TOOLS DEFINIEREN
# zum Beispiel: Wikipedia-Suche, Taschenrechner, etc.


# =============================================================================
# 🤖 TEIL 2: AGENTEN KONFIGURATION
# =============================================================================

"""
INFO: MÖGLICHE PARAMETER FÜR AGENTEN
-------------------------------------
Agent(
    role="...",             # (Pflicht) Die Job-Bezeichnung (z.B. "Researcher").
    goal="...",             # (Pflicht) Was soll der Agent erreichen?
    backstory="...",        # (Pflicht) Charakter, Hintergrund & Motivation.
    tools=[...],            # Liste der Werkzeuge (z.B. [RagTools.ask_rag]).
    verbose=True,           # Wenn True, gibt der Agent viele Infos in der Konsole aus.
    allow_delegation=False, # Wenn True, kann der Agent Aufgaben an andere delegieren.
    memory=True,            # Wenn True, erinnert sich der Agent an vorherige Schritte.
    max_iter=15,            # Maximale Anzahl an Schritten, bevor er abbricht.
    llm=...,                # (Optional) Ein spezifisches LLM für diesen Agenten überschreiben.
    function_calling_llm=.. # (Optional) Spezielles LLM nur für Tool-Calls.
)
"""

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
        allow_delegation=False, # Er macht seine Arbeit selbst
        tools=[search_tool], # Er darf das RAG System benutzen
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

"""
INFO: MÖGLICHE PARAMETER FÜR TASKS
-----------------------------------
Task(
    description="...",      # (Pflicht) Genaue Beschreibung, was zu tun ist.
    expected_output="...",  # (Pflicht) Wie soll das Ergebnis aussehen? (Liste, Text, JSON...)
    agent=...,              # (Pflicht) Welcher Agent ist verantwortlich?
    tools=[...],            # (Optional) Spezifische Tools nur für diese Aufgabe.
    context=[...],          # (Optional) Liste von anderen Tasks, deren Output hier wichtig ist.
    output_file="out.txt",  # (Optional) Speichert das Ergebnis in eine Datei.
    output_json=...,        # (Optional) Pydantic Model für strukturierten JSON Output.
    output_pydantic=...,    # (Optional) Pydantic Model für stark typisierten Output.
    callback=...,           # (Optional) Eine Funktion, die nach Abschluss aufgerufen wird.
    human_input=False       # (Optional) Wenn True, fragt der Agent den Menschen um Rat.
)
"""

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
        context=[task_research] # Wir geben explizit an, dass dieser Task vom Ergebnis des Researchtasks abhängt
    )
    
    return task_research, task_write


# =============================================================================
# 🚀 TEIL 4: FLOW CONTROL & AUSFÜHRUNG
# =============================================================================

def run_challenge(challenge_input: str):
    """
    Baut die Crew und führt sie aus.
    """
    
    # 1. Agenten erstellen
    researcher, writer = create_agents()
    
    # 2. Aufgaben erstellen
    t_research, t_write = create_tasks(challenge_input, researcher, writer)
    
    # 3. Crew zusammenstellen
    """
    INFO: CREW PARAMETER
    --------------------
    process=Process.sequential  -> Aufgaben der Reihe nach (Standard).
    process=Process.hierarchical-> Ein 'Manager' Agent (autom.) verteilt Aufgaben.
    """
    crew = Crew(
        agents=[researcher, writer],
        tasks=[t_research, t_write],
        process=Process.sequential,
        verbose=True
    )

    # 4. Starten
    result = crew.kickoff()
    return result


if __name__ == "__main__":
    # --- DUMMY INPUT / OUTPUT DATEN FÜR CHALLENGE 1 ---
    # Hier definieren wir Testfälle, um zu prüfen, ob die Agenten gute Arbeit leisten.
    
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

    c_input = challenges[1]["input"]
    c_expected = challenges[1]["expected_key_points"]
        
    run_challenge(c_input)