"""
CHALLENGE 5 - ABI STOCK ANALYSIS (LIVE + VISUAL)
=================================================

Warum keine "claims" mehr?
- Fuer ein schulnahes Portfolio-Projekt sind harte Constraints und echte
  Marktdaten wichtiger als statische Behauptungslisten.
- Deshalb basiert diese Version auf:
  1) Input-Constraints
  2) Live-/Near-Live-Marktsnapshot (Adapter)
  3) Quantitativer Portfolio-Plan
  4) Visualisierung (PNG-Chart)

INPUT FORMAT (StockChallengeInput):
{
  "challenge_name": str,
  "team_name": str,
  "grade_level": str,
  "scenario_prompt": str,
  "investor_wishes": [str, ...],
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
  "output_language": "de" | "en"
}

OUTPUT FORMAT (StockMissionReport):
{
  "challenge_name": str,
  "team_name": str,
  "scenario_prompt": str,
  "investor_wishes": [...],
  "market_snapshot": [...],
  "market_news": [...],
  "wishes_coverage": [...],
  "selected_stocks": [...],
  "excluded_tickers": [...],
  "allocation_plan": {...},
  "scenario_analysis": [...],
  "risk_register": [...],
  "didactic_explanation": str,
  "decision_pitch": str,
  "visualization_paths": [...],
  "quality_checks": [...],
  "why_not_single_agent": [...],
  "final_recommendation": str
}
"""

import csv
import datetime
import json
import math
import os
import re
import sys
import tempfile
import time
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, ValidationError, model_validator

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["OPENAI_API_BASE"] = "http://localhost:11434/v1"
os.environ["OPENAI_API_KEY"] = "NA"

from crewai import Agent, Crew, Process, Task

