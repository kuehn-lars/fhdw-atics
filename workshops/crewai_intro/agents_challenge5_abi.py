"""
CHALLENGE 5 - ABI MISSION PLANNER
=================================

Ziel:
Ein Abi-Team plant eine "klimaneutrale Projektwoche" fuer die Schule.
Die Loesung muss fachlich korrekt, finanziell realistisch, didaktisch sinnvoll
und organisatorisch umsetzbar sein.

Warum mindestens 6 Agenten?
- Faktencheck braucht externe Recherche-Tools.
- Budgetrechnung braucht mathematische Verifikation.
- Zeitplanung braucht Constraint-Optimierung.
- Didaktik braucht paedagogische Ableitung aus den Ergebnissen.
- Risikoanalyse braucht ein separates Sicherheits- und Umsetzungs-Review.
- Finales Reporting braucht konsistente Zusammenfuehrung aller Artefakte.
Ein einzelner Agent ohne diese Spezialisierung und Zwischenabnahmen soll die
Aufgabe nicht loesen.

INPUT FORMAT (ChallengeInput):
{
  "challenge_name": str,
  "team_name": str,
  "grade_level": str,
  "participants": int,
  "total_budget_eur": float,
  "max_hours_total": int,
  "hard_constraints": [str, ...],
  "module_pool": [
    {
      "module_id": str,
      "title": str,
      "duration_hours": int,
      "cost_eur": float,
      "co2_reduction_points": int,
      "skill_focus": [str, ...],
      "required_room": str
    }, ...
  ],
  "claims_to_verify": [
    {
      "claim_id": str,
      "claim_text": str,
      "source_name": str,
      "source_url": str
    }, ...
  ],
  "output_language": "de" | "en"
}

OUTPUT FORMAT (AbiMissionReport / JSON):
{
  "challenge_name": str,
  "team_name": str,
  "selected_modules": [...],
  "excluded_module_ids": [...],
  "verified_claims": [...],
  "budget_plan": {...},
  "schedule": [...],
  "pedagogical_strategy": str,
  "communication_pitch": str,
  "risk_register": [...],
  "quality_checks": [...],
  "why_not_single_agent": [...],
  "final_recommendation": str
}
"""

import os
import sys
from typing import List, Literal

from pydantic import BaseModel, Field, ValidationError, model_validator

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["OPENAI_API_BASE"] = "http://localhost:11434/v1"
os.environ["OPENAI_API_KEY"] = "NA"

from crewai import Agent, Crew, Process, Task

from config.settings import settings
from workshops.crewai_intro.tools import (
    datetime_tool,
    json_formatter_tool,
    math_tool,
    python_repl_tool,
    text_summarizer_tool,
    web_scraper_tool,
    wikipedia_tool,
)

my_llm = f"openai/{settings.local_model}"


class ModuleOption(BaseModel):
    module_id: str = Field(..., description="Eindeutige Kennung des Moduls")
    title: str = Field(..., description="Titel des Moduls")
    duration_hours: int = Field(..., ge=1, le=8)
    cost_eur: float = Field(..., ge=0)
    co2_reduction_points: int = Field(..., ge=0, le=100)
    skill_focus: List[str] = Field(..., min_length=1)
    required_room: str = Field(..., description="Raumanforderung")


class SourceClaim(BaseModel):
    claim_id: str
    claim_text: str
    source_name: str
    source_url: str


class ChallengeInput(BaseModel):
    challenge_name: str
    team_name: str
    grade_level: str
    participants: int = Field(..., ge=5, le=120)
    total_budget_eur: float = Field(..., gt=0)
    max_hours_total: int = Field(..., ge=6, le=40)
    hard_constraints: List[str] = Field(..., min_length=3)
    module_pool: List[ModuleOption] = Field(..., min_length=6)
    claims_to_verify: List[SourceClaim] = Field(..., min_length=4)
    output_language: Literal["de", "en"] = "de"

    @model_validator(mode="after")
    def validate_complexity(self):
        unique_rooms = {m.required_room for m in self.module_pool}
        if len(unique_rooms) < 2:
            raise ValueError("Es werden mindestens zwei unterschiedliche Raeume benoetigt.")
        if not any("budget" in c.lower() or "kosten" in c.lower() for c in self.hard_constraints):
            raise ValueError("Mindestens eine harte Budget-/Kostenbedingung fehlt.")
        return self


