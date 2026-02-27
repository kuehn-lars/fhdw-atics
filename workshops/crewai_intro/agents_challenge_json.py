"""
📚 CREWAI REFERENZ & DOKUMENTATION
===================================

⚠️  DIESE DATEI IST NICHT ZUM AUSFÜHREN GEDACHT!
    Sie dient als vollständige Referenz für alle CrewAI-Konzepte:

    1. Tools        – Alle verfügbaren Werkzeuge
    2. Agenten      – Konfiguration und Parameter
    3. Tasks        – Aufgaben und deren Optionen
    4. Crews        – Orchestrierung und Prozesse
    5. Output       – Pydantic-Modelle für strukturierte Ausgabe
    6. Callbacks    – Logging und Monitoring
    7. Tipps        – Best Practices und häufige Fehler

Autor: Workshop "Advanced Topics in CS"
"""

# =============================================================================
# 📦 IMPORTS (nur für Code-Completion und Referenz)
# =============================================================================

import os
import sys
import json
from typing import List, Optional
from pydantic import BaseModel, Field

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool

# Unsere eigene Tool-Bibliothek
from workshops.crewai_intro.tools import (
    # Einzelne Tools
    rag_search_tool,
    wikipedia_tool,
    web_scraper_tool,
    file_reader_tool,
    file_writer_tool,
    math_tool,
    datetime_tool,
    json_formatter_tool,
    text_summarizer_tool,
    directory_list_tool,
    python_repl_tool,
    # Gruppierte Tool-Sets
    ALL_TOOLS,
    RESEARCH_TOOLS,
    FILE_TOOLS,
    UTILITY_TOOLS,
    DEVELOPER_TOOLS,
)


# =============================================================================
# 🛠️  TEIL 1: TOOLS – ALLE VERFÜGBAREN WERKZEUGE
# =============================================================================
"""
ÜBERSICHT ALLER TOOLS
---------------------
Jedes Tool erbt von `crewai.tools.BaseTool` und kann einem Agenten zugewiesen
werden. Die Tools sind in `workshops/crewai_intro/tools.py` definiert.

┌────────────────────────┬─────────────────────┬────────────────────────────────────┐
│ Tool-Instanz           │ Variablenname       │ Was es tut                         │
├────────────────────────┼─────────────────────┼────────────────────────────────────┤
│ RagSearchTool          │ rag_search_tool     │ Sucht im lokalen Vector Store      │
│ WikipediaTool          │ wikipedia_tool      │ Sucht auf Wikipedia (deutsch)      │
│ WebScraperTool         │ web_scraper_tool    │ Liest Webseiten-Inhalte            │
│ FileReaderTool         │ file_reader_tool    │ Liest lokale Dateien               │
│ FileWriterTool         │ file_writer_tool    │ Schreibt in lokale Dateien         │
│ MathTool               │ math_tool           │ Berechnet math. Ausdrücke          │
│ DateTimeTool           │ datetime_tool       │ Gibt Datum/Uhrzeit zurück          │
│ JSONFormatterTool      │ json_formatter_tool │ Formatiert Text als JSON           │
│ TextSummarizerTool     │ text_summarizer_tool│ Kürzt Texte auf n Zeichen          │
│ DirectoryListTool      │ directory_list_tool │ Listet Dateien in Verzeichnissen   │
│ PythonREPLTool         │ python_repl_tool    │ Führt Python-Code aus (Sandbox)    │
└────────────────────────┴─────────────────────┴────────────────────────────────────┘

TOOL-SETS (Gruppierungen für verschiedene Anwendungsfälle):
    RESEARCH_TOOLS  = [rag_search_tool, wikipedia_tool, web_scraper_tool]
    FILE_TOOLS      = [file_reader_tool, file_writer_tool, directory_list_tool]
    UTILITY_TOOLS   = [math_tool, datetime_tool, json_formatter_tool, text_summarizer_tool]
    DEVELOPER_TOOLS = [python_repl_tool, file_reader_tool, file_writer_tool]
    ALL_TOOLS       = [alle 11 Tools]
"""


# ─── Eigenes Tool erstellen (Beispiel) ───────────────────────────────────────

class MeinEigenesTool(BaseTool):
    """
    So erstellt man ein eigenes Tool.
    
    PFLICHTFELDER:
        name: str           – Name des Tools (wird dem Agenten angezeigt)
        description: str    – Beschreibung (der Agent entscheidet basierend darauf, wann er es nutzt!)
    
    PFLICHTMETHODE:
        _run(self, input)   – Die eigentliche Logik
    """
    name: str = "Mein Tool"
    description: str = "Beschreibung, die dem Agenten erklärt, WANN und WIE er dieses Tool nutzen soll."
    
    def _run(self, eingabe: str) -> str:
        # Hier kommt die Logik hin
        return f"Ergebnis für: {eingabe}"