from config.settings import settings
from workshops.crewai_intro.tools import (
    current_news_tool,
    json_formatter_tool,
    live_stock_data_tool,
    math_tool,
    python_repl_tool,
    text_summarizer_tool,
    visualization_tool,
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


class StockChallengeInput(BaseModel):
    challenge_name: str
    team_name: str
    grade_level: str
    scenario_prompt: str = Field(..., min_length=10)
    investor_wishes: List[str] = Field(..., min_length=2)
    capital_eur: float = Field(..., gt=1000)
    investment_horizon_months: int = Field(..., ge=6, le=60)
    risk_profile: Literal["defensiv", "ausgewogen", "offensiv"]
    max_single_position_pct: int = Field(..., ge=10, le=60)
    hard_constraints: List[str] = Field(..., min_length=3)
    company_universe: List[CompanyOption] = Field(..., min_length=6)
    output_language: Literal["de", "en"] = "de"

    @model_validator(mode="after")
    def validate_complexity(self):
        sectors = {c.sector for c in self.company_universe}
        if len(sectors) < 3:
            raise ValueError("Mindestens 3 verschiedene Sektoren noetig.")
        if not any("max" in c.lower() or "position" in c.lower() for c in self.hard_constraints):
            raise ValueError("Mindestens eine Positionsgrenze in hard_constraints fehlt.")
        return self


class LiveQuote(BaseModel):
    ticker: str
    name: str
    last_price_eur: float = Field(..., ge=0)
    change_pct_1d: float
    source: str
    as_of_utc: str


class NewsItem(BaseModel):
    ticker_or_topic: str
    title: str
    source: str
    link: str
    relevance_note: str


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
    scenario_prompt: str
    investor_wishes: List[str] = Field(..., min_length=2)
    market_snapshot: List[LiveQuote] = Field(..., min_length=3)
    market_news: List[NewsItem] = Field(..., min_length=3)
    wishes_coverage: List[str] = Field(..., min_length=2)
    selected_stocks: List[SelectedStock] = Field(..., min_length=3)
    excluded_tickers: List[str]
    allocation_plan: AllocationPlan
    scenario_analysis: List[ScenarioResult] = Field(..., min_length=3)
    risk_register: List[RiskItem] = Field(..., min_length=4)
    didactic_explanation: str
    decision_pitch: str
    visualization_paths: List[str] = Field(default_factory=list)
    quality_checks: List[str] = Field(..., min_length=6)
    why_not_single_agent: List[str] = Field(..., min_length=6)
    final_recommendation: str


class ChallengeRunResult:
    def __init__(self, raw_output: object = None, report: Optional[StockMissionReport] = None, **kwargs):
        if raw_output is None and "raw_result" in kwargs:
            raw_output = kwargs["raw_result"]
        self.raw_output = raw_output
        self.pydantic = report

    def __str__(self) -> str:
        if self.pydantic is None:
            return str(self.raw_output)
        return json.dumps(self.pydantic.model_dump(), ensure_ascii=False)


def create_agents(llm_model: Optional[str] = None):
    agent_llm = llm_model or my_llm

    input_architect = Agent(
        role="Input-Architekt",
        goal="Normalisiere den Input und extrahiere klare Constraints fuer die Analyse.",
        backstory=(
            "Du bist Daten-Moderator der Boersen-AG und sorgst fuer eine saubere "
            "Ausgangsbasis fuer alle Folgeagenten."
        ),
        tools=[json_formatter_tool, text_summarizer_tool],
        llm=agent_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=8,
    )

    market_data_adapter = Agent(
        role="Live-Datenadapter",
        goal=(
            "Ziehe aktuelle Kursdaten fuer die Ticker aus dem Input und liefere "
            "ein tabellarisches Marktsnapshot."
        ),
        backstory=(
            "Du bindest externe Marktdaten in die Analyse ein und machst "
            "Datenluecken explizit sichtbar."
        ),
        tools=[live_stock_data_tool, web_scraper_tool, text_summarizer_tool],
        llm=agent_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=8,
    )

    news_analyst = Agent(
        role="News-Analyst",
        goal=(
            "Sammle aktuelle, relevante Nachrichten zu Szenario, Sektoren und "
            "Tickern und leite konkrete Investment-Implikationen ab."
        ),
        backstory=(
            "Du beobachtest Marktnews und trennst Signal von Rauschen. Du verbindest "
            "Headlines mit den Wünschen des Nutzers."
        ),
        tools=[current_news_tool, web_scraper_tool, text_summarizer_tool],
        llm=agent_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=8,
    )

    fundamental_analyst = Agent(
        role="Fundamentalanalyst",
        goal=(
            "Bewerte Unternehmen anhand Kennzahlen und priorisiere sinnvolle "
            "Portfolio-Kandidaten."
        ),
        backstory=(
            "Du bist Mathe- und Wirtschaftsprofi. Jede Auswahl muss mit Kennzahlen "
            "begruendet werden."
        ),
        tools=[math_tool, python_repl_tool, json_formatter_tool],
        llm=agent_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )

    portfolio_optimizer = Agent(
        role="Portfolio-Optimierer",
        goal=(
            "Erzeuge eine Allokation unter Positionslimits, Cash-Reserve und "
            "Risikoprofil."
        ),
        backstory=(
            "Du optimierst Portfolios unter harten Nebenbedingungen und lieferst "
            "einen umsetzbaren Plan."
        ),
        tools=[python_repl_tool, math_tool, visualization_tool, json_formatter_tool],
        llm=agent_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )

    risk_manager = Agent(
        role="Risiko- und Szenario-Manager",
        goal=(
            "Erstelle Bull/Base/Bear-Szenarien und ein Risiko-Register mit "
            "Mitigationsmassnahmen."
        ),
        backstory=(
            "Du sorgst dafuer, dass der Plan auch bei negativen Marktszenarien "
            "durchdacht bleibt."
        ),
        tools=[python_repl_tool, text_summarizer_tool],
        llm=agent_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )

    didactic_coach = Agent(
        role="Didaktik-Coach",
        goal="Uebersetze die Analyse in eine klare, abi-taugliche Erklaerung.",
        backstory=(
            "Du bist Lehrkraft fuer Wirtschaft und machst aus komplexen Zahlen "
            "eine verstaendliche Lernbotschaft."
        ),
        tools=[text_summarizer_tool, wikipedia_tool],
        llm=agent_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=8,
    )

    final_reporter = Agent(
        role="Final-Reporter",
        goal=(
            "Fasse alle Ergebnisse zu einem konsistenten JSON-Bericht zusammen "
            "und referenziere Visualisierungsartefakte."
        ),
        backstory=(
            "Du verantwortest die finale Abgabe. Nur konsistente Struktur und "
            "nachvollziehbare Zahlen gelten als erledigt."
        ),
        tools=[json_formatter_tool, visualization_tool, text_summarizer_tool],
        llm=agent_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=12,
    )

    return (
        input_architect,
        market_data_adapter,
        news_analyst,
        fundamental_analyst,
        portfolio_optimizer,
        risk_manager,
        didactic_coach,
        final_reporter,
    )


def create_tasks(challenge_input: StockChallengeInput, agents: tuple) -> list:
    (
        input_architect,
        market_data_adapter,
        news_analyst,
        fundamental_analyst,
        portfolio_optimizer,
        risk_manager,
        didactic_coach,
        final_reporter,
    ) = agents

    input_json = challenge_input.model_dump_json(indent=2)
    ticker_list = ",".join([c.ticker for c in challenge_input.company_universe])

    task_input_design = Task(
        description=f"""
        Analysiere und normalisiere den Input:
        {input_json}

        Liefere:
        1) Harte Constraints (max 10 Bullet Points)
        2) Kennzahlen-Tabelle aller Unternehmen
        3) No-Go Regeln fuer die Portfolio-Optimierung
        """,
        expected_output="Constraint-Liste, Kennzahlen-Tabelle, No-Go-Regeln.",
        agent=input_architect,
    )

    task_market_data = Task(
        description=f"""
        Erstelle ein Live-Marktsnapshot fuer diese Ticker:
        {ticker_list}

        Nutze primar das Tool 'Live Aktien Daten'.
        Ausgabe:
        - Ticker
        - Last Price
        - Day Change (%)
        - Source
        - Missing/Errors separat auflisten
        """,
        expected_output="Marktsnapshot-Tabelle plus Datenluecken.",
        agent=market_data_adapter,
        context=[task_input_design],
    )

    task_news = Task(
        description=f"""
        Erstelle ein News-Briefing fuer dieses Szenario:
        - scenario_prompt: {challenge_input.scenario_prompt}
        - investor_wishes: {json.dumps(challenge_input.investor_wishes, ensure_ascii=False)}
        - Ticker: {ticker_list}

        Nutze 'Aktuelle News suchen' fuer:
        1) Die wichtigsten Ticker
        2) Das Szenario als Freitext
        3) Mindestens ein makrooekonomisches Thema

        Ausgabe:
        - mindestens 5 News-Hinweise
        - pro Hinweis: titel, link, quelle, kurze Relevanz fuer das Portfolio
        """,
        expected_output="News-Briefing mit mindestens 5 relevanten Hinweisen.",
        agent=news_analyst,
        context=[task_input_design, task_market_data],
    )

    task_fundamental = Task(
        description="""
        Erstelle ein fundamentales Ranking:
        - Mindestens 3 starke und 2 schwache Kandidaten markieren
        - Begruendung mit PE, Wachstum, Verschuldung, Volatilitaet, Dividende, ESG
        - Noch keine finale Gewichtung
        """,
        expected_output="Fundamentales Ranking mit Starken, Schwachen und Gruenden.",
        agent=fundamental_analyst,
        context=[task_input_design, task_market_data, task_news],
    )

    task_allocation = Task(
        description="""
        Erzeuge die finale Allokation:
        - Mindestens 3 Aktien
        - Jede Position <= max_single_position_pct
        - Mindestens geforderte Cash-Reserve
        - invested_eur <= capital_eur
        - weighted_avg_pe und weighted_avg_volatility_pct berechnen
        """,
        expected_output="Allokationsplan mit Positionsgewichten und Kennzahlen.",
        agent=portfolio_optimizer,
        context=[task_input_design, task_market_data, task_news, task_fundamental],
    )

    task_risk = Task(
        description="""
        Erzeuge:
        1) Szenarioanalyse (bull/base/bear)
        2) Risiko-Register mit mindestens 4 Risiken
           (probability, impact, mitigation, owner)
        """,
        expected_output="Szenarioanalyse und Risiko-Register.",
        agent=risk_manager,
        context=[task_allocation, task_market_data, task_news],
    )

    task_didactic = Task(
        description="""
        Erzeuge:
        - didactic_explanation (6-10 Saetze)
        - decision_pitch (max 120 Woerter)
        Fokus: Abi-Niveau, klare Begriffe, kein Fachjargon ohne Erklaerung.
        """,
        expected_output="Didaktische Erklaerung plus kurzer Pitch.",
        agent=didactic_coach,
        context=[task_fundamental, task_allocation, task_risk, task_news],
    )

    task_final_report = Task(
        description=f"""
        Erzeuge den finalen Bericht als valides JSON gemaess StockMissionReport.
        challenge_name = "{challenge_input.challenge_name}"
        team_name = "{challenge_input.team_name}"
        scenario_prompt = "{challenge_input.scenario_prompt}"
        investor_wishes = {json.dumps(challenge_input.investor_wishes, ensure_ascii=False)}

        Zwingend:
        - market_snapshot enthalten
        - market_news mit >=3 relevanten Eintraegen
        - wishes_coverage mit >=2 konkreten Abdeckungen der investor_wishes
        - mindestens 3 selected_stocks
        - allocation_plan vollstaendig
        - scenario_analysis mit bull/base/bear
        - risk_register mit >=4 Eintraegen
        - quality_checks mit >=6 Checks
        - why_not_single_agent mit >=6 Gruenden
        - final_recommendation mit klarer Entscheidung
        - visualization_paths mit Chart-Pfad, falls erstellt

        Ausgabe nur JSON.
        """,
        expected_output="Vollstaendiger StockMissionReport als JSON.",
        agent=final_reporter,
        context=[
            task_input_design,
            task_market_data,
            task_news,
            task_fundamental,
            task_allocation,
            task_risk,
            task_didactic,
        ],
        output_pydantic=StockMissionReport,
    )

    return [
        task_input_design,
        task_market_data,
        task_news,
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


def _extract_min_cash_reserve_pct(challenge_input: StockChallengeInput) -> float:
    fallback = {"defensiv": 20.0, "ausgewogen": 15.0, "offensiv": 10.0}[challenge_input.risk_profile]
    for constraint in challenge_input.hard_constraints:
        lower = constraint.lower()
        if "cash" not in lower and "reserve" not in lower:
            continue
        match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:%|prozent)", lower)
        if match:
            return float(match.group(1).replace(",", "."))
    return fallback


def _extract_min_positions(challenge_input: StockChallengeInput) -> int:
    minimum = 3
    for constraint in challenge_input.hard_constraints:
        lower = constraint.lower()
        if "aktien" not in lower:
            continue
        match = re.search(r"mindestens\s+(\d+)", lower)
        if match:
            minimum = max(minimum, int(match.group(1)))
    return minimum


def _extract_max_debt_to_equity(challenge_input: StockChallengeInput) -> float:
    max_debt = 10.0
    for constraint in challenge_input.hard_constraints:
        lower = constraint.lower()
        if "debt_to_equity" not in lower:
            continue
        match = re.search(r"(\d+(?:[.,]\d+)?)", lower)
        if match:
            max_debt = min(max_debt, float(match.group(1).replace(",", ".")))
    return max_debt


def _symbol_candidates(ticker: str) -> List[str]:
    base = ticker.upper().strip()
    symbols = [base]
    if "." not in base:
        symbols.extend([f"{base}.US", f"{base}.DE", f"{base}.SW", f"{base}.IT"])
    dedup = []
    for symbol in symbols:
        if symbol not in dedup:
            dedup.append(symbol)
    return dedup


def _fetch_quote_from_stooq(symbol: str) -> Optional[dict]:
    try:
        import requests
    except ImportError:
        return None

    url = f"https://stooq.com/q/l/?s={symbol.lower()}&f=sd2t2ohlcvn&e=csv"
    response = requests.get(url, timeout=8)
    response.raise_for_status()
    reader = csv.DictReader(response.text.splitlines())
    row = next(reader, None)
    if not row:
        return None

    close_str = str(row.get("Close", "")).strip()
    open_str = str(row.get("Open", "")).strip()
    if close_str in {"", "N/D"}:
        return None

    close_value = float(close_str)
    change_pct = 0.0
    if open_str not in {"", "N/D"}:
        open_value = float(open_str)
        if open_value > 0:
            change_pct = ((close_value / open_value) - 1.0) * 100.0

    return {
        "symbol_used": symbol,
        "last_price_eur": close_value,
        "change_pct_1d": round(change_pct, 2),
        "source": "stooq",
    }


def _fetch_live_market_snapshot(challenge_input: StockChallengeInput) -> List[dict]:
    now_iso = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    snapshot: List[dict] = []

    for company in challenge_input.company_universe:
        live_row = None
        for symbol in _symbol_candidates(company.ticker):
            try:
                live_row = _fetch_quote_from_stooq(symbol)
            except Exception:
                continue
            if live_row is not None:
                break

        if live_row is None:
            snapshot.append(
                {
                    "ticker": company.ticker,
                    "name": company.name,
                    "last_price_eur": company.price_eur,
                    "change_pct_1d": 0.0,
                    "source": "static_input_fallback",
                    "as_of_utc": now_iso,
                }
            )
        else:
            snapshot.append(
                {
                    "ticker": company.ticker,
                    "name": company.name,
                    "last_price_eur": live_row["last_price_eur"],
                    "change_pct_1d": live_row["change_pct_1d"],
                    "source": f"{live_row['source']}:{live_row['symbol_used']}",
                    "as_of_utc": now_iso,
                }
            )
    return snapshot


def _company_score(company: CompanyOption, live_change_pct: float) -> float:
    return (
        company.eps_growth_pct * 1.2
        + company.dividend_yield_pct * 1.3
        + company.esg_score * 0.12
        - company.volatility_1y_pct * 0.75
        - company.debt_to_equity * 7.0
        - company.pe_ratio * 0.18
        + live_change_pct * 0.6
    )


def _generate_portfolio_chart(challenge_name: str, selected_stocks: List[dict]) -> Optional[str]:
    if not selected_stocks:
        return None
    labels = [row["ticker"] for row in selected_stocks]
    weights = [row["weight_pct"] for row in selected_stocks]
    output_dir = os.path.join(os.path.dirname(__file__), "outputs")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "challenge5_portfolio.png")

    try:
        os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "matplotlib-cache"))
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None

    try:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4))
        axes[0].bar(labels, weights, color="#2E86AB")
        axes[0].set_title("Portfolio Weights")
        axes[0].set_ylabel("Weight (%)")
        axes[0].grid(axis="y", linestyle="--", alpha=0.3)

        axes[1].pie(weights, labels=labels, autopct="%1.1f%%", startangle=100)
        axes[1].set_title("Allocation Share")

        fig.suptitle(challenge_name)
        fig.tight_layout()
        fig.savefig(output_path, dpi=160)
        plt.close(fig)
        return output_path
    except Exception:
        return None