class VerifiedClaim(BaseModel):
    claim_id: str
    verdict: Literal["korrekt", "unsicher", "falsch"]
    evidence: str
    used_tool: Literal["wikipedia_tool", "web_scraper_tool", "both", "none"]


class SelectedModule(BaseModel):
    module_id: str
    title: str
    planned_hours: int = Field(..., ge=1, le=8)
    planned_cost_eur: float = Field(..., ge=0)
    abi_competency: str
    rationale: str


class BudgetPlan(BaseModel):
    budget_limit_eur: float = Field(..., ge=0)
    planned_total_eur: float = Field(..., ge=0)
    remaining_eur: float
    reserve_ratio: float = Field(..., ge=0, le=1)
    cost_per_student_eur: float = Field(..., ge=0)


class ScheduleSlot(BaseModel):
    day: int = Field(..., ge=1, le=5)
    start: str = Field(..., description="Format HH:MM")
    end: str = Field(..., description="Format HH:MM")
    module_id: str
    room: str
    facilitator_agent: str


class RiskItem(BaseModel):
    risk: str
    probability: Literal["niedrig", "mittel", "hoch"]
    impact: Literal["niedrig", "mittel", "hoch"]
    mitigation: str
    owner: str


class AbiMissionReport(BaseModel):
    challenge_name: str
    team_name: str
    selected_modules: List[SelectedModule] = Field(..., min_length=3)
    excluded_module_ids: List[str]
    verified_claims: List[VerifiedClaim] = Field(..., min_length=4)
    budget_plan: BudgetPlan
    schedule: List[ScheduleSlot] = Field(..., min_length=3)
    pedagogical_strategy: str
    communication_pitch: str
    risk_register: List[RiskItem] = Field(..., min_length=4)
    quality_checks: List[str] = Field(..., min_length=6)
    why_not_single_agent: List[str] = Field(..., min_length=6)
    final_recommendation: str