# =============================================================================
# 🤖 TEIL 2: AGENTEN – ALLE PARAMETER
# =============================================================================
"""
AGENT PARAMETER – VOLLSTÄNDIGE REFERENZ
----------------------------------------

agent = Agent(
    # ─── PFLICHTFELDER ──────────────────────────────────────────────
    role="...",                 # Die Rolle/Job-Bezeichnung des Agenten
    goal="...",                 # Was soll der Agent erreichen?
    backstory="...",            # Charakter, Hintergrund, Motivation
    
    # ─── TOOLS ──────────────────────────────────────────────────────
    tools=[...],               # Liste von BaseTool-Instanzen
                               # z.B. tools=[wikipedia_tool, math_tool]
                               # oder tools=RESEARCH_TOOLS
    
    # ─── LLM KONFIGURATION ─────────────────────────────────────────
    llm="openai/qwen2.5:3b",   # Das LLM für diesen Agenten
    function_calling_llm=...,  # (Optional) Separates LLM nur für Tool-Calls
    
    # ─── VERHALTEN ──────────────────────────────────────────────────
    verbose=True,              # Ausführliches Logging in der Konsole
    allow_delegation=False,    # Kann der Agent Aufgaben an andere delegieren?
    memory=True,               # Soll sich der Agent an frühere Schritte erinnern?
    max_iter=15,               # Max. Anzahl an Iterationen bevor Abbruch
    max_rpm=None,              # Rate Limiting (Requests per Minute)
    
    # ─── CALLBACKS ──────────────────────────────────────────────────
    step_callback=...,         # Funktion, die nach jedem Schritt aufgerufen wird
                               # z.B. step_callback=mein_logger
)
"""


# ─── Beispiel-Agenten für verschiedene Rollen ─────────────────────────────────

def beispiel_agenten(my_llm: str):
    """Zeigt verschiedene Agenten-Konfigurationen."""
    
    # Minimaler Agent (nur Pflichtfelder)
    minimal_agent = Agent(
        role="Assistent",
        goal="Beantworte einfache Fragen.",
        backstory="Du bist ein freundlicher Helfer.",
        llm=my_llm,
    )
    
    # Forscher mit Tools
    researcher = Agent(
        role="Senior Researcher",
        goal="Finde detaillierte, faktisch korrekte Antworten.",
        backstory="""
        Du bist ein erfahrener Forscher mit Zugang zu verschiedenen 
        Informationsquellen. Du gibst dich nicht mit oberflächlichen 
        Antworten zufrieden.
        """,
        tools=RESEARCH_TOOLS,  # RAG + Wikipedia + Web Scraper
        llm=my_llm,
        verbose=True,
        allow_delegation=False,
        memory=True,
    )
    
    # Entwickler mit System-Zugriff
    developer = Agent(
        role="Software Engineer",
        goal="Schreibe und teste Code.",
        backstory="Du bist ein erfahrener Entwickler.",
        tools=DEVELOPER_TOOLS,  # Shell + Python + File Read/Write
        llm=my_llm,
        verbose=True,
        max_iter=25,  # Mehr Iterationen für komplexe Aufgaben
    )
    
    # Mathematiker
    mathematician = Agent(
        role="Mathematiker",
        goal="Löse mathematische Probleme präzise.",
        backstory="Du bist ein Mathematik-Professor.",
        tools=[math_tool, python_repl_tool],
        llm=my_llm,
    )
    
    # Schreiber (ohne Tools, nur Text)
    writer = Agent(
        role="Tech Writer",
        goal="Verfasse verständliche Zusammenfassungen.",
        backstory="""
        Du bist ein technischer Redakteur. Komplexe Informationen 
        aufzubereiten ist deine Stärke.
        """,
        llm=my_llm,
        verbose=True,
        allow_delegation=False,
    )
    
    return minimal_agent, researcher, developer, mathematician, writer


# =============================================================================
# 📋 TEIL 3: TASKS – ALLE PARAMETER
# =============================================================================
"""
TASK PARAMETER – VOLLSTÄNDIGE REFERENZ
--------------------------------------

task = Task(
    # ─── PFLICHTFELDER ──────────────────────────────────────────────
    description="...",          # Genaue Beschreibung, was zu tun ist
    expected_output="...",      # Wie soll das Ergebnis aussehen?
    agent=...,                  # Welcher Agent ist verantwortlich?
    
    # ─── ABHÄNGIGKEITEN ─────────────────────────────────────────────
    context=[task1, task2],     # Liste anderer Tasks, deren Output hier einfließt
                                # → Der Agent erhält die Ergebnisse als Kontext
    
    # ─── TOOLS (Task-spezifisch) ────────────────────────────────────
    tools=[...],                # Zusätzliche Tools NUR für diese Aufgabe
    
    # ─── OUTPUT FORMATE ─────────────────────────────────────────────
    output_file="result.txt",   # Speichert das Ergebnis in eine Datei
    output_json=MyModel,        # Pydantic Model → Agent gibt JSON zurück
    output_pydantic=MyModel,    # Pydantic Model → Ergebnis als Python-Objekt
    
    # ─── INTERAKTION ────────────────────────────────────────────────
    human_input=False,          # Wenn True, fragt der Agent den Benutzer
    
    # ─── CALLBACKS ──────────────────────────────────────────────────
    callback=...,               # Funktion, die nach Abschluss aufgerufen wird
)
"""