def _build_default_report(challenge_input: StockChallengeInput, market_snapshot: List[dict]) -> dict:
    min_cash_pct = _extract_min_cash_reserve_pct(challenge_input)
    max_position = float(challenge_input.max_single_position_pct)
    target_invest_pct = max(0.0, 100.0 - min_cash_pct)
    min_positions = _extract_min_positions(challenge_input)
    min_positions_by_cap = max(1, int(math.ceil(target_invest_pct / max_position)))
    needed_positions = max(3, min_positions, min_positions_by_cap)

    snapshot_map = {row["ticker"]: row for row in market_snapshot}
    max_debt = _extract_max_debt_to_equity(challenge_input)
    filtered = [c for c in challenge_input.company_universe if c.debt_to_equity <= max_debt]
    candidates = filtered if len(filtered) >= 3 else challenge_input.company_universe

    ranked = sorted(
        candidates,
        key=lambda c: _company_score(c, snapshot_map.get(c.ticker, {}).get("change_pct_1d", 0.0)),
        reverse=True,
    )
    picked = ranked[: min(len(ranked), needed_positions)]
    if len(picked) < 3:
        picked = ranked[:3]

    selected_count = max(1, len(picked))
    target_bp = int(round(target_invest_pct * 100))
    base_bp = target_bp // selected_count
    weight_bp = [base_bp for _ in range(selected_count)]
    for idx in range(target_bp - base_bp * selected_count):
        weight_bp[idx] += 1
    weight_pct = [bp / 100.0 for bp in weight_bp]

    capital = challenge_input.capital_eur
    investments = [round(capital * (w / 100.0), 2) for w in weight_pct]
    intended_total = round(capital * (sum(weight_pct) / 100.0), 2)
    if investments:
        diff = round(intended_total - sum(investments), 2)
        investments[-1] = round(investments[-1] + diff, 2)

    selected_stocks = []
    company_map = {c.ticker: c for c in challenge_input.company_universe}
    for idx, company in enumerate(picked):
        live_delta = snapshot_map.get(company.ticker, {}).get("change_pct_1d", 0.0)
        selected_stocks.append(
            {
                "ticker": company.ticker,
                "name": company.name,
                "weight_pct": round(weight_pct[idx], 2),
                "investment_eur": investments[idx],
                "investment_thesis": (
                    "Ausgewaehlt wegen Kombination aus Wachstum, Bilanzqualitaet, "
                    "Risikoprofil und aktueller Marktbewegung."
                ),
                "key_metric_note": (
                    f"KGV {company.pe_ratio}, EPS-Wachstum {company.eps_growth_pct}%, "
                    f"Volatilitaet {company.volatility_1y_pct}%, Day-Change {live_delta}%."
                ),
            }
        )

    invested_eur = round(sum(item["investment_eur"] for item in selected_stocks), 2)
    cash_reserve_eur = round(capital - invested_eur, 2)
    cash_reserve_pct = round((cash_reserve_eur / capital) * 100.0, 2) if capital else 0.0

    total_weight = sum(item["weight_pct"] for item in selected_stocks) or 1.0
    weighted_avg_pe = round(
        sum((item["weight_pct"] / total_weight) * company_map[item["ticker"]].pe_ratio for item in selected_stocks),
        2,
    )
    weighted_avg_volatility = round(
        sum(
            (item["weight_pct"] / total_weight) * company_map[item["ticker"]].volatility_1y_pct
            for item in selected_stocks
        ),
        2,
    )

    excluded_tickers = [c.ticker for c in challenge_input.company_universe if c.ticker not in {p.ticker for p in picked}]

    scenario_map = {
        "defensiv": (7.0, 4.0, -8.0),
        "ausgewogen": (13.0, 7.0, -14.0),
        "offensiv": (22.0, 10.0, -24.0),
    }
    bull, base, bear = scenario_map[challenge_input.risk_profile]
    scenario_analysis = [
        {
            "scenario": "bull",
            "expected_portfolio_return_pct": bull,
            "assumption": "Disinflation, stabile Zinsen, Gewinnrevisionen nach oben.",
        },
        {
            "scenario": "base",
            "expected_portfolio_return_pct": base,
            "assumption": "Moderates Wachstum, keine grossen exogenen Schocks.",
        },
        {
            "scenario": "bear",
            "expected_portfolio_return_pct": bear,
            "assumption": "Wachstumseinbruch, Multiple-Kompression, Risk-off Rotation.",
        },
    ]

    risk_register = [
        {
            "risk": "Klumpenrisiko in zyklischen Titeln",
            "probability": "mittel",
            "impact": "hoch",
            "mitigation": "Gewicht pro Position limitieren und Cash-Reserve beibehalten.",
            "owner": "Portfolio-Optimierer",
        },
        {
            "risk": "Bewertungsrisiko bei hohen Multiples",
            "probability": "mittel",
            "impact": "mittel",
            "mitigation": "Bewertung regelmaessig gegen Gewinnwachstum spiegeln.",
            "owner": "Fundamentalanalyst",
        },
        {
            "risk": "Makro-Risiko durch Zins- und Waehrungsschocks",
            "probability": "niedrig",
            "impact": "hoch",
            "mitigation": "Szenario-Update monatlich und Rebalancing-Regeln definieren.",
            "owner": "Risiko- und Szenario-Manager",
        },
        {
            "risk": "Datenluecken bei Live-Quotes",
            "probability": "mittel",
            "impact": "mittel",
            "mitigation": "Fallback auf Input-Preise und Kennzeichnung der Datenquelle.",
            "owner": "Live-Datenadapter",
        },
    ]

    chart_path = _generate_portfolio_chart(challenge_input.challenge_name, selected_stocks)
    visualization_paths = [chart_path] if chart_path else []

    picked_symbols = ", ".join([item["ticker"] for item in selected_stocks])
    quality_checks = [
        "StockMissionReport hat alle Pflichtfelder.",
        "Mindestens 3 Aktien wurden allokiert.",
        "Keine Position liegt ueber max_single_position_pct.",
        "Invested + Cash entspricht capital_eur (Rundungstoleranz 0.01).",
        "Szenarioanalyse enthaelt bull/base/bear.",
        "Risiko-Register enthaelt mindestens 4 vollstaendige Eintraege.",
        "Market-Snapshot enthaelt fuer alle Ticker mindestens einen Datenpunkt (live oder fallback).",
    ]
    why_not_single_agent = [
        "Input-Architektur und Constraint-Parsing sind ein eigener Arbeitsschritt.",
        "Live-Datenabruf verlangt getrennte Adapterlogik und Fehlerbehandlung.",
        "Fundamentale Bewertung braucht dedizierte Kennzahlenanalyse.",
        "Portfolio-Optimierung ist ein eigenes numerisches Nebenbedingungen-Problem.",
        "Risikomanagement erfordert separate Szenario- und Mitigationssicht.",
        "Didaktische Aufbereitung unterscheidet sich von quantitativer Analyse.",
        "Finales Reporting muss alle Artefakte konsistent zusammenfuehren.",
    ]

    return {
        "challenge_name": challenge_input.challenge_name,
        "team_name": challenge_input.team_name,
        "market_snapshot": market_snapshot,
        "selected_stocks": selected_stocks,
        "excluded_tickers": excluded_tickers,
        "allocation_plan": {
            "capital_eur": capital,
            "invested_eur": invested_eur,
            "cash_reserve_eur": cash_reserve_eur,
            "cash_reserve_pct": cash_reserve_pct,
            "weighted_avg_pe": weighted_avg_pe,
            "weighted_avg_volatility_pct": weighted_avg_volatility,
        },
        "scenario_analysis": scenario_analysis,
        "risk_register": risk_register,
        "didactic_explanation": (
            "Das Portfolio kombiniert Wachstums- und Stabilitaetswerte aus mehreren "
            "Sektoren. Fuer das Abi-Niveau gilt: Kennzahlen immer im Zusammenspiel "
            "lesen (Bewertung, Wachstum, Risiko, Diversifikation) statt isoliert."
        ),
        "decision_pitch": (
            f"Unser Vorschlag allokiert {picked_symbols} mit klaren Positionslimits "
            "und Cash-Reserve. So ist das Portfolio nicht nur chancenorientiert, "
            "sondern auch bei schwachen Marktphasen kontrollierbar."
        ),
        "visualization_paths": visualization_paths,
        "quality_checks": quality_checks,
        "why_not_single_agent": why_not_single_agent,
        "final_recommendation": (
            "Portfolio in dieser Struktur umsetzen, monatlich ueberpruefen und bei "
            "deutlichen Regimewechseln rebalancen. Prioritaet hat nachvollziehbare "
            "Entscheidungslogik statt kurzfristige Spekulation."
        ),
    }