def create_agents():
    input_architect = Agent(
        role="Input-Architekt",
        goal=(
            "Normalisiere den Challenge-Input in eine klare Datengrundlage mit "
            "verwertbaren Constraints fuer die Folgeagenten."
        ),
        backstory=(
            "Du arbeitest wie ein Datenarchitekt in einem Schulprojekt-Team und "
            "lieferst die verbindliche Struktur fuer alle Folgeentscheidungen."
        ),
        tools=[json_formatter_tool, text_summarizer_tool, datetime_tool],
        llm=my_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=8,
    )

    fact_checker = Agent(
        role="Fakten- und Quellenpruefer",
        goal=(
            "Pruefe alle Claims mit Wikipedia und ggf. Originalquelle und gib "
            "fuer jeden Claim ein belastbares Urteil ab."
        ),
        backstory=(
            "Du bist Recherche-Lead und kennzeichnest Behauptungen nur dann als "
            "korrekt, wenn die Evidenz belastbar ist."
        ),
        tools=[wikipedia_tool, web_scraper_tool, text_summarizer_tool],
        llm=my_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )

    budget_analyst = Agent(
        role="Budget- und Matheanalyst",
        goal=(
            "Waehle ein kostenrealistisches Modulpaket, berechne Kennzahlen und "
            "halte alle Budgetgrenzen strikt ein."
        ),
        backstory=(
            "Du bist Mathe-LK-Tutor und kaufmaennischer Planer. Jeder Betrag muss "
            "nachvollziehbar gerechnet sein."
        ),
        tools=[math_tool, python_repl_tool, json_formatter_tool],
        llm=my_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )

    schedule_optimizer = Agent(
        role="Stundenplan-Optimierer",
        goal=(
            "Erzeuge einen konfliktfreien Ablaufplan (Tag, Uhrzeit, Raum), der "
            "zu Budget, Dauer und Hard Constraints passt."
        ),
        backstory=(
            "Du koordinierst Schulprojekte und bist spezialisiert auf robuste "
            "Zeit- und Raumplanung mit mehreren Abhaengigkeiten."
        ),
        tools=[python_repl_tool, datetime_tool, json_formatter_tool],
        llm=my_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )

    pedagogy_coach = Agent(
        role="Didaktik-Coach",
        goal=(
            "Uebersetze das fachliche Ergebnis in einen starken Abi-Lernplan mit "
            "klaren Kompetenzzielen und motivierender Kommunikation."
        ),
        backstory=(
            "Du bist Lehrer und Curriculum-Coach. Du machst aus Daten und Fakten "
            "eine Lernstrategie, die in der Schule wirklich funktioniert."
        ),
        tools=[text_summarizer_tool, wikipedia_tool],
        llm=my_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=8,
    )

    risk_manager = Agent(
        role="Risiko- und Umsetzungsmanager",
        goal=(
            "Identifiziere die groessten Projekt-Risiken und liefere pro Risiko "
            "konkrete Gegenmassnahmen und Verantwortlichkeiten."
        ),
        backstory=(
            "Du arbeitest wie ein PMO-Lead: kein Plan geht live ohne sauberes "
            "Risiko-Register."
        ),
        tools=[web_scraper_tool, text_summarizer_tool, json_formatter_tool],
        llm=my_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=8,
    )

    final_editor = Agent(
        role="Abschlussredakteur",
        goal=(
            "Fuehre alle Teilresultate konsistent zu einem finalen JSON-Bericht "
            "im AbiMissionReport-Format zusammen."
        ),
        backstory=(
            "Du bist verantwortlich fuer den finalen Abgabebericht. Das Ergebnis "
            "muss fachlich konsistent, valide und direkt praesentierbar sein."
        ),
        tools=[json_formatter_tool, python_repl_tool, text_summarizer_tool],
        llm=my_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=12,
    )

    return (
        input_architect,
        fact_checker,
        budget_analyst,
        schedule_optimizer,
        pedagogy_coach,
        risk_manager,
        final_editor,
    )


