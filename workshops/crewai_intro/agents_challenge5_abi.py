"""
CHALLENGE 5 - ABI STOCK ANALYSIS MISSION
========================================

Ziel:
Ein Abi-Kurs (Wirtschaft) soll ein kleines Aktien-Portfolio fuer ein
Schulprojekt bauen. Die Loesung muss datenbasiert, rechnerisch sauber,
risikobewusst und praesentierbar sein.

Warum 6+ Agenten?
- Quellen/Faktencheck von Markt-Behauptungen
- Fundamentalanalyse und Kennzahlenrechnung
- Portfolio-Allokation unter harten Limits
- Risiko- und Szenarioanalyse
- Didaktische Uebersetzung fuer Abi-Niveau
- Finales Reporting als sauberes JSON
Diese Schritte sind absichtlich getrennt, damit kein Einzelagent die Aufgabe
alleine "durchraten" kann.

INPUT FORMAT (StockChallengeInput):
{
  "challenge_name": str,
  "team_name": str,
  "grade_level": str,
  "capital_eur": float,
  "investment_horizon_months": int,
  "risk_profile": "defensiv" | "ausgewogen" | "offensiv",
  "max_single_position_pct": int,
  "hard_constraints": [str, ...],
  "company_universe": [
    {
      "ticker": str,
      "name": str,
      "sector": str,
      "price_eur": float,
      "pe_ratio": float,
      "eps_growth_pct": float,
      "debt_to_equity": float,
      "volatility_1y_pct": float,
      "dividend_yield_pct": float,
      "esg_score": int
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

OUTPUT FORMAT (StockMissionReport / JSON):
{
  "challenge_name": str,
  "team_name": str,
  "selected_stocks": [...],
  "excluded_tickers": [...],
  "verified_claims": [...],
  "allocation_plan": {...},
  "scenario_analysis": [...],
  "risk_register": [...],
  "didactic_explanation": str,
  "decision_pitch": str,
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
    json_formatter_tool,
    math_tool,
    python_repl_tool,
    text_summarizer_tool,
    web_scraper_tool,
    wikipedia_tool,
)

my_llm = f"openai/{settings.local_model}"


class CompanyOption(BaseModel):
    ticker: str
    name: str
    sector: str
    price_eur: float = Field(..., gt=0)
    pe_ratio: float = Field(..., ge=0)
    eps_growth_pct: float = Field(..., ge=-100, le=200)
    debt_to_equity: float = Field(..., ge=0, le=10)
    volatility_1y_pct: float = Field(..., ge=0, le=200)
    dividend_yield_pct: float = Field(..., ge=0, le=20)
    esg_score: int = Field(..., ge=0, le=100)


class SourceClaim(BaseModel):
    claim_id: str
    claim_text: str
    source_name: str
    source_url: str


class StockChallengeInput(BaseModel):
    challenge_name: str
    team_name: str
    grade_level: str
    capital_eur: float = Field(..., gt=1000)
    investment_horizon_months: int = Field(..., ge=6, le=60)
    risk_profile: Literal["defensiv", "ausgewogen", "offensiv"]
    max_single_position_pct: int = Field(..., ge=10, le=60)
    hard_constraints: List[str] = Field(..., min_length=3)
    company_universe: List[CompanyOption] = Field(..., min_length=6)
    claims_to_verify: List[SourceClaim] = Field(..., min_length=4)
    output_language: Literal["de", "en"] = "de"

    @model_validator(mode="after")
    def validate_complexity(self):
        sectors = {c.sector for c in self.company_universe}
        if len(sectors) < 3:
            raise ValueError("Mindestens 3 verschiedene Sektoren noetig.")
        if not any("max" in c.lower() or "position" in c.lower() for c in self.hard_constraints):
            raise ValueError("Mindestens eine Positionsgrenze in hard_constraints fehlt.")
        return self


class VerifiedClaim(BaseModel):
    claim_id: str
    verdict: Literal["korrekt", "unsicher", "falsch"]
    evidence: str
    used_tool: Literal["wikipedia_tool", "web_scraper_tool", "both", "none"]


class SelectedStock(BaseModel):
    ticker: str
    name: str
    weight_pct: float = Field(..., ge=0, le=100)
    investment_eur: float = Field(..., ge=0)
    investment_thesis: str
    key_metric_note: str


class AllocationPlan(BaseModel):
    capital_eur: float = Field(..., gt=0)
    invested_eur: float = Field(..., ge=0)
    cash_reserve_eur: float = Field(..., ge=0)
    cash_reserve_pct: float = Field(..., ge=0, le=100)
    weighted_avg_pe: float = Field(..., ge=0)
    weighted_avg_volatility_pct: float = Field(..., ge=0)


class ScenarioResult(BaseModel):
    scenario: Literal["bull", "base", "bear"]
    expected_portfolio_return_pct: float = Field(..., ge=-100, le=200)
    assumption: str


class RiskItem(BaseModel):
    risk: str
    probability: Literal["niedrig", "mittel", "hoch"]
    impact: Literal["niedrig", "mittel", "hoch"]
    mitigation: str
    owner: str


class StockMissionReport(BaseModel):
    challenge_name: str
    team_name: str
    selected_stocks: List[SelectedStock] = Field(..., min_length=3)
    excluded_tickers: List[str]
    verified_claims: List[VerifiedClaim] = Field(..., min_length=4)
    allocation_plan: AllocationPlan
    scenario_analysis: List[ScenarioResult] = Field(..., min_length=3)
    risk_register: List[RiskItem] = Field(..., min_length=4)
    didactic_explanation: str
    decision_pitch: str
    quality_checks: List[str] = Field(..., min_length=6)
    why_not_single_agent: List[str] = Field(..., min_length=6)
    final_recommendation: str


def create_agents():
    input_architect = Agent(
        role="Input-Architekt",
        goal="Normalisiere den Input und extrahiere harte, maschinenlesbare Constraints.",
        backstory=(
            "Du bist der Daten-Moderator der Boersen-AG und sorgst fuer eine "
            "klare Ausgangsbasis fuer alle Folgeagenten."
        ),
        tools=[json_formatter_tool, text_summarizer_tool],
        llm=my_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=8,
    )

    fact_checker = Agent(
        role="Quellen- und Faktenpruefer",
        goal=(
            "Pruefe Marktaussagen mit Wikipedia und Webquellen und liefere "
            "pro Claim ein nachvollziehbares Urteil."
        ),
        backstory=(
            "Du arbeitest wie ein Research-Analyst. Ohne belastbare Quelle wird "
            "kein Claim als korrekt akzeptiert."
        ),
        tools=[wikipedia_tool, web_scraper_tool, text_summarizer_tool],
        llm=my_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )

    fundamental_analyst = Agent(
        role="Fundamentalanalyst",
        goal=(
            "Bewerte Unternehmen anhand Kennzahlen (PE, Wachstum, Verschuldung, "
            "Volatilitaet, ESG) und identifiziere Kandidaten."
        ),
        backstory=(
            "Du bist Mathe- und Wirtschaftsprofi. Jede Auswahl muss sich in den "
            "Zahlen begruenden lassen."
        ),
        tools=[math_tool, python_repl_tool, json_formatter_tool],
        llm=my_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )

    portfolio_optimizer = Agent(
        role="Portfolio-Optimierer",
        goal=(
            "Berechne eine Allokation mit Positionslimits, Cash-Reserve und "
            "risikoprofilgerechter Verteilung."
        ),
        backstory=(
            "Du optimierst Portfolios unter harten Nebenbedingungen und lieferst "
            "einen umsetzbaren Verteilungsplan."
        ),
        tools=[python_repl_tool, math_tool, json_formatter_tool],
        llm=my_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )

    risk_manager = Agent(
        role="Risiko- und Szenario-Manager",
        goal=(
            "Erzeuge Bull/Base/Bear Szenarien und ein Risiko-Register mit klaren "
            "Massnahmen und Verantwortlichkeiten."
        ),
        backstory=(
            "Du bist verantwortlich dafuer, dass der Plan nicht nur gut aussieht, "
            "sondern auch in schlechten Marktphasen standhaelt."
        ),
        tools=[python_repl_tool, web_scraper_tool, text_summarizer_tool],
        llm=my_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )

    didactic_coach = Agent(
        role="Didaktik-Coach",
        goal=(
            "Uebersetze die Analyse in eine Abi-verstaendliche Erklaerung und "
            "einen praegnanten Pitch fuer die Klasse."
        ),
        backstory=(
            "Du bist Lehrkraft fuer Wirtschaft und machst aus komplexer Analyse "
            "eine klare Lernbotschaft."
        ),
        tools=[text_summarizer_tool, wikipedia_tool],
        llm=my_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=8,
    )

    final_editor = Agent(
        role="Final-Reporter",
        goal=(
            "Fuehre alle Teilresultate zu einem konsistenten, validen JSON im "
            "StockMissionReport-Format zusammen."
        ),
        backstory=(
            "Du verantwortest die finale Abgabe. Nur saubere Struktur und "
            "konsistente Zahlen werden akzeptiert."
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
        fundamental_analyst,
        portfolio_optimizer,
        risk_manager,
        didactic_coach,
        final_editor,
    )


def create_tasks(challenge_input: StockChallengeInput, agents: tuple) -> list:
    (
        input_architect,
        fact_checker,
        fundamental_analyst,
        portfolio_optimizer,
        risk_manager,
        didactic_coach,
        final_editor,
    ) = agents

    input_json = challenge_input.model_dump_json(indent=2)

    task_input_design = Task(
        description=f"""
        Analysiere und normalisiere den Input:
        {input_json}

        Liefere:
        1) Harte Constraints (max 10 Bullet Points)
        2) Kennzahlen-Tabelle aller Unternehmen
        3) No-Go Regeln fuer die Portfolio-Optimierung
        """,
        expected_output="Constraint-Liste, Kennzahlen-Tabelle, No-Go Regeln.",
        agent=input_architect,
    )

    task_fact_check = Task(
        description=f"""
        Pruefe alle Claims im Input mit Tools.
        Input:
        {input_json}

        Fuer jeden Claim:
        - claim_id
        - verdict: korrekt/unsicher/falsch
        - evidence
        - used_tool: wikipedia_tool/web_scraper_tool/both/none

        Kein Claim darf fehlen.
        """,
        expected_output="Vollstaendige Claim-Pruefung fuer alle claim_id.",
        agent=fact_checker,
        context=[task_input_design],
    )

    task_fundamental = Task(
        description="""
        Erstelle ein Ranking der Aktien aus company_universe:
        - Begruende Auswahl/Abwahl mit Kennzahlen
        - Markiere mindestens 3 starke und mindestens 2 schwache Kandidaten
        - Keine finale Gewichtung hier, nur qualitative und quantitative Voranalyse
        """,
        expected_output="Fundamentales Ranking mit Starken, Schwachen und Gruenden.",
        agent=fundamental_analyst,
        context=[task_input_design, task_fact_check],
    )

    task_allocation = Task(
        description="""
        Erzeuge eine finale Allokation:
        - Mindestens 3 Aktien auswaehlen
        - Jede Position <= max_single_position_pct
        - Summe der Gewichte <= 100%
        - invested_eur <= capital_eur
        - Cash-Reserve ausweisen
        - weighted_avg_pe und weighted_avg_volatility_pct berechnen
        """,
        expected_output="Ausgewaehlte Aktien mit Gewichtung und vollstaendiger AllocationPlan.",
        agent=portfolio_optimizer,
        context=[task_input_design, task_fact_check, task_fundamental],
    )

    task_risk = Task(
        description="""
        Erstelle:
        1) Szenarioanalyse mit bull/base/bear (jeweils erwartete Portfoliorendite)
        2) Risiko-Register mit mindestens 4 Risiken
           (probability, impact, mitigation, owner)
        """,
        expected_output="Szenarioanalyse und Risiko-Register.",
        agent=risk_manager,
        context=[task_input_design, task_allocation, task_fact_check],
    )

    task_didactic = Task(
        description="""
        Erzeuge:
        - didactic_explanation: kurze, klare Abi-Erklaerung (6-10 Saetze)
        - decision_pitch: max 120 Woerter fuer 2-min Vorstellung in der Klasse
        """,
        expected_output="Didaktische Erklaerung und Pitch.",
        agent=didactic_coach,
        context=[task_input_design, task_fundamental, task_allocation, task_risk],
    )

    task_final_report = Task(
        description=f"""
        Erzeuge den finalen Bericht als valides JSON gemaess StockMissionReport.
        Nutze alle bisherigen Task-Ergebnisse.

        Zwingend:
        - challenge_name = "{challenge_input.challenge_name}"
        - team_name = "{challenge_input.team_name}"
        - mindestens 3 selected_stocks
        - alle claims_to_verify als verified_claims
        - allocation_plan mit invested/cash/weighted averages
        - scenario_analysis mit bull/base/bear
        - risk_register mit mindestens 4 Eintraegen
        - quality_checks mit mindestens 6 konkreten Checks
        - why_not_single_agent mit mindestens 6 konkreten Gruenden
        - final_recommendation mit klarer Entscheidung (2-4 Saetze)

        Ausgabe nur als JSON.
        """,
        expected_output="Vollstaendiger StockMissionReport als JSON.",
        agent=final_editor,
        context=[
            task_input_design,
            task_fact_check,
            task_fundamental,
            task_allocation,
            task_risk,
            task_didactic,
        ],
        output_pydantic=StockMissionReport,
    )

    return [
        task_input_design,
        task_fact_check,
        task_fundamental,
        task_allocation,
        task_risk,
        task_didactic,
        task_final_report,
    ]


def _validate_input(challenge_input) -> StockChallengeInput:
    if isinstance(challenge_input, StockChallengeInput):
        return challenge_input
    try:
        return StockChallengeInput.model_validate(challenge_input)
    except ValidationError as exc:
        raise ValueError(f"Ungueltiges StockChallengeInput-Format:\n{exc}") from exc


challenges = [
    {
        "id": 1,
        "challenge_name": "Abi Trading Lab: KI-Boom vs. Rezessionsangst",
        "team_name": "Leistungskurs Wirtschaft Q2",
        "grade_level": "Q2",
        "capital_eur": 15000.0,
        "investment_horizon_months": 12,
        "risk_profile": "ausgewogen",
        "max_single_position_pct": 30,
        "hard_constraints": [
            "Maximal 30 Prozent pro Einzelposition",
            "Mindestens 4 Aktien aus mindestens 3 Sektoren",
            "Mindestens 15 Prozent Cash Reserve behalten",
            "Keine Aktie mit debt_to_equity ueber 2.0 aufnehmen",
            "Pitch fuer Schulleitung muss in 2 Minuten funktionieren",
        ],
        "company_universe": [
            {
                "ticker": "MSFT",
                "name": "Microsoft Corp.",
                "sector": "Software",
                "price_eur": 402.0,
                "pe_ratio": 34.0,
                "eps_growth_pct": 15.0,
                "debt_to_equity": 0.45,
                "volatility_1y_pct": 23.0,
                "dividend_yield_pct": 0.8,
                "esg_score": 81,
            },
            {
                "ticker": "NVDA",
                "name": "NVIDIA Corp.",
                "sector": "Halbleiter",
                "price_eur": 720.0,
                "pe_ratio": 48.0,
                "eps_growth_pct": 32.0,
                "debt_to_equity": 0.29,
                "volatility_1y_pct": 41.0,
                "dividend_yield_pct": 0.1,
                "esg_score": 65,
            },
            {
                "ticker": "ASML",
                "name": "ASML Holding",
                "sector": "Halbleiter",
                "price_eur": 835.0,
                "pe_ratio": 34.0,
                "eps_growth_pct": 20.0,
                "debt_to_equity": 0.33,
                "volatility_1y_pct": 32.0,
                "dividend_yield_pct": 0.9,
                "esg_score": 69,
            },
            {
                "ticker": "SIE",
                "name": "Siemens AG",
                "sector": "Industrie",
                "price_eur": 184.0,
                "pe_ratio": 20.0,
                "eps_growth_pct": 12.0,
                "debt_to_equity": 0.64,
                "volatility_1y_pct": 22.0,
                "dividend_yield_pct": 2.5,
                "esg_score": 79,
            },
            {
                "ticker": "JNJ",
                "name": "Johnson & Johnson",
                "sector": "Gesundheit",
                "price_eur": 149.0,
                "pe_ratio": 16.0,
                "eps_growth_pct": 5.0,
                "debt_to_equity": 0.52,
                "volatility_1y_pct": 14.0,
                "dividend_yield_pct": 3.1,
                "esg_score": 76,
            },
            {
                "ticker": "ALV",
                "name": "Allianz SE",
                "sector": "Finanzen",
                "price_eur": 292.0,
                "pe_ratio": 11.0,
                "eps_growth_pct": 9.0,
                "debt_to_equity": 0.95,
                "volatility_1y_pct": 18.0,
                "dividend_yield_pct": 4.8,
                "esg_score": 77,
            },
            {
                "ticker": "NESN",
                "name": "Nestle SA",
                "sector": "Konsum",
                "price_eur": 98.0,
                "pe_ratio": 22.0,
                "eps_growth_pct": 6.0,
                "debt_to_equity": 1.42,
                "volatility_1y_pct": 15.0,
                "dividend_yield_pct": 3.0,
                "esg_score": 73,
            },
            {
                "ticker": "ENEL",
                "name": "Enel SpA",
                "sector": "Versorger",
                "price_eur": 6.5,
                "pe_ratio": 13.0,
                "eps_growth_pct": 8.0,
                "debt_to_equity": 1.95,
                "volatility_1y_pct": 19.0,
                "dividend_yield_pct": 5.4,
                "esg_score": 80,
            },
        ],
        "claims_to_verify": [
            {
                "claim_id": "C1",
                "claim_text": "Diversifikation ueber Sektoren kann unsystematisches Risiko reduzieren.",
                "source_name": "Wikipedia Diversifikation",
                "source_url": "https://de.wikipedia.org/wiki/Diversifikation_(Wirtschaft)",
            },
            {
                "claim_id": "C2",
                "claim_text": "Ein niedriges KGV allein reicht nicht fuer eine gute Kaufentscheidung.",
                "source_name": "Wikipedia KGV",
                "source_url": "https://de.wikipedia.org/wiki/Kurs-Gewinn-Verh%C3%A4ltnis",
            },
            {
                "claim_id": "C3",
                "claim_text": "Hohe Volatilitaet kann kurzfristig zu groesseren Schwankungen und Drawdowns fuehren.",
                "source_name": "Investopedia Volatility",
                "source_url": "https://www.investopedia.com/terms/v/volatility.asp",
            },
            {
                "claim_id": "C4",
                "claim_text": "Dividendenrendite ist eine Kennzahl fuer laufende Ausschuettungen, aber kein Garant fuer Gesamtperformance.",
                "source_name": "Wikipedia Dividendenrendite",
                "source_url": "https://de.wikipedia.org/wiki/Dividendenrendite",
            },
            {
                "claim_id": "C5",
                "claim_text": "Starkes EPS-Wachstum kann hoehere Bewertungen rechtfertigen, erhoeht aber oft Erwartungsrisiken.",
                "source_name": "Investopedia EPS",
                "source_url": "https://www.investopedia.com/terms/e/eps.asp",
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