def _find_json_dicts(text: str) -> List[dict]:
    if not text:
        return []
    matches: List[dict] = []
    start = None
    depth = 0
    in_string = False
    escaped = False

    for idx, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue

        if char == "{":
            if depth == 0:
                start = idx
            depth += 1
            continue

        if char == "}":
            if depth == 0:
                continue
            depth -= 1
            if depth == 0 and start is not None:
                chunk = text[start : idx + 1]
                try:
                    parsed = json.loads(chunk)
                    if isinstance(parsed, dict):
                        matches.append(parsed)
                except Exception:
                    pass
                start = None
    return matches


def _extract_candidate_dict(raw_result: object) -> dict:
    candidates: List[dict] = []
    if isinstance(raw_result, dict):
        candidates.append(raw_result)

    json_dict = getattr(raw_result, "json_dict", None)
    if isinstance(json_dict, dict):
        candidates.append(json_dict)

    raw_text = ""
    if isinstance(raw_result, str):
        raw_text = raw_result
    else:
        raw_attr = getattr(raw_result, "raw", None)
        if isinstance(raw_attr, str):
            raw_text = raw_attr
        else:
            raw_text = str(raw_result)
    candidates.extend(_find_json_dicts(raw_text))

    if not candidates:
        return {}
    return max(candidates, key=lambda d: len(d.keys()))