def create_tasks(challenge_input: ChallengeInput, agents: tuple) -> list:
    (
        input_architect,
        fact_checker,
        budget_analyst,
        schedule_optimizer,
        pedagogy_coach,
        risk_manager,
        final_editor,
    ) = agents

    input_json = challenge_input.model_dump_json(indent=2)

    task_input_design = Task(
        description=f"""
        Erzeuge eine normalisierte Arbeitsgrundlage aus folgendem Input:
        {input_json}

        Liefere:
        1) Eine kompakte Constraint-Liste (max 10 Punkte)
        2) Eine modulare Tabelle (module_id, stunden, kosten, raum, co2_punkte)
        3) Explizite no-go Regeln aus den Hard Constraints
        4) Ein Datenqualitaetsfazit (1-2 Saetze)
        """,
        expected_output=(
            "Constraint-Liste, Modultabelle, no-go Regeln, Datenqualitaetsfazit."
        ),
        agent=input_architect,
    )

    task_fact_check = Task(
        description=f"""
        Pruefe alle Claims aus dem Input mit Tools.
        Input:
        {input_json}

        Fuer jeden Claim:
        - claim_id
        - verdict: korrekt/unsicher/falsch
        - kurze Evidenz
        - used_tool: wikipedia_tool/web_scraper_tool/both/none

        Kein Claim darf ausgelassen werden.
        """,
        expected_output="Vollstaendige Claim-Pruefung mit Urteil und Evidenz je claim_id.",
        agent=fact_checker,
        context=[task_input_design],
    )

    task_budget = Task(
        description="""
        Nutze die Input-Analyse und den Faktencheck:
        - Waehle mindestens 3 Module aus.
        - Summe der Modulstunden darf max_hours_total nicht ueberschreiten.
        - Summe der Kosten darf total_budget_eur nicht ueberschreiten.
        - Berechne reserve_ratio und cost_per_student_eur.
        - Liste auch ausgeschlossene Module mit kurzem Grund auf.
        """,
        expected_output=(
            "Ausgewaehlte Module mit Kosten/Stunden, ausgeschlossene Module, "
            "vollstaendiger BudgetPlan."
        ),
        agent=budget_analyst,
        context=[task_input_design, task_fact_check],
    )

    task_schedule = Task(
        description="""
        Erzeuge auf Basis der Budgetauswahl einen umsetzbaren Ablaufplan:
        - mind. 3 Schedule-Slots
        - format: day(1-5), start(HH:MM), end(HH:MM), module_id, room
        - keine Raumkonflikte am gleichen Tag/Zeitslot
        - Stundenbudget darf nicht ueberschritten werden
        """,
        expected_output="Konfliktfreier Ablaufplan mit day/start/end/module_id/room.",
        agent=schedule_optimizer,
        context=[task_input_design, task_budget],
    )

    task_didactic = Task(
        description="""
        Entwickle eine Abi-taugliche Lern- und Kommunikationsstrategie:
        - pedagogical_strategy: 1 klarer Absatz
        - communication_pitch: max 120 Woerter fuer Schulleitung + Mitschueler
        - Verknuepfe die ausgewaehlten Module mit konkreten Abi-Kompetenzen
        """,
        expected_output="Didaktische Strategie, Pitch und Kompetenzmapping.",
        agent=pedagogy_coach,
        context=[task_input_design, task_fact_check, task_budget, task_schedule],
    )

    task_risk = Task(
        description="""
        Erstelle ein Risiko-Register mit mindestens 4 Risiken:
        - risk
        - probability: niedrig/mittel/hoch
        - impact: niedrig/mittel/hoch
        - mitigation
        - owner

        Risiken sollen organisatorisch UND inhaltlich sein.
        """,
        expected_output="Risiko-Register mit mindestens 4 vollstaendigen Eintraegen.",
        agent=risk_manager,
        context=[task_input_design, task_budget, task_schedule, task_didactic],
    )

    task_final_report = Task(
        description=f"""
        Erzeuge den finalen Bericht als valides JSON gemaess AbiMissionReport.
        Nutze alle vorigen Task-Outputs.

        Zwingend enthalten:
        - challenge_name = "{challenge_input.challenge_name}"
        - team_name = "{challenge_input.team_name}"
        - mindestens 3 selected_modules
        - alle claims_to_verify aus Input als verified_claims
        - budget_plan inklusive reserve_ratio
        - konfliktfreie schedule-Liste
        - mindestens 4 risk_register Eintraege
        - quality_checks: mindestens 6 konkrete Checks
        - why_not_single_agent: mindestens 6 konkrete Gruende, je Rolle ein Grund
        - final_recommendation: klare Entscheidung mit 2-4 Saetzen

        Gib nur den finalen JSON-Bericht aus.
        """,
        expected_output="Vollstaendiger AbiMissionReport als JSON.",
        agent=final_editor,
        context=[
            task_input_design,
            task_fact_check,
            task_budget,
            task_schedule,
            task_didactic,
            task_risk,
        ],
        output_pydantic=AbiMissionReport,
    )

    return [
        task_input_design,
        task_fact_check,
        task_budget,
        task_schedule,
        task_didactic,
        task_risk,
        task_final_report,
    ]


def _validate_input(challenge_input) -> ChallengeInput:
    if isinstance(challenge_input, ChallengeInput):
        return challenge_input
    try:
        return ChallengeInput.model_validate(challenge_input)
    except ValidationError as exc:
        raise ValueError(f"Ungueltiges ChallengeInput-Format:\n{exc}") from exc