# ─── Pydantic-Modelle für strukturierten Output ──────────────────────────────

class FrontendResponse(BaseModel):
    """Beispiel: Strukturierter Output für ein Frontend."""
    title: str = Field(..., description="Kurze Überschrift")
    summary: str = Field(..., description="Zusammenfassung in 2-3 Sätzen")
    key_facts: List[str] = Field(..., description="3-5 wichtige Fakten als Liste")
    confidence_score: int = Field(..., description="Sicherheit 0-100")


class CodeReview(BaseModel):
    """Beispiel: Code-Review als strukturierter Output."""
    file_name: str = Field(..., description="Name der geprüften Datei")
    issues: List[str] = Field(default_factory=list, description="Gefundene Probleme")
    suggestions: List[str] = Field(default_factory=list, description="Verbesserungsvorschläge")
    quality_score: int = Field(..., description="Codequalität 0-100")
    approved: bool = Field(..., description="Kann der Code so deployed werden?")


class ResearchReport(BaseModel):
    """Beispiel: Forschungsbericht als strukturierter Output."""
    topic: str = Field(..., description="Das untersuchte Thema")
    findings: List[str] = Field(..., description="Kernerkenntnisse")
    sources: List[str] = Field(default_factory=list, description="Verwendete Quellen")
    conclusion: str = Field(..., description="Fazit")
    further_research: Optional[List[str]] = Field(None, description="Offene Fragen")


# ─── Beispiel-Tasks ──────────────────────────────────────────────────────────

def beispiel_tasks(researcher, writer, question: str):
    """Zeigt verschiedene Task-Konfigurationen."""
    
    # Einfacher Task
    task_simple = Task(
        description=f"Beantworte diese Frage: '{question}'",
        expected_output="Eine klare Antwort in 2-3 Sätzen.",
        agent=researcher,
    )
    
    # Task mit Kontext-Abhängigkeit
    task_with_context = Task(
        description="Fasse die Recherche zusammen.",
        expected_output="Ein verständlicher Erklärtext.",
        agent=writer,
        context=[task_simple],  # ← Bekommt das Ergebnis von task_simple
    )
    
    # Task mit JSON-Output (Pydantic)
    task_json = Task(
        description=f"Recherchiere zu '{question}' und formatiere als JSON.",
        expected_output="Ein valides JSON gemäß FrontendResponse.",
        agent=researcher,
        output_pydantic=FrontendResponse,  # ← Erzwingt Pydantic-Format
    )
    
    # Task mit Datei-Output
    task_file = Task(
        description="Schreibe einen ausführlichen Bericht.",
        expected_output="Ein mehrseitiger Bericht.",
        agent=writer,
        context=[task_simple],
        output_file="output/bericht.txt",  # ← Ergebnis wird gespeichert
    )
    
    return task_simple, task_with_context, task_json, task_file


# =============================================================================
# 🚀 TEIL 4: CREW – ORCHESTRIERUNG
# =============================================================================
"""
CREW PARAMETER – VOLLSTÄNDIGE REFERENZ
--------------------------------------

crew = Crew(
    # ─── PFLICHTFELDER ──────────────────────────────────────────────
    agents=[agent1, agent2],    # Liste der Agenten
    tasks=[task1, task2],       # Liste der Aufgaben (Reihenfolge wichtig!)
    
    # ─── PROZESSTYP ─────────────────────────────────────────────────
    process=Process.sequential,     # Aufgaben der Reihe nach
    # process=Process.hierarchical, # Ein Manager verteilt Aufgaben
    
    # ─── OPTIONEN ───────────────────────────────────────────────────
    verbose=True,               # Ausführliches Logging
    memory=False,               # Gemeinsamer Speicher für alle Agenten
    planning=False,             # Automatische Planungsphase vor Ausführung
    
    # ─── HIERARCHICAL MODE ──────────────────────────────────────────
    manager_llm=...,            # LLM für den Manager (nur bei hierarchical)
    manager_agent=...,          # Eigener Manager-Agent (statt auto-generiert)
)


PROCESS-TYPEN ERKLÄRT
---------------------

1. Process.sequential (Standard)
   → Task 1 → Task 2 → Task 3 → Ergebnis
   Jeder Task wird nacheinander abgearbeitet.
   Der Output von Task N wird als Kontext für Task N+1 verfügbar.

2. Process.hierarchical
   → Manager → delegiert → Agent A (Task 1) → Agent B (Task 2) → ...
   Ein automatisch erstellter (oder manuell definierter) Manager-Agent
   entscheidet, welcher Agent welche Aufgabe bekommt.
   Brauchst du: manager_llm="..." oder manager_agent=Agent(...)
"""