def _deep_merge_defaults(default_data: dict, candidate_data: dict) -> dict:
    merged = dict(default_data)
    for key, value in candidate_data.items():
        if key not in merged:
            continue
        if value in (None, "", [], {}):
            continue
        if isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge_defaults(merged[key], value)
        else:
            merged[key] = value
    return merged


def _repair_report(raw_result: object, challenge_input: StockChallengeInput, market_snapshot: List[dict]) -> StockMissionReport:
    defaults = _build_default_report(challenge_input, market_snapshot)
    candidate = _extract_candidate_dict(raw_result)
    merged = _deep_merge_defaults(defaults, candidate)

    try:
        return StockMissionReport.model_validate(merged)
    except ValidationError:
        return StockMissionReport.model_validate(defaults)


challenges = [
    {
        "id": 1,
        "challenge_name": "Abi Trading Lab: KI-Boom vs. Rezessionsangst",
        "team_name": "Leistungskurs Wirtschaft Q2",
        "grade_level": "Q2",
        "scenario_prompt": (
            "Die Klasse erwartet volatile Maerkte: KI-Boom in Tech, aber Risiko "
            "einer Konjunkturabkuehlung in Europa. Erstelle ein robustes, "
            "verstaendliches Portfolio fuer ein Schulprojekt."
        ),
        "investor_wishes": [
            "Nicht zu spekulativ, aber mit Chance auf ueberdurchschnittliche Rendite",
            "ESG soll sichtbar beruecksichtigt werden",
            "Mindestens ein defensiver Sektor zur Stabilisierung",
        ],
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
        "output_language": "de",
    }
]