challenges = [
    {
        "id": 1,
        "challenge_name": "Klimaneutrale Abi-Projektwoche 2026",
        "team_name": "Q2 Umweltkurs",
        "grade_level": "Q2",
        "participants": 28,
        "total_budget_eur": 3200.0,
        "max_hours_total": 16,
        "hard_constraints": [
            "Kosten muessen innerhalb des Budgets bleiben",
            "Mindestens ein Experiment und ein Debattenformat enthalten",
            "Alle Module muessen ohne externe Uebernachtung umsetzbar sein",
            "Plan muss der Schulleitung in 5 Minuten praesentierbar sein",
        ],
        "module_pool": [
            {
                "module_id": "M1",
                "title": "CO2-Fussabdruck Workshop",
                "duration_hours": 3,
                "cost_eur": 380.0,
                "co2_reduction_points": 45,
                "skill_focus": ["Datenkompetenz", "Alltagsbezug", "Reflexion"],
                "required_room": "Computerraum",
            },
            {
                "module_id": "M2",
                "title": "Debatte: Klima, Wirtschaft, Gerechtigkeit",
                "duration_hours": 2,
                "cost_eur": 120.0,
                "co2_reduction_points": 15,
                "skill_focus": ["Argumentation", "Urteilsbildung"],
                "required_room": "Aula",
            },
            {
                "module_id": "M3",
                "title": "Solar-Mini-Lab",
                "duration_hours": 4,
                "cost_eur": 980.0,
                "co2_reduction_points": 70,
                "skill_focus": ["Experiment", "Naturwissenschaft"],
                "required_room": "Physikraum",
            },
            {
                "module_id": "M4",
                "title": "Stadtklima-Mapping zu Fuss",
                "duration_hours": 3,
                "cost_eur": 210.0,
                "co2_reduction_points": 35,
                "skill_focus": ["Geographie", "Datenanalyse"],
                "required_room": "Aussenbereich",
            },
            {
                "module_id": "M5",
                "title": "Muellkreislauf und Circular Economy",
                "duration_hours": 2,
                "cost_eur": 260.0,
                "co2_reduction_points": 30,
                "skill_focus": ["Wirtschaft", "Nachhaltigkeit"],
                "required_room": "Biologieraum",
            },
            {
                "module_id": "M6",
                "title": "Pitch-Training fuer Schulleitung",
                "duration_hours": 2,
                "cost_eur": 150.0,
                "co2_reduction_points": 10,
                "skill_focus": ["Kommunikation", "Teamarbeit"],
                "required_room": "Aula",
            },
            {
                "module_id": "M7",
                "title": "Externe Exkursion Windpark",
                "duration_hours": 6,
                "cost_eur": 1900.0,
                "co2_reduction_points": 80,
                "skill_focus": ["Praxisbezug", "Technik"],
                "required_room": "Exkursion",
            },
        ],
        "claims_to_verify": [
            {
                "claim_id": "C1",
                "claim_text": "Deutschland will bis 2045 treibhausgasneutral sein.",
                "source_name": "Bundesregierung",
                "source_url": "https://www.bundesregierung.de/",
            },
            {
                "claim_id": "C2",
                "claim_text": "Photovoltaik ist in Deutschland 2025 die groesste Stromquelle.",
                "source_name": "Fraunhofer ISE",
                "source_url": "https://www.ise.fraunhofer.de/",
            },
            {
                "claim_id": "C3",
                "claim_text": "Methan wirkt auf 20 Jahre deutlich staerker als CO2.",
                "source_name": "IPCC",
                "source_url": "https://www.ipcc.ch/",
            },
            {
                "claim_id": "C4",
                "claim_text": "Die Erwaermung seit vorindustrieller Zeit liegt bei etwa 1.1 bis 1.3 Grad.",
                "source_name": "WMO",
                "source_url": "https://wmo.int/",
            },
        ],
        "output_language": "de",
    }
]

CHALLENGE_INPUT = challenges[0]


def run_challenge(challenge_input: dict) -> object:
    validated_input = _validate_input(challenge_input)
    agents = create_agents()
    tasks = create_tasks(validated_input, agents)

    crew = Crew(
        agents=list(agents),
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )
    return crew.kickoff()


if __name__ == "__main__":
    import json

    result = run_challenge(CHALLENGE_INPUT)
    if getattr(result, "pydantic", None):
        print(json.dumps(result.pydantic.model_dump(), indent=2, ensure_ascii=False))
    else:
        print(result)