# ─── Beispiel-Crews ──────────────────────────────────────────────────────────

def beispiel_crews(agents, tasks, my_llm):
    """Zeigt verschiedene Crew-Konfigurationen."""
    researcher, writer = agents
    t1, t2 = tasks
    
    # Standard: Sequential
    crew_simple = Crew(
        agents=[researcher, writer],
        tasks=[t1, t2],
        process=Process.sequential,
        verbose=True,
    )
    
    # Mit Memory
    crew_with_memory = Crew(
        agents=[researcher, writer],
        tasks=[t1, t2],
        process=Process.sequential,
        verbose=True,
        memory=True,  # ← Agenten teilen sich einen Speicher
    )
    
    # Hierarchical (mit Manager)
    crew_hierarchical = Crew(
        agents=[researcher, writer],
        tasks=[t1, t2],
        process=Process.hierarchical,
        manager_llm=my_llm,  # ← LLM für den automatischen Manager
        verbose=True,
    )
    
    return crew_simple, crew_with_memory, crew_hierarchical


# =============================================================================
# 📊 TEIL 5: ERGEBNISSE AUSWERTEN
# =============================================================================
"""
ERGEBNIS-ZUGRIFF
-----------------

result = crew.kickoff()
"""


# =============================================================================
# 💡 TEIL 7: TIPPS & BEST PRACTICES
# =============================================================================
"""
HÄUFIGE FEHLER & LÖSUNGEN
--------------------------

1. ❌ Agent nutzt Tool nicht
   → Die `description` des Tools muss klar erklären, WANN es nützlich ist.
   → Tipp: In der Task-Description explizit sagen: "Nutze das RAG System."

2. ❌ Agent halluziniert statt Tool zu nutzen
   → `allow_delegation=False` setzen
   → Klare `expected_output` in der Task definieren
   → `max_iter` erhöhen, damit der Agent mehr Versuche hat

3. ❌ Server hängt beim Import
   → Module-Level Code (z.B. ChromaDB init) wird beim Import ausgeführt!
   → Lösung: Lazy Loading verwenden (siehe agents_router.py)

4. ❌ Telemetry-Timeout (app.crewai.com)
   → Am Anfang der Datei setzen:
       os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
       os.environ["OTEL_SDK_DISABLED"] = "true"

5. ❌ ANSI-Farbcodes im Output
   → `import re; re.sub(r'\\x1b\\[[0-9;]*m', '', text)` zum Entfernen

6. ❌ Agent gibt falsches JSON-Format
   → `output_pydantic=MeinModel` erzwingt das Schema
   → Separaten "Formatter"-Agenten verwenden

7. ❌ Tasks laufen in falscher Reihenfolge
   → `context=[vorheriger_task]` explizit setzen
   → Oder `Process.sequential` verwenden
"""


# =============================================================================
# 🎓 ZUSAMMENFASSUNG: SO BAUT MAN EINE CREW
# =============================================================================
"""
KURZANLEITUNG (Copy-Paste Template)
------------------------------------

from workshops.crewai_intro.tools import wikipedia_tool, rag_search_tool
from crewai import Agent, Task, Crew, Process

# 1. Tools auswählen (aus tools.py importieren)

# 2. Agenten definieren
researcher = Agent(
    role="Researcher",
    goal="Finde Informationen",
    backstory="Du bist ein Experte.",
    tools=[wikipedia_tool, rag_search_tool],
    llm="openai/qwen2.5:3b",
    verbose=True,
)

writer = Agent(
    role="Writer",
    goal="Schreibe verständliche Texte",
    backstory="Du bist ein Redakteur.",
    llm="openai/qwen2.5:3b",
    verbose=True,
)

# 3. Tasks definieren
t1 = Task(
    description="Recherchiere zu 'Was ist KI?'",
    expected_output="Faktenliste",
    agent=researcher,
)

t2 = Task(
    description="Schreibe eine Zusammenfassung.",
    expected_output="Kurzer Erklärtext",
    agent=writer,
    context=[t1],
)

# 4. Crew zusammenstellen und starten
crew = Crew(agents=[researcher, writer], tasks=[t1, t2], verbose=True)
result = crew.kickoff()
print(result)
"""