CHALLENGE_INPUT = challenges[0]


def run_challenge(challenge_input: dict, model_override: Optional[str] = None, verbose: bool = True) -> object:
    validated_input = _validate_input(challenge_input)
    agents = create_agents(model_override)
    tasks = create_tasks(validated_input, agents)

    crew = Crew(
        agents=list(agents),
        tasks=tasks,
        process=Process.sequential,
        verbose=verbose,
    )
    return crew.kickoff()


def run_model_comparison(challenge_input: dict, model_list: List[str]) -> List[dict]:
    """
    Fuehrt die gleiche Challenge mit mehreren Modellen aus und liefert
    Vergleichsdaten ohne Fallback-Reparatur.
    """
    comparison: List[dict] = []
    for model_name in model_list:
        started = time.perf_counter()
        entry = {
            "model": model_name,
            "success": False,
            "duration_sec": 0.0,
            "has_pydantic": False,
            "selected_stocks_count": 0,
            "error": None,
        }
        try:
            result = run_challenge(challenge_input, model_override=model_name, verbose=False)
            report = getattr(result, "pydantic", None)
            entry["success"] = True
            entry["has_pydantic"] = report is not None
            if report is not None:
                entry["selected_stocks_count"] = len(report.selected_stocks)
        except Exception as exc:
            entry["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            entry["duration_sec"] = round(time.perf_counter() - started, 3)
        comparison.append(entry)
    return comparison


if __name__ == "__main__":
    result = run_challenge(CHALLENGE_INPUT, verbose=True)
    if getattr(result, "pydantic", None):
        final_json = json.dumps(result.pydantic.model_dump(), indent=2, ensure_ascii=False)
        print(final_json)

        out_dir = os.path.join(os.path.dirname(__file__), "outputs")
        os.makedirs(out_dir, exist_ok=True)

        report_file = os.path.join(out_dir, "challenge5_last_report.json")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(final_json + "\n")

        raw_file = os.path.join(out_dir, "challenge5_last_raw.txt")
        with open(raw_file, "w", encoding="utf-8") as f:
            f.write(str(result) + "\n")

        print(f"\nGespeichert: {report_file}")
        print(f"Raw Output: {raw_file}")
    else:
        print(result)
