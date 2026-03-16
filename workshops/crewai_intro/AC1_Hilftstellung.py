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
    
"""

# =============================================================================
# 🛠️  TEIL 1: TOOLS
# =============================================================================

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