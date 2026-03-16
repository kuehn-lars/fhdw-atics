# ==========================================================
# Imports
# ==========================================================

import os
import sys

# Root-Verzeichnis für absolute Importe (workshops.*) hinzufügen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

import requests
import json
import re
import concurrent.futures
from datetime import datetime
from typing import List, Literal, Optional, Any, Dict, Union
from pydantic import BaseModel, Field, conint, confloat
from dotenv import load_dotenv
from pathlib import Path
from textwrap import shorten

from workshops.crewai_intro.AC1_VordefinierteTools import (
    BulkFinancialTool, 
    InstitutionalNewsScanner, 
    KellyCriterionTool, 
    StrictMathValidator
    )

from config.settings import settings
from src.llm_backend.crew_factory import get_crew_llm

load_dotenv()
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from crewai import Agent, Crew, Task, LLM, Process
from crewai.tools import BaseTool


# ==========================================================
# Helper Functions & Classes
# ==========================================================

class AuditManager:
    """Verwaltet Audit-Dateien, Pfade und Callbacks."""
    def __init__(self, topic, base_dir):
        self.output_dir = os.path.join(base_dir, "outputs")
        os.makedirs(self.output_dir, exist_ok=True)
        self.audit_file = os.path.join(self.output_dir, "ultimate_ib_audit_v33.md")
        self.report_file = os.path.join(self.output_dir, "ultimate_ib_investment_report_v33.md")
        self._init_audit_file(topic)

    def _init_audit_file(self, topic):
        with open(self.audit_file, "w", encoding="utf-8") as f:
            f.write("# 🏛️ LIVE IB SWARM AUDIT (V33)\n\n")
            f.write(f"**Thema:** {topic}\n")
            f.write("**Status:** ⏳ In Arbeit (Live Updates...)\n")
            f.write(f"**Start:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")

    def stream_callback(self, task_output):
        try:
            agent_name = getattr(task_output, "agent", "Unknown Agent")
            description = getattr(task_output, "description", "No description available")
            raw_output = getattr(task_output, "raw", str(task_output))
            with open(self.audit_file, "a", encoding="utf-8") as f:
                f.write(f"## ✅ AGENT COMPLETE: {agent_name}\n")
                f.write(f"**Task Description:** {description}\n\n")
                f.write("### 📄 RAW OUTPUT:\n")
                f.write(f"{raw_output}\n\n")
                f.write("---\n\n")
            print(f"📡 [Live Update] Ergebnisse von {agent_name} gestreamt nach {self.audit_file}")
        except Exception as e:
            print(f"⚠️ Callback Fehler: {e}")

def _safe_md(text: Optional[str]) -> str:
    if text is None:
        return "N/A"
    # Entferne Zeilenumbrüche und Tabs, eskaliere Pipes
    cleaned = str(text).replace("\r", "").replace("\n", " ").replace("\t", " ")
    return cleaned.strip().replace("|", "\\|")

def _render_md_table(headers: List[str], rows: List[List[Any]], alignments: Optional[List[str]] = None) -> List[str]:
    """
    Erstellt eine robuste Markdown-Tabelle mit Padding für vertikale Ausrichtung.
    alignments: Liste von 'L', 'C', 'R' für Left, Center, Right. Standard: 'L'
    """
    if not headers:
        return []
    
    num_cols = len(headers)
    if alignments is None:
        alignments = ['L'] * num_cols
    
    # Vorbereitung der Daten (Strings & Alignment-Safe)
    processed_rows = []
    for row in rows:
        padded_row = list(row) + [""] * (num_cols - len(row))
        processed_rows.append([_safe_md(str(c)) for c in padded_row[:num_cols]])
    
    header_processed = [_safe_md(h) for h in headers]
    
    # Berechne maximale Breite pro Spalte
    col_widths = []
    for i in range(num_cols):
        widths = [len(header_processed[i])] + [len(r[i]) for r in processed_rows]
        col_widths.append(max(widths))
    
    lines = []
    
    # Helper for Padding
    def pad(text, width, align):
        if align == 'R':
            return text.rjust(width)
        elif align == 'C':
            return text.center(width)
        else:
            return text.ljust(width)

    # Header
    header_line = "| " + " | ".join([pad(header_processed[i], col_widths[i], 'L') for i in range(num_cols)]) + " |"
    lines.append(header_line)
    
    # Separator
    sep_cols = []
    for i, align in enumerate(alignments):
        w = col_widths[i]
        if align == 'R':
            sep_cols.append("-" * (w - 1) + ":")
        elif align == 'C':
            sep_cols.append(":" + "-" * (w - 2) + ":")
        else:
            sep_cols.append("-" * w)
    sep_line = "| " + " | ".join(sep_cols) + " |"
    lines.append(sep_line)
    
    # Rows
    for row in processed_rows:
        content_line = "| " + " | ".join([pad(row[i], col_widths[i], alignments[i]) for i in range(num_cols)]) + " |"
        lines.append(content_line)
        
    return lines

def _fmt_pct(x: Optional[float]) -> str:
    if x is None:
        return "N/A"
    return f"{x:.2f}%"

def _fmt_ratio(x: Optional[float]) -> str:
    if x is None:
        return "N/A"
    return f"{x:.2f}"

def _fmt_weight(x: Optional[float]) -> str:
    if x is None:
        return "N/A"
    return f"{x*100:.2f}%" if x <= 1 else f"{x:.2f}%"

def _get_task_pydantic(task_obj):
    """
    Holt robust das pydantic-Ergebnis eines CrewAI-Task-Outputs.
    """
    if task_obj is None:
        return None
    if hasattr(task_obj, "pydantic") and task_obj.pydantic is not None:
        return task_obj.pydantic
    if hasattr(task_obj, "output") and hasattr(task_obj.output, "pydantic"):
        return task_obj.output.pydantic
    return None

def _extract_results_from_crew_result(result):
    """
    Versucht, die einzelnen Task-Outputs aus dem Crew-Resultat zu extrahieren.
    Je nach CrewAI-Version kann das leicht variieren.
    """
    task_outputs = []

    if hasattr(result, "tasks_output") and result.tasks_output:
        task_outputs = result.tasks_output
    elif hasattr(result, "task_outputs") and result.task_outputs:
        task_outputs = result.task_outputs
    elif isinstance(result, list):
        task_outputs = result

    return task_outputs

def render_investment_report(discovery, quant, macro, research, bear, portfolio, output_file, suche_thema, kapital_eur, risiko_profil, anlage_horizont):
    quant_map = {q.symbol: q for q in quant.audit_results}
    research_map = {r.symbol: r for r in research.individual_reports}
    bear_map = {b.symbol: b for b in bear.bear_cases}

    lines = []
    lines.append("# 🏛️ Investment Committee Report")
    lines.append("")
    lines.append(f"**Thema:** {suche_thema}")
    lines.append(f"**Kapital:** {kapital_eur:,.2f} EUR")
    lines.append(f"**Risikoprofil:** {risiko_profil}")
    lines.append(f"**Anlagehorizont:** {anlage_horizont}")
    lines.append(f"**Erstellt am:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"**Mandat:** {_safe_md(discovery.mandate)}")
    lines.append("")
    lines.append(f"**Top Pick:** `{_safe_md(discovery.top_pick_ticker)}`")
    lines.append("")
    lines.append(_safe_md(discovery.top_pick_summary))
    lines.append("")
    lines.append(f"**Overall Observations:** {_safe_md(discovery.overall_observations)}")
    lines.append("")
    lines.append(f"**Portfolio Allocation View:** {_safe_md(portfolio.allocation_rationale)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Discovery Overview")
    lines.append("")
    lines.append(f"**Theme Definition:** {_safe_md(discovery.universe_definition.definition)}")
    lines.append("")
    lines.append("**Value Chain Segments:**")
    for seg in discovery.universe_definition.value_chain_segments:
        lines.append(f"- {seg}")
    lines.append("")
    lines.append("**Screening Logic:**")
    lines.append(_safe_md(discovery.universe_definition.screening_logic))
    lines.append("")
    lines.append("**Search Queries:**")
    for q in discovery.search_audit.primary_queries:
        lines.append(f"- {q}")
    if discovery.search_audit.expanded_queries:
        lines.append("")
        lines.append("**Expanded Queries:**")
        for q in discovery.search_audit.expanded_queries:
            lines.append(f"- {q}")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Sector & Macro View")
    lines.append("")
    lines.append(_safe_md(macro.macro_synthesis))
    lines.append("")

    for section_name, values in [
        ("Demand / Adoption Observations", getattr(macro, "demand_observations", [])),
        ("Regulatory Observations", getattr(macro, "regulatory_observations", [])),
        ("Geopolitical Observations", getattr(macro, "geopolitical_observations", [])),
        ("Market Structure Observations", getattr(macro, "market_structure_observations", [])),
        ("Capital Allocation Observations", getattr(macro, "capital_allocation_observations", [])),
        ("Key Macro Risks", getattr(macro, "key_macro_risks", [])),
        ("Macro Implications for Shortlist", getattr(macro, "macro_implications_for_shortlist", [])),
    ]:
        if values:
            lines.append(f"**{section_name}:**")
            for x in values:
                lines.append(f"- {x}")
            lines.append("")

    lines.append("---")
    lines.append("")

    lines.append("## Shortlisted Equities")
    lines.append("")
    
    shortlist_headers = ["Symbol", "Company", "Exposure", "Moat", "Disc. Conviction", "Quant Conviction", "Investability"]
    shortlist_rows = []
    for asset in discovery.shortlisted_assets:
        q = quant_map.get(asset.ticker)
        moat = asset.moat.moat_type if getattr(asset, "moat", None) else "N/A"
        quant_conv = getattr(q, "quant_conviction_score", "N/A") if q else "N/A"
        investability = getattr(q, "investability_score", "N/A") if q else "N/A"
        shortlist_rows.append([
            f"`{asset.ticker}`",
            asset.company_name,
            asset.exposure_type,
            moat,
            asset.conviction_score,
            quant_conv,
            investability
        ])
    
    lines.extend(_render_md_table(shortlist_headers, shortlist_rows, alignments=['L', 'L', 'L', 'L', 'R', 'R', 'R']))
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Equity Deep Dives")
    lines.append("")
    for asset in discovery.shortlisted_assets:
        symbol = asset.ticker
        q = quant_map.get(symbol)
        r = research_map.get(symbol)
        b = bear_map.get(symbol)

        lines.append(f"### {asset.company_name} (`{symbol}`)")
        lines.append("")
        lines.append(f"**Role in Ecosystem:** {_safe_md(asset.ecosystem_role)}")
        lines.append("")
        lines.append(f"**Exposure Type:** `{asset.exposure_type}`")
        lines.append("")
        lines.append(f"**Why Now:** {_safe_md(asset.why_now)}")
        lines.append("")
        lines.append(f"**Economic Linkage:** {_safe_md(asset.economic_linkage)}")
        lines.append("")
        lines.append(f"**Moat:** `{asset.moat.moat_type}` / `{asset.moat.moat_strength}`")
        lines.append("")
        lines.append(_safe_md(asset.moat.rationale))
        lines.append("")
        lines.append(f"**Discovery Thesis:** {_safe_md(asset.short_investment_case)}")
        lines.append("")
        lines.append(f"**Discovery Conviction:** {asset.conviction_score}/10")
        lines.append("")

        if q:
            fm = q.financial_metrics
            lines.append("**Quant Snapshot:**")
            lines.append("")
            
            quant_headers = ["Metric", "Value"]
            quant_rows = [
                ["P/E", _fmt_ratio(fm.pe)],
                ["P/S", _fmt_ratio(fm.ps)],
                ["EV/EBITDA", _fmt_ratio(fm.ev_ebitda)],
                ["Beta", _fmt_ratio(fm.beta)],
                ["Yield", _fmt_pct(fm.yield_pct)],
                ["ROE", _fmt_pct(fm.roe)],
                ["Net Margin", _fmt_pct(fm.net_margin)],
                ["Operating Margin", _fmt_pct(fm.op_margin)],
                ["Debt/Equity", _fmt_ratio(fm.debt_to_equity)],
                ["Current Ratio", _fmt_ratio(fm.current_ratio)],
                ["Revenue Growth", _fmt_pct(fm.rev_growth)],
                ["FCF Growth", _fmt_pct(fm.fcf_growth)]
            ]
            lines.extend(_render_md_table(quant_headers, quant_rows, alignments=['L', 'R']))
            lines.append("")
            lines.append(f"**Quant Validation:** {_safe_md(q.financial_validation.summary)}")
            lines.append("")
            lines.append(f"**Valuation Commentary:** {_safe_md(q.valuation_commentary)}")
            lines.append("")
            lines.append(f"**Quality Commentary:** {_safe_md(q.quality_commentary)}")
            lines.append("")
            lines.append(f"**Risk Commentary:** {_safe_md(q.risk_commentary)}")
            lines.append("")
            lines.append(f"**Quant Scores:** Investability `{q.investability_score}/10`, Quant Conviction `{q.quant_conviction_score}/10`")
            lines.append("")

        if r:
            lines.append(f"**Investment Thesis:** {_safe_md(r.investment_thesis)}")
            lines.append("")
            lines.append(f"**Micro Analysis:** {_safe_md(r.micro_analysis)}")
            lines.append("")
            lines.append(f"**Macro Analysis:** {_safe_md(r.macro_analysis)}")
            lines.append("")
            lines.append(f"**Quant Integration:** {_safe_md(r.quant_integration)}")
            lines.append("")
            lines.append(f"**Consistency Check:** {_safe_md(r.thesis_consistency_check)}")
            lines.append("")
            if r.key_risks:
                lines.append("**Key Risks:**")
                for risk in r.key_risks:
                    lines.append(f"- {risk}")
                lines.append("")
            if r.citations:
                lines.append("**Supporting Citations:**")
                for c in r.citations[:4]:
                    lines.append(
                        f"- **{c.source_name}** ({c.date}) [{c.citation_type}/{c.evidence_strength}]  \n"
                        f"  {_safe_md(c.quote)}  \n"
                        f"  {_safe_md(c.url)}"
                    )
                lines.append("")

        if b:
            lines.append("**Bear Case:**")
            lines.append(f"- Counter Thesis: {_safe_md(b.counter_thesis)}")
            lines.append(f"- Failure Mechanism: {_safe_md(b.failure_mechanism)}")
            lines.append(f"- Primary Risk Type: `{b.primary_risk_type}`")
            lines.append(f"- Downside: {b.downside_pct:.2f}%")
            lines.append(f"- Failure Probability: {b.failure_probability:.2%}")
            lines.append(f"- Trigger Signal: {_safe_md(b.trigger_signal)}")
            lines.append(f"- Bear Conviction: {b.bear_conviction}")
            lines.append("")

        lines.append("---")
        lines.append("")

    if discovery.rejected_assets:
        lines.append("## Rejected / Lower-Priority Candidates")
        lines.append("")
        for rej in discovery.rejected_assets:
            ticker = f" (`{rej.ticker}`)" if rej.ticker else ""
            lines.append(f"### {rej.company_name}{ticker}")
            lines.append(f"- Category: `{rej.rejection_category}`")
            lines.append(f"- Reason: {_safe_md(rej.rejection_reason)}")
            lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## Final Portfolio")
    lines.append("")
    lines.append(f"**Strategy Name:** {_safe_md(portfolio.strategy_name)}")
    lines.append("")
    
    portfolio_headers = ["Symbol", "Weight", "Amount (EUR)", "Kelly Fraction"]
    portfolio_rows = [
        [f"`{p.symbol}`", _fmt_weight(p.weight), f"{p.amount_eur:,.2f}", f"{p.kelly_fraction:.4f}"]
        for p in portfolio.portfolio
    ]
    lines.extend(_render_md_table(portfolio_headers, portfolio_rows, alignments=['L', 'R', 'R', 'R']))
    lines.append("")

    for p in portfolio.portfolio:
        lines.append(f"### Portfolio Rationale – `{p.symbol}`")
        lines.append("")
        lines.append(f"**Final Thesis:** {_safe_md(p.final_thesis)}")
        lines.append("")
        lines.append(f"**Inclusion Rationale:** {_safe_md(p.inclusion_rationale)}")
        lines.append("")
        lines.append(f"**Key Monitoring Point:** {_safe_md(p.key_monitoring_point)}")
        lines.append("")

    if portfolio.excluded_finalists:
        lines.append("**Excluded Finalists:**")
        for x in portfolio.excluded_finalists:
            lines.append(f"- {x}")
        lines.append("")

    lines.append(f"**Allocation Rationale:** {_safe_md(portfolio.allocation_rationale)}")
    lines.append("")
    lines.append(f"**Risk Summary:** {_safe_md(portfolio.risk_summary)}")
    lines.append("")
    lines.append(f"**Math Audit:** {_safe_md(portfolio.math_audit_log)}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Method & Trace Summary")
    lines.append("")
    lines.append(_safe_md(portfolio.full_trace_summary))
    lines.append("")
    if getattr(discovery, "execution_notes", None):
        lines.append("**Execution Notes:**")
        lines.append(_safe_md(discovery.execution_notes))
        lines.append("")

    Path(output_file).write_text("\n".join(lines), encoding="utf-8")


# ==========================================================
# 🛠️ AGNOSTISCHER KONFIGURATIONS-KASTEN
# ==========================================================

BACKEND = "nim"  # "nim" (NVIDIA) oder "local" (Ollama)
MODEL = None      # Falls None, wird settings.nvidia_model / settings.local_model genutzt

SUCHE_THEMA = "Solarenergie EU"
KAPITAL_EUR = 2_000.0
RISIKO_PROFIL = "Low Risk" 
ANLAGE_HORIZONT = "10 Jahre"
MAX_SWARM_SIZE = 2

# Aliases for internal consistency
suche_thema = SUCHE_THEMA
kapital = KAPITAL_EUR
risiko = RISIKO_PROFIL
horizont = ANLAGE_HORIZONT


# ==========================================================
# Pydantic Models
# ==========================================================

class NewsSignal(BaseModel):
    query_used: str = Field(
        ...,
        description="Die konkrete Suchanfrage, mit der das Signal gefunden wurde."
    )
    headline: str = Field(
        ...,
        description="Kurztitel oder prägnante Zusammenfassung des News-Signals."
    )
    signal_type: Literal[
            "contract_award",
            "partnership",
            "product_launch",
            "capacity_expansion",
            "regulatory_tailwind",
            "market_share_gain",
            "demand_acceleration",
            "strategic_positioning",
            "earnings_readthrough",
            "other"
        ] = Field(
            ...,
            description="Typ des identifizierten Signals."
        )
    relevance_explanation: str = Field(
            ...,
            description="Warum dieses Signal für den Equity Case des Unternehmens relevant ist."
        )
    source_snippet: Optional[str] = Field(
            default=None,
            description="Optionaler kurzer Auszug oder paraphrasierte Evidenz aus dem News-Scan.")

class MoatAssessment(BaseModel):
    moat_type: Literal[
        "scale_advantage",
        "cost_advantage",
        "switching_costs",
        "installed_base",
        "regulatory_barrier",
        "proprietary_technology",
        "ip_patent_position",
        "distribution_power",
        "data_advantage",
        "ecosystem_lock_in",
        "supply_chain_control",
        "manufacturing_expertise",
        "brand_trust",
        "mission_critical_integration",
        "none_or_unclear"
    ] = Field(
        ...,
        description="Primärer identifizierter Moat-Typ."
    )
    moat_strength: Literal["weak", "moderate", "strong"] = Field(
        ...,
        description="Subjektive, aber begründete Einschätzung der Moat-Stärke."
    )
    rationale: str = Field(
        ...,
        description="Begründung, warum dieser Moat plausibel ist."
    )
    evidence_linked_to_news: bool = Field(
        ...,
        description="Ob der Moat durch News-Signale zusätzlich gestützt wurde."
    )

class CandidateAssessment(BaseModel):
    company_name: str = Field(
        ...,
        description="Name des Unternehmens."
    )
    ticker: str = Field(
        ...,
        description="Börsenticker des Unternehmens."
    )
    primary_listing_region: Optional[str] = Field(
        default=None,
        description="Hauptbörsenregion oder Markt des Unternehmens."
    )
    ecosystem_role: str = Field(
        ...,
        description="Rolle des Unternehmens im Themen-Ökosystem."
    )
    exposure_type: Literal[
        "pure_play",
        "high_exposure",
        "selective_exposure",
        "indirect_enabler"
    ] = Field(
        ...,
        description="Klassifikation der thematischen Exposure."
    )
    thematic_fit: conint(ge=1, le=10) = Field(
        ...,
        description="Wie stark das Unternehmen operativ und wirtschaftlich mit dem Thema verknüpft ist."
    )
    economic_linkage: str = Field(
        ...,
        description="Wie genau sich das Thema in Umsatz, Margen, Nachfrage, Marktanteil oder strategische Relevanz übersetzt."
    )
    why_now: str = Field(
        ...,
        description="Warum der Titel aktuell relevant ist; idealerweise mit Bezug auf News, Timing oder Marktveränderung."
    )
    news_signals: List[NewsSignal] = Field(
        default_factory=list,
        description="Liste relevanter News-Signale für diesen Kandidaten."
    )
    moat: MoatAssessment = Field(
        ...,
        description="Bewertung des Wettbewerbsvorteils."
    )
    conviction_score: conint(ge=1, le=10) = Field(
        ...,
        description="Gesamt-Conviction des Titels von 1 bis 10."
    )
    conviction_rationale: str = Field(
        ...,
        description="Zusammenfassende Begründung für den Conviction Score."
    )
    key_risks: List[str] = Field(
        default_factory=list,
        description="Wesentliche Risiken für die Investmentthese."
    )
    short_investment_case: str = Field(
        ...,
        description="Kurze, nüchterne institutionelle Investment-These."
    )

class RejectedCandidate(BaseModel):
    company_name: str = Field(
        ...,
        description="Name des verworfenen Unternehmens."
    )
    ticker: Optional[str] = Field(
        default=None,
        description="Ticker, falls vorhanden oder bekannt."
    )
    rejection_reason: str = Field(
        ...,
        description="Konkreter Grund für die Ablehnung."
    )
    rejection_category: Literal[
        "weak_thematic_fit",
        "insufficient_news_support",
        "unclear_economic_linkage",
        "no_plausible_moat",
        "too_indirect",
        "non_investable",
        "inferior_relative_positioning",
        "private_or_acquired",
        "other"
    ] = Field(
        ...,
        description="Standardisierte Ablehnungskategorie."
    )

class UniverseDefinition(BaseModel):
    theme: str = Field(
        ...,
        description="Das ursprünglich gesuchte Investment-Thema."
    )
    definition: str = Field(
        ...,
        description="Präzise Definition des Themenraums."
    )
    value_chain_segments: List[str] = Field(
        default_factory=list,
        description="Relevante Segmente der Wertschöpfungskette."
    )
    included_geographies: List[str] = Field(
        default_factory=list,
        description="Geografien oder Märkte, die im Screening berücksichtigt wurden."
    )
    screening_logic: str = Field(
        ...,
        description="Beschreibung, wie aus dem Themenraum ein investierbares Universum abgeleitet wurde."
    )

class SearchAudit(BaseModel):
    primary_queries: List[str] = Field(
        default_factory=list,
        description="Direkte Suchanfragen zum Thema."
    )
    expanded_queries: List[str] = Field(
        default_factory=list,
        description="Abstrahierte, alternative oder wertschöpfungskettenbasierte Suchanfragen."
    )
    search_notes: Optional[str] = Field(
        default=None,
        description="Bemerkungen zur Suchstrategie."
    )

class DiscoveryContract(BaseModel):
    search_theme: str = Field(
        ...,
        description="Das vom Nutzer vorgegebene Suchthema."
    )
    mandate: str = Field(
        ...,
        description="Kurzbeschreibung des Discovery-Mandats."
    )
    universe_definition: UniverseDefinition = Field(
        ...,
        description="Definition und Eingrenzung des investierbaren Universums."
    )
    search_audit: SearchAudit = Field(
        ...,
        description="Dokumentation der verwendeten Suchlogik."
    )
    shortlisted_assets: List[CandidateAssessment] = Field(
        default_factory=list,
        description="Final priorisierte investierbare Titel."
    )
    rejected_assets: List[RejectedCandidate] = Field(
        default_factory=list,
        description="Geprüfte, aber verworfene Titel mit Ablehnungsgrund."
    )
    top_pick_ticker: Optional[str] = Field(
        default=None,
        description="Ticker des am höchsten priorisierten Titels."
    )
    top_pick_summary: Optional[str] = Field(
        default=None,
        description="Kurzbegründung des höchsten Conviction-Titels."
    )
    overall_observations: str = Field(
        ...,
        description="Makro-/Themenfazit über die Qualität des Opportunity Sets."
    )
    execution_notes: Optional[str] = Field(
        default=None,
        description="Optionale Hinweise zur Datenlage oder Grenzen des Screenings."
    )

class FinancialValidation(BaseModel):
    validated_via_bulk_financial_metrics: bool = Field(
        ...,
        description="True nur dann, wenn der Ticker tatsächlich durch das Financial Tool validiert wurde."
    )
    ticker_used_for_validation: str = Field(
        ...,
        description="Ticker-Symbol, das an das Financial Tool übergeben wurde."
    )
    summary: str = Field(
        ...,
        description="Kurze qualitative Zusammenfassung der Financial Validation."
    )
    profitability_profile: Optional[str] = Field(
        default=None,
        description="Kurze Einordnung von Profitabilität / Margenqualität."
    )
    growth_profile: Optional[str] = Field(
        default=None,
        description="Kurze Einordnung von Umsatz-/Ergebniswachstum."
    )
    balance_sheet_profile: Optional[str] = Field(
        default=None,
        description="Kurze Einordnung der Bilanzstärke."
    )
    investability_profile: Optional[str] = Field(
        default=None,
        description="Kurze Einordnung institutioneller Investierbarkeit."
    )
    red_flags: List[str] = Field(
        default_factory=list,
        description="Wesentliche finanzielle Warnhinweise."
    )

class FinancialMetrics(BaseModel):
    symbol: str
    pe: Optional[float] = Field(None, description="Price to Earnings Ratio")
    ps: Optional[float] = Field(None, description="Price to Sales Ratio")
    ev_ebitda: Optional[float] = Field(None, description="Enterprise Value / EBITDA")
    beta: Optional[float] = Field(None, description="Beta (Volatility)")
    yield_pct: Optional[float] = Field(None, description="Dividend Yield %")
    roe: Optional[float] = Field(None, description="Return on Equity %")
    net_margin: Optional[float] = Field(None, description="Net Profit Margin %")
    op_margin: Optional[float] = Field(None, description="Operating Margin %")
    debt_to_equity: Optional[float] = Field(None, description="Debt / Equity")
    current_ratio: Optional[float] = Field(None, description="Current Ratio")
    rev_growth: Optional[float] = Field(None, description="Revenue Growth %")
    fcf_growth: Optional[float] = Field(None, description="Free Cash Flow Growth %")

class QuantAssessment(BaseModel):
    symbol: str = Field(..., description="Ticker-Symbol")
    financial_metrics: FinancialMetrics = Field(..., description="Rohmetriken aus dem BulkFinancialTool")
    financial_validation: FinancialValidation = Field(
        ...,
        description="Qualitative finanzielle Validierung auf Basis der Rohmetriken."
    )
    valuation_commentary: str = Field(
        ...,
        description="Einordnung von Bewertung und Multiple-Profil."
    )
    quality_commentary: str = Field(
        ...,
        description="Einordnung von Profitabilität, Kapitalrendite und Bilanzqualität."
    )
    risk_commentary: str = Field(
        ...,
        description="Quantitative Risiken wie Volatilität, schwache Margen, Verschuldung oder fehlende Profitabilität."
    )
    investability_score: conint(ge=1, le=10) = Field(
        ...,
        description="Quantitative Einschätzung der institutionellen Investierbarkeit."
    )
    quant_conviction_score: conint(ge=1, le=10) = Field(
        ...,
        description="Gesamteinschätzung des Titels aus quantitativer Sicht."
    )

class QuantAuditContract(BaseModel):
    audit_results: List[QuantAssessment] = Field(
        default_factory=list,
        description="Quantitative Einzelbewertungen für alle Shortlist-Titel aus Task 1."
    )
    portfolio_level_observations: str = Field(
        ...,
        description="Übergreifende Beobachtungen zum Bewertungs-, Qualitäts- und Risikoprofil des Shortlistsets."
    )

class PrioritizedEvent(BaseModel):
    date: str = Field(..., description="Datum des Events.")
    title: str = Field(..., description="Kurztitel des Events.")
    priority: conint(ge=1, le=10) = Field(..., description="Relative Priorität des Events.")
    theme_bucket: Literal[
        "regulation",
        "demand",
        "geopolitics",
        "competition",
        "market_structure",
        "technology",
        "capital_flows",
        "consolidation",
        "supply_chain",
        "other"
    ] = Field(..., description="Makro-/Sektor-Cluster des Events.")
    event_type: Literal[
        "policy_event",
        "company_event",
        "market_report",
        "industry_event",
        "macro_event",
        "other"
    ] = Field(
        ...,
        description="Klassifikation des Ereignistyps."
    )
    impact_analysis: str = Field(
        ...,
        description="Warum dieses Event makroökonomisch oder sektoral relevant ist."
    )
    evidence_strength: Literal["low", "medium", "high"] = Field(
        ...,
        description="Wie belastbar dieses Event als Evidenz einzustufen ist."
    )

class TableFormattedAssetImplication(BaseModel):
    asset: str = Field(..., description="Ticker oder Name des Assets.")
    implication: str = Field(..., description="Details zur Makro-Implikation.")

class MacroNewsContract(BaseModel):
    prioritized_news: List[PrioritizedEvent] = Field(
        default_factory=list,
        description="Wichtigste priorisierte Sektorereignisse."
    )
    macro_synthesis: str = Field(
        ...,
        description="Verdichteter institutioneller Makro- und Sektorbericht."
    )
    demand_observations: List[str] = Field(
        default_factory=list,
        description="Beobachtungen zu Nachfrage, Adoption und kommerzieller Dynamik."
    )
    regulatory_observations: List[str] = Field(
        default_factory=list,
        description="Beobachtungen zu Regulierung, Politik und öffentlichen Treibern."
    )
    geopolitical_observations: List[str] = Field(
        default_factory=list,
        description="Beobachtungen zu geopolitischen Einflüssen."
    )
    market_structure_observations: List[str] = Field(
        default_factory=list,
        description="Beobachtungen zu Wettbewerb, Marktstruktur und Konsolidierung."
    )
    capital_allocation_observations: List[str] = Field(
        default_factory=list,
        description="Beobachtungen zu Investitionen, M&A, Capex und Kapitalströmen."
    )
    key_macro_risks: List[str] = Field(
        default_factory=list,
        description="Makro- und Sektor-Risiken für Investoren."
    )
    macro_implications_for_shortlist: List[Union[str, TableFormattedAssetImplication]] = Field(
        default_factory=list,
        description="Explizite Implikationen des Makrobilds für die Shortlist (Strings oder strukturierte Implikationen)."
    )

class SourceCitation(BaseModel):
    source_name: str = Field(..., description="Name der Quelle.")
    url: str = Field(..., description="URL der Quelle.")
    quote: str = Field(..., description="Kurzer belegbarer Ausschnitt oder Snippet.")
    date: str = Field(..., description="Datum der Quelle.")
    citation_type: Literal[
        "scanner_direct",
        "scanner_derived",
        "context_referenced"
    ] = Field(
        ...,
        description="Wie die Citation entstanden ist."
    )
    evidence_strength: Literal["low", "medium", "high"] = Field(
        ...,
        description="Subjektive Belastbarkeit der Citation."
    )

class CompanyDeepDive(BaseModel):
    symbol: str = Field(..., description="Ticker.")
    investment_thesis: str = Field(
        ...,
        description="Verdichtete institutionelle Investmentthese für den Titel."
    )
    micro_analysis: str = Field(
        ...,
        description="Analyse von Geschäftsmodell, Moat, Wettbewerb und company-specific catalysts."
    )
    macro_analysis: str = Field(
        ...,
        description="Einordnung des Titels in den sektoralen und makroökonomischen Kontext."
    )
    quant_integration: str = Field(
        ...,
        description="Wie die quantitativen Kennzahlen die qualitative These stützen oder einschränken."
    )
    thesis_consistency_check: str = Field(
        ...,
        description="Explizite Prüfung, ob Discovery-These, Macro-Lage und Quant-Profil konsistent zusammenpassen."
    )
    growth_score: float = Field(..., description="Analytischer Wachstumsscore.")
    risk_score: float = Field(..., description="Analytischer Risiko-Score.")
    key_risks: List[str] = Field(
        default_factory=list,
        description="Wesentliche Risiken des Titels."
    )
    citations: List[SourceCitation] = Field(
        ...,
        min_items=2,
        description="Belastbare Citations zur Stützung der These."
    )

class ResearchContract(BaseModel):
    individual_reports: List[CompanyDeepDive] = Field(
        default_factory=list,
        description="Individuelle Research-Deep-Dives pro Ticker."
    )

class BearCase(BaseModel):
    symbol: str = Field(..., description="Ticker des Unternehmens.")
    counter_thesis: str = Field(
        ...,
        description="Verdichtete Gegen-These zur Bull-Story."
    )
    failure_mechanism: str = Field(
        ...,
        description="Konkrete Erklärung, wie und warum die Bull-These scheitern könnte."
    )
    primary_risk_type: Literal[
        "valuation",
        "growth",
        "cyclicality",
        "margin_pressure",
        "competition",
        "regulation",
        "balance_sheet",
        "execution",
        "technology",
        "macro",
        "other"
    ] = Field(
        ...,
        description="Dominanter Risikotyp des Bear-Case."
    )
    downside_pct: float = Field(
        ...,
        description="Geschätztes Downside-Potenzial in Prozent."
    )
    failure_probability: float = Field(
        ...,
        description="Geschätzte Eintrittswahrscheinlichkeit des negativen Szenarios (0-1)."
    )
    trigger_signal: str = Field(
        ...,
        description="Wichtigstes Warnsignal oder Trigger."
    )
    bear_conviction: float = Field(
        ...,
        description="Stärke des Bear-Case."
    )

class ChallengerContract(BaseModel):
    bear_cases: List[BearCase] = Field(
        default_factory=list,
        description="Bear-Cases für alle priorisierten Titel."
    )

class PortfolioPosition(BaseModel):
    symbol: str = Field(..., description="Ticker des Portfoliotitels.")
    weight: float = Field(..., description="Portfoliogewicht (0-1).")
    amount_eur: float = Field(..., description="Investierter Betrag in EUR.")
    kelly_fraction: float = Field(..., description="Kelly-basierte Referenzgröße.")
    final_thesis: str = Field(
        ...,
        description="Finale, risikoadjustierte Investmentthese."
    )
    inclusion_rationale: str = Field(
        ...,
        description="Warum der Titel trotz Gegenargumenten im finalen Portfolio enthalten ist."
    )
    key_monitoring_point: str = Field(
        ...,
        description="Wichtigster Monitoring-Punkt nach Portfolioaufnahme."
    )
    risk_fit_commentary: str = Field(
        ...,
        description="Warum der Titel zum gewählten Risikoprofil passt."
    )
    horizon_fit_commentary: str = Field(
        ...,
        description="Warum der Titel zum Anlagehorizont passt."
    )

class MasterAuditReport(BaseModel):
    strategy_name: str = Field(
        ...,
        description="Name oder Kurzbeschreibung der finalen Strategie."
    )
    risk_profile_used: str = Field(
        ...,
        description="Verwendetes Risikoprofil."
    )
    time_horizon_used: str = Field(
        ...,
        description="Verwendeter Anlagehorizont."
    )
    portfolio_style: str = Field(
        ...,
        description="Einordnung des Portfoliostils."
    )
    portfolio: List[PortfolioPosition] = Field(
        ...,
        description="Alle finalen Positionen des Portfolios."
    )
    excluded_finalists: List[str] = Field(
        default_factory=list,
        description="Titel, die im finalen Schritt trotz Research nicht aufgenommen wurden."
    )
    allocation_rationale: str = Field(
        ...,
        description="Übergreifende Begründung der Portfolioallokation."
    )
    risk_summary: str = Field(
        ...,
        description="Zusammenfassung der wichtigsten Portfolio-Risiken."
    )
    math_audit_log: str = Field(
        ...,
        description="Ergebnis der mathematischen Validierung."
    )
    full_trace_summary: str = Field(
        ...,
        description="Zusammenfassung des gesamten Entscheidungsprozesses."
    )

# ==========================================================
# Pipeline (incl. Agents, Tasks, Tools)
# ==========================================================

def run_v33_master_pipeline():
    audit = AuditManager(SUCHE_THEMA, os.path.dirname(os.path.abspath(__file__)))
    master_llm = get_crew_llm(backend=BACKEND, model=MODEL)
    
    # --- AGENTEN ---
    
    discoverer = Agent(
        role="Head of Asset Sourcing & Public Equities Origination (Institutional IB / Buy-Side Standard)",
        goal=(
            f"Identifiziere für das Investment-Thema '{suche_thema}' jene börsennotierten Aktientitel, "
            "bei denen die Wahrscheinlichkeit am höchsten ist, dass sie den ökonomischen Wert des Themas "
            "tatsächlich monetisieren und damit als investierbare Equity-Ideen in Frage kommen. "
        "Arbeite nicht wie eine Suchmaschine, sondern wie ein institutioneller Origination-Lead: "
        "Baue zuerst ein investierbares Universum auf, segmentiere die Wertschöpfungskette, trenne direkte "
        "Pure-Plays von indirekten Enablern, Infrastruktur-, Software-, Komponenten- und Service-Playern, "
        "und isoliere anschließend die Kandidaten mit der stärksten Kombination aus thematischer Relevanz, "
        "nachweisbarer operativer Traktion, belastbarer Wettbewerbsposition und plausibler ökonomischer Hebelung. "
        "Dein Auftrag ist nicht maximale Listenlänge, sondern maximale Selektionsgüte. "
        "Jeder vorgeschlagene Ticker muss thematisch hergeleitet, über News-Signale plausibilisiert und "
        "über einen belastbaren ökonomischen Link zum Thema begründet werden. "
        "Wenn direkte Suchen zu wenig Treffer liefern, musst du das Thema intelligent abstrahieren, Synonyme, "
        "Sub-Segmente, Upstream-/Downstream-Wertschöpfungsstufen, technologische Nachbarcluster und "
        "ökonomische Enabler durchsuchen. "
        "Priorisiere unternehmensspezifische Evidenz klar vor generischen Branchenreports. "
        "Reine Marktgrößenprognosen, allgemeine Sektorberichte oder weit gefasste Trendbeschreibungen dürfen "
        "nur als Sekundärbeleg dienen und niemals der Hauptgrund für die Aufnahme eines Titels sein. "
        "Bevorzuge Signale wie konkrete Produktadoption, Management-Guidance, Segmentwachstum, Partnerschaften, "
        "kommerzielle Rollouts, Auftragsmeldungen, Kundentraktion, disclosed operating metrics oder "
        "strategische Schritte, die direkt dem Unternehmen zugeordnet werden können. "
        "Das Feld 'why_now' muss einen aktuellen oder zeitnah relevanten Trigger benennen; ein bloßer "
        "Langfristtrend ohne konkreten Timing-Aspekt genügt nicht. "
        f"Berücksichtige explizit das Mandat '{risiko}' bei einem Anlagehorizont von '{horizont}'."
        "Bei einem langfristigen Horizont darfst du kurzfristige Zyklik, temporär schwache Wachstumsphasen "
        "oder zwischenzeitliche Bewertungsvolatilität tolerieren, sofern die mehrjährige Monetarisierungslogik, "
        "die thematische Reinheit und der strukturelle Moat stark sind. "
        "Bei einem High-Risk-Mandat darfst du Titel mit höherem Upside-Potenzial, höherer Volatilität und ambitionierterer "
        "Bewertung priorisieren, solange der ökonomische Hebel und die langfristige These belastbar sind. "
        "Du priorisierst nur solche Namen, bei denen ein plausibler Zusammenhang zwischen Thema, Umsatzhebel, "
        "strategischer Positionierung und Equity-Upside erkennbar ist. "
        "Vermeide Story-Stocks ohne belastbare wirtschaftliche Verbindung. "
        "WICHTIG ZUR TICKER-WAHL: Da das nachgelagerte Finanz-Tool ('bulk_financial_metrics') auf US-zentrierte Stammdaten "
        "optimiert ist, gib zusätzlich zum primären europäischen Ticker (z.B. SAP.DE) immer den Basis-Ticker ohne Suffix (z.B. SAP) "
        "an oder bevorzuge US-ADRs/Listen-Äquivalente, falls das Primär-Listing keine Daten liefert. "
        "Die quantitative und finanzielle Validierung erfolgt in einem nachgelagerten Quant-Audit; "
        "deine Aufgabe ist die thematische Discovery, Origination und qualitative Vorselektion auf institutionellem Niveau."
        ),
        backstory=(
        "Du agierst wie ein erfahrener Asset Sourcing Lead an der Schnittstelle von Investment Banking, "
        "Equity Research und Public Markets Origination. "
        "Du bist darauf trainiert, aus unscharfen Makro-, Technologie- oder Regulierungsthemen ein investierbares "
        "Aktienuniversum abzuleiten und daraus jene Titel herauszufiltern, bei denen sich der thematische Trend "
        "mit der höchsten Wahrscheinlichkeit in operative Ergebnisse, relative Marktanteilsgewinne oder "
        "mehrjährige Equity-Narrative übersetzen lässt. "
        "Du denkst in Wertschöpfungsketten statt in Schlagworten. Wenn ein Thema wie 'Drohnen' zu wenige direkte "
        "Treffer liefert, suchst du nicht stumpf weiter, sondern zerlegst das Thema in UAV-Hardware, Sensorik, "
        "Navigation, Aerospace-Elektronik, Defense Robotics, Autonomy-Software, mission-critical communications, "
        "Zulieferer, Betreiber, Infrastruktur, regulatorische Enabler und angrenzende technologische Plattformen. "
        "Du verstehst, dass die besten Aktienideen oft nicht bei den lautesten Narrativen liegen, sondern bei den "
        "Unternehmen, die kritische Komponenten liefern, über Vertriebsmacht verfügen, in Ausschreibungen "
        "systematisch gewinnen, regulatorisch privilegiert sind oder einen schwer replizierbaren operativen "
        "Vorsprung besitzen. "
        "Du kennst den Unterschied zwischen bloßer thematischer Assoziation und echter Ergebnishebelung. "
        "Du bewertest Moats nicht oberflächlich, sondern ordnest sie präzise ein: Kostenführerschaft, Skalenvorteile, "
        "Switching Costs, installierte Basis, regulierte Eintrittsbarrieren, proprietäre Technologie, Netzwerkeffekte, "
        "Vertriebsmacht, Datenvorteile, Supply-Chain-Kontrolle, Fertigungskompetenz, missionskritische Integration "
        "oder wiederkehrende Kundenbindung. "
        "Du weißt außerdem, dass ein gutes Sourcing-Memo nicht alles auflistet, sondern schlechte Ideen aktiv verwirft. "
        "Daher sortierst du Kandidaten aus, wenn ihre Exposure zu indirekt, die News-Lage zu dünn, die Evidenz zu "
        "generisch, der ökonomische Hebel zu unklar oder der Equity Case zu narrativ und zu wenig belastbar ist. "
        "Du stützt dich bevorzugt auf unternehmensspezifische Katalysatoren und behandelst allgemeine Branchenreports "
            "nur als Hintergrundmaterial. "
            "Dein Qualitätsmaßstab ist nicht Kreativität, sondern institutionelle Verwendbarkeit in einem realen "
            "Investment-Prozess. Die finanzielle Tiefenvalidierung übernimmt ein separater Quant-Agent."
        ),
        tools=[InstitutionalNewsScanner()],
        llm=master_llm
     )

    quant = Agent(
        role="Lead Quantitative Equity Analyst & Financial Validation Specialist",
        goal=(
            "Führe für alle von Task 1 priorisierten Titel ein striktes quantitatives Audit durch. "
            "Deine Aufgabe ist es, die Shortlist nicht thematisch, sondern zahlenbasiert zu validieren. "
            "Rufe zwingend das Tool 'bulk_financial_metrics' für alle Shortlist-Ticker auf und nutze ausschließlich "
            "die daraus erhaltenen Finanzdaten als Grundlage deiner Bewertung. "
            "Du analysierst Bewertung, Profitabilität, Wachstum, Bilanzqualität, Risiko und institutionelle "
            "Investierbarkeit. Du errätst niemals fehlende Kennzahlen und übernimmst keine Zahlen aus freiem Text. "
            "Wenn Daten fehlen, markiere sie explizit als None und benenne die daraus entstehende Unsicherheit. "
            "Interpretiere Kennzahlen sektorsensitiv und nicht mechanisch. Eine hohe Verschuldung, ein Current Ratio "
            "unter 1.0 oder ein negatives Wachstumsprofil sind nicht automatisch kritisch, sondern im Kontext des "
            "Geschäftsmodells, der Kapitalintensität, der Zyklik und der Branchenstruktur zu bewerten. "
            f"Berücksichtige explizit das Mandat '{risiko}' bei einem Anlagehorizont von '{horizont}'."
            "Bei einem High-Risk-Mandat mit langfristigem Horizont sind höhere Bewertung, höhere Volatilität und "
            "zwischenzeitliche Ergebnisschwankungen tolerierbarer als in einem konservativen Mandat, sofern "
            "Profit-Pool-Potenzial, langfristige Skalierbarkeit und thematische Durability stark sind. "
            "Bewerte deshalb Bewertungsrisiko, Bilanzrisiko und kurzfristige Wachstumsdellen nicht mechanisch, "
            "sondern im Lichte des langfristigen Opportunity-Sets. "
            "Leite die quantitative Gesamteinschätzung konsistent aus fünf Dimensionen ab: "
            "1. Profitabilität, 2. Wachstumsqualität, 3. Bilanzrobustheit, 4. Bewertungsrisiko, 5. Investierbarkeit. "
            "Dein Auftrag ist es, aus Rohmetriken ein professionelles Quant-Audit zu machen, das für Portfolio- "
            "Konstruktion und finale CIO-Entscheidung belastbar ist."
        ),
        backstory=(
            "Du bist ein pedantischer Quant-Analyst mit institutionellem Qualitätsanspruch. "
            "Du vertraust keinen narrativen Investment-Storys, solange sie nicht durch Finanzdaten gestützt werden. "
            "Du denkst in Bewertungsmultiples, Margenprofilen, Kapitalrendite, Bilanzrobustheit, Wachstumsqualität, "
            "Volatilität und Investierbarkeit. "
            "Du bist nicht dafür zuständig, das Thema zu entdecken, sondern die vom Discovery-Team vorgeschlagenen "
            "Titel numerisch zu prüfen, zu strukturieren und kritisch zu klassifizieren. "
            "Du arbeitest streng datenbasiert: kein Schätzen, kein Ausschmücken, keine implizite Datenübernahme. "
            "Gleichzeitig weißt du, dass Kennzahlen ohne Geschäftsmodellkontext fehlgedeutet werden können; deshalb "
            "bewertest du Zahlen immer im Lichte von Kapitalintensität, Zyklik, Segmentmix und Marktstruktur. "
            "Wo Daten schwach, lückenhaft oder problematisch sind, dokumentierst du die Schwächen offen. "
            "Dein Output ist die quantitative Wahrheitsschicht für die weitere Entscheidungsfindung."
        ),
        tools=[BulkFinancialTool()],
        llm=master_llm
     )

    strategist = Agent(
        role="Head of Sector Intelligence & Macro Strategy",
        goal=(
            f"Erstelle für das Investment-Thema '{suche_thema}' eine institutionelle Sector- und Macro-Intelligence-Synthese "
            "auf Basis aktueller Nachrichten- und Signals-Lage. "
            "Deine Aufgabe ist es nicht, bloß viele Headlines zusammenzufassen, sondern aus der Nachrichtenlage die "
            "entscheidenden strukturellen Treiber, Nachfrageimpulse, regulatorischen Entwicklungen, geopolitischen "
            "Einflüsse, Wettbewerbsdynamiken, Kapitalallokationsmuster und Kommerzialisierungssignale herauszuarbeiten, "
            "die das Opportunity Set für Investoren prägen. "
            "Nutze den InstitutionalNewsScanner diszipliniert und formuliere eine kleine Zahl hochwertiger Suchanfragen, "
            "die den Sektor entlang seiner wichtigsten Dimensionen erfassen. "
            "Arbeite mit dem tatsächlich verfügbaren Tool-Output und erfinde keine künstliche Präzision, "
            "keine fiktiven Artikel-Indizes und keine nicht belegbaren Metadatenstrukturen. "
            "Trenne sauber zwischen harten Ereignissen (policy/company events), Marktberichten und breiten "
            "Sektorbeobachtungen. Ein Marktbericht darf nicht wie ein bestätigtes Company-Event behandelt werden. "
            "Das Ergebnis soll ein belastbarer Macro-Rahmen sein, in den die Einzeltitel aus Task 1 und Task 2 "
            "eingeordnet werden können."
        ),
        backstory=(
            "Du bist ein Chefstratege für thematische Sektoranalyse und institutionelle Makro-Synthese. "
            "Du erkennst aus Nachrichtenströmen nicht nur einzelne Events, sondern die übergeordneten Muster: "
            "wo Nachfrage strukturell entsteht, wo Regulierung Gewinner und Verlierer produziert, wo geopolitische "
            "Verschiebungen Lieferketten und Preisbildung verändern und wo Narrative durch reale Investitionsströme "
            "unterfüttert werden oder wieder auseinanderfallen. "
            "Du arbeitest verdichtend, nicht ausschmückend. "
            "Du kennst den Unterschied zwischen policy event, company event, research report und generischer "
            "Markterzählung und kennzeichnest diese Unterschiede sauber. "
            "Dein Bericht soll für nachgelagerte Equity-Research- und Portfolio-Entscheidungen verwendbar sein."
        ),
        tools=[InstitutionalNewsScanner()],
        llm=master_llm
     )

    researcher = Agent(
        role="Lead Equity Research Analyst",
        goal=(
            "Erstelle für jeden priorisierten Titel einen institutionellen Equity-Research-Deep-Dive, "
            "der qualitative Discovery-These, quantitative Validierung und sektoralen Makro-Kontext "
            "zu einer belastbaren Einzeltitelanalyse verbindet. "
            "Nutze den InstitutionalNewsScanner zusätzlich gezielt, um unternehmensspezifische Evidenz "
            "nachzurecherchieren und die Research-These mit belastbaren Signalen zu stützen. "
            "Dein Bericht soll nicht nur beschreiben, warum ein Titel interessant klingt, sondern "
            "warum der Equity Case im Lichte von Wettbewerb, Financials und aktuellem Sektorregime "
            "tragfähig oder angreifbar ist. "
            "Zitationen müssen tool-grounded sein. Wenn du eine Quelle nicht glaubwürdig aus Scanner-Output "
            "oder belastbarem Kontext ableiten kannst, darfst du sie nicht als harte Citation ausgeben."
        ),
        backstory=(
            "Du arbeitest wie ein Tier-1 Equity Research Analyst. "
            "Du baust keine bloßen Storys, sondern Investmentthesen mit Belegkette. "
            "Du verbindest Company-Specific Catalysts, Moat-Struktur, Kapitalmarktlogik, "
            "quantitative Realität und sektorale Makrodynamik zu einer sauberen Einzeltitelbeurteilung. "
            "Du bist besonders sensibel für die Frage, ob eine gute Story auch durch Evidenz getragen wird. "
            "Du unterscheidest strikt zwischen direkter Scanner-Evidenz, abgeleiteter Evidenz und "
            "bloßer Kontextreferenz."
        ),
        tools=[InstitutionalNewsScanner()],
        llm=master_llm
     )

    challenger = Agent(
        role="Head of Risk Challenge & Bear-Case Review",
        goal=(
            "Greife die optimistischen Bull-Thesen aus dem Equity-Research systematisch an und formuliere "
            "für jeden priorisierten Titel einen belastbaren Bear-Case. "
            "Deine Aufgabe ist nicht, pauschal negativ zu sein, sondern die wahrscheinlichsten Wege zu identifizieren, "
            "über die die Investmentthese scheitern, sich verzögern oder vom Markt anders gepreist werden könnte als erwartet. "
            "Nutze dafür die qualitative These aus Task 1, die quantitative Validierung aus Task 2, den Makro-Rahmen aus Task 3 "
            "und den Equity-Research-Deep-Dive aus Task 4. "
            f"Kalibriere deine Bear-Cases auf das Mandat '{RISIKO_PROFIL}' und den Anlagehorizont '{ANLAGE_HORIZONT}'. "
            "Unterscheide zwischen kurzfristigen Enttäuschungen, die für ein langfristiges Mandat tolerierbar sein können, "
            "und echten Thesis-Break-Risiken, die die mehrjährige Investmentlogik zerstören würden. "
            "Gewichte langfristige strukturelle Risiken höher als rein kurzfristige Ergebnisvolatilität. "
            "Prüfe insbesondere, ob der Moat überschätzt, der Wachstumspfad zu optimistisch, die Bewertung zu ambitioniert, "
            "die Zyklik unterschätzt, die Makro-Lage zu freundlich interpretiert oder die Evidenzbasis zu schwach ist. "
            "Leite für jeden Titel einen realistischen Bear-Case mit klarer Failure-Mechanik, Downside-Szenario "
            "und Einschätzung der Eintrittswahrscheinlichkeit ab."
        ),
        backstory=(
            "Du bist der härteste Gegenprüfer im Investmentprozess. "
            "Du bist nicht dafür da, Ideen zu zerstören, sondern Selbsttäuschung zu verhindern. "
            "Du liest Bull-Thesen wie ein Short-Seller, ein Risiko-Manager und ein skeptischer PM zugleich. "
            "Du fragst immer: Wo ist die schwächste Stelle? Welche Annahme ist am fragilsten? "
            "Was, wenn Wachstum nur zyklisch war? Was, wenn der Moat weniger stark ist als angenommen? "
            "Was, wenn die Bewertung keinen Fehler erlaubt? "
            "Du suchst nicht nach rhetorischen Gegenargumenten, sondern nach echten Failure-Modes: "
            "Nachfrageeinbruch, Margendruck, regulatorische Intervention, Wettbewerbsintensivierung, "
            "Bilanzstress, Kapitaldisziplinprobleme, Execution-Risiken, M&A-Fehlintegration, "
            "Technologieverzögerung oder falsche Marktpositionierung. "
            "Dein Output muss für CIO und Portfolio-Konstruktion direkt nutzbar sein."
        ),
        llm=master_llm
        )

    cio = Agent(
        role="Chief Investment Officer (CIO) – Final Portfolio Construction & Capital Allocation",
        goal=(
            f"Baue das finale, thematisch saubere und risikobewusste Portfolio für '{suche_thema}' und ein "
            f"Gesamtkapital von {kapital} EUR. "
            "Du integrierst die Discovery-These, das Quant-Audit, den Makro-Rahmen, die Equity-Research-Deep-Dives "
            "und die Bear-Cases zu einer finalen Investitionsentscheidung. "
            "Du darfst nur Titel berücksichtigen, die im finalen Research-Briefing belastbar vertreten sind. "
            "Das Portfolio darf nur aus Namen bestehen, die thematisch sauber, evidenzgestützt und im Verhältnis "
            "von Upside zu Risiko vertretbar sind. "
            "Das Kelly-Tool dient dir als Orientierung für Positionsgrößen, aber du handelst nicht mechanisch; "
            "du musst Kelly, thematische Reinheit, Konzentrationsrisiko, Bear-Case-Schwere, Makro-Lage und "
            "institutionelle Plausibilität gemeinsam abwägen. "
            f"Berücksichtige explizit das Mandat '{risiko}' bei einem Anlagehorizont von '{horizont}'."
            "Bei einem High-Risk-Mandat mit langfristigem Horizont darf das finale Portfolio konzentrierter sein und höhere "
            "zwischenzeitliche Volatilität tolerieren, sofern die Titel einen starken langfristigen thematischen Hebel, "
            "robuste Moats und ein attraktives mehrjähriges Upside-Profil aufweisen. "
            "Gewichte kurzfristige Schwankungen, Beta und temporäre Bewertungsdehnung geringer als die Frage, "
            "ob ein Titel über mehrere Jahre einen großen Anteil des thematischen Value Pools abschöpfen kann. "
            "Reduziere jedoch kompromisslos Titel mit schwacher Evidenz, fragiler These oder unklarem langfristigem "
            "Wettbewerbsvorteil. "
            "Wenn ein Titel trotz attraktiver Bull-These im Bear-Case oder Quant-Audit zu schwach erscheint, "
            "darfst du ihn reduzieren oder vollständig ausschließen. "
            f"STRENGSTES THEMENGEBOT: Wenn ein Titel nicht sauber zum Thema '{SUCHE_THEMA}' passt, "
            "darf er nicht ins Portfolio. "
            "Du musst die finale Allokation mathematisch validieren. "
            "Nutze den `strict_math_validator` zwingend mit einem strukturierten JSON der Form "
            '{"total_capital": <KAPITAL_EUR>, "portfolio": [...]} '
            "und übernimm das Validator-Ergebnis in `math_audit_log`. "
            "Wenn der Validator Fehler oder Inkonsistenzen meldet, musst du die Allokation korrigieren, "
            "bevor du dein finales Ergebnis abgibst. "
            "Dein Output muss ein vollständig auditierbares, logisch begründetes und mathematisch konsistentes "
            "Portfolio-Resultat sein."
        ),
        backstory=(
            "Du bist der finale Kapitalallokator. "
            "Du entscheidest nicht auf Basis einzelner schöner Narrative, sondern auf Basis von Konsistenz "
            "zwischen Thema, Wettbewerbsvorteil, Quant-Profil, Makro-Lage und Risk/Reward. "
            "Du bist weder blind bullish noch mechanisch quantitativ. "
            "Du weißt, dass das beste Portfolio nicht aus den meisten Ideen besteht, sondern aus den belastbarsten. "
            "Du arbeitest mit institutioneller Strenge: keine thematische Verwässerung, keine unklare Evidenz, "
            "keine mathematischen Fehler, keine nicht verteidigbaren Positionsgrößen. "
            "Du nutzt Kelly diszipliniert, aber nicht dogmatisch. "
            "Du reduzierst Konzentrationsrisiko dort, wo die Failure-Modes korreliert sind, und bevorzugst Namen, "
            "bei denen Bull-These und Bear-Case in einem vernünftigen Verhältnis stehen. "
            "Du gibst niemals ein finales Portfolio aus, ohne die mathematische Konsistenz der Gewichte und Beträge "
            "über den Validator geprüft zu haben. "
            "Dein Output ist das finale Investmentkomitee-taugliche Ergebnis."
        ),
        tools=[KellyCriterionTool(), StrictMathValidator()],
        llm=master_llm
        )

    # --- TASKS ---

    t1 = Task(
        description=(
            f"Erstelle ein institutionelles Origination-Memo für das Investment-Thema '{SUCHE_THEMA}'. "
            "Das Memo soll nicht als bloße Themenliste, sondern als belastbares Discovery- und Pre-Screening-Dokument "
            "für investierbare Public-Equity-Ideen aufgebaut werden. "
            "\n\n"
            "ARBEITSAUFTRAG UND METHODIK:\n"
            "1) UNIVERSE DEFINITION / INVESTABLE SCOPE:\n"
            "   - Definiere zunächst präzise, was unter dem Thema zu verstehen ist und welche Teilsegmente "
            "     tatsächlich investierbar sind.\n"
            "   - Zerlege das Thema in Wertschöpfungsstufen und Exposures: direkte Pure-Plays, Infrastruktur, "
            "     Software, Komponenten, Zulieferer, Plattformen, Betreiber, Services, Enabler und angrenzende Gewinnersegmente.\n"
            "   - Identifiziere daraus relevante geografische Cluster und börsennotierte Kandidaten.\n"
            "   - Trenne klar zwischen hoher thematischer Reinheit, partieller Exposure und bloßer Randassoziation.\n"
            "\n"
            "2) SIGNALS INTELLIGENCE / NEWS-BASED ORIGINATION:\n"
            "   - Scanne relevante News-Signale systematisch in deutscher und englischer Sprache.\n"
            "   - Nutze den 'InstitutionalNewsScanner' mehrfach und intelligent, nicht nur mit dem Primärbegriff, "
            "     sondern auch mit Synonymen, Subsegmenten, Anwendungsfeldern, Wertschöpfungsstufen, "
            "     regulatorischen Treibern und technologischen Nachbarbegriffen.\n"
            "   - Wenn direkte Suchanfragen keine oder zu wenige verwertbare Treffer liefern, abstrahiere das Thema "
            "     professionell und leite alternative Suchbegriffe entlang der ökonomischen Logik des Themas ab.\n"
            "   - Berücksichtige Hinweise auf Auftragsgewinne, Partnerschaften, neue Produkte, Kapazitätsausbau, "
            "     regulatorische Vorteile, Marktanteilsgewinne, Nachfragebeschleunigung, strategische Positionierung, "
            "     Segmentwachstum, Management-Guidance, kommerzielle Rollouts, Kundentraktion oder strukturelle "
            "     Nachfrageverschiebungen.\n"
            "   - Priorisiere unternehmensspezifische Evidenz klar vor generischen Branchenreports.\n"
            "   - Reine Marktgrößenprognosen, allgemeine Sektorberichte oder breit gefasste Trendbeschreibungen dürfen "
            "     nur als Sekundärbeleg verwendet werden und niemals der Hauptgrund für die Aufnahme eines Titels sein.\n"
            "   - Vermeide die Aufnahme von Kandidaten, deren Relevanz sich nur aus vagen Pressemeldungen, reinem "
            "     Marketing oder aus zu allgemeinen Branchenstudien ableitet.\n"
            "\n"
            "3) CANDIDATE SELECTION / ECONOMIC LINKAGE TEST:\n"
            "   - Prüfe für jeden Kandidaten explizit, wie genau das Thema in Umsatz, Marge, Auftragslage, "
            "     Marktanteil oder strategische Relevanz übersetzen könnte.\n"
            "   - Bevorzuge Unternehmen, bei denen der ökonomische Nutzen des Themas mit hoher Wahrscheinlichkeit "
            "     beim börsennotierten Vehikel ankommt.\n"
            "   - Sei skeptisch bei Konglomeraten oder stark diversifizierten Firmen, wenn das Thema dort nur ein "
            "     kleiner und kaum kursrelevanter Teil des Geschäfts ist.\n"
            "   - Kennzeichne den Exposure-Typ als Pure-Play, High-Exposure, Selective Exposure oder Indirect Enabler.\n"
            "\n"
            "4) MOAT VALIDATION:\n"
            "   - Identifiziere für jeden ernsthaften Kandidaten den wahrscheinlichsten Wettbewerbsvorteil bzw. Moat-Typ.\n"
            "   - Zulässige Moat-Typen sind insbesondere: Skalenvorteil, Kostenführerschaft, Switching Costs, "
            "     installierte Basis, regulatorische Eintrittsbarriere, proprietäre Technologie/IP, "
            "     Fertigungskompetenz, Supply-Chain-Kontrolle, Vertriebsmacht, Datenvorteil, Ökosystembindung, "
            "     Brand/Trust oder missionskritische Integration.\n"
            "   - Der Moat darf nicht nur behauptet werden; er muss aus der Positionierung des Unternehmens und "
            "     möglichst aus unternehmensspezifischen Signalen nachvollziehbar begründet werden.\n"
            "\n"
            "5) ELIMINATION DISCIPLINE:\n"
            "   - Verwirf Kandidaten aktiv, wenn mindestens einer der folgenden Punkte zutrifft:\n"
            "       a) thematische Relevanz zu indirekt oder opportunistisch,\n"
            "       b) News-Lage zu dünn oder nicht belastbar,\n"
            "       c) Evidenz zu generisch und nicht ausreichend unternehmensspezifisch,\n"
            "       d) kein nachvollziehbarer ökonomischer Hebel,\n"
            "       e) kein plausibler Moat.\n"
            "   - Qualität geht vor Vollständigkeit.\n"
            "   - Wenn ein Kandidat zwar thematisch passt, aber im relativen Vergleich zu klar stärkeren Peers "
            "     unterlegen ist, darfst du ihn verwerfen oder niedriger priorisieren.\n"
            "\n"
            "6) FINAL OUTPUT / DISCOVERY MEMO:\n"
            "   - Erstelle am Ende ein strukturiertes institutionelles Discovery-Memo.\n"
            "   - Für jeden finalen Titel muss enthalten sein:\n"
            "       • Unternehmensname\n"
            "       • Ticker\n"
            "       • Rolle im Themen-Ökosystem\n"
            "       • Art der Exposure\n"
            "       • zentrale News-/Signalbegründung\n"
            "       • ökonomischer Hebel / warum das Thema beim Unternehmen monetarisierbar ist\n"
            "       • Moat-Typ mit Begründung\n"
            "       • Conviction-Score von 1 bis 10\n"
            "       • kurze, nüchterne Buy-Side-Logik, warum der Titel in die Shortlist gehört\n"
            "   - Das Feld 'why_now' muss einen aktuellen oder zeitnah relevanten Trigger enthalten; "
            "     ein bloßer Langfristtrend ohne Timing-Aspekt genügt nicht.\n"
            "   - News-Signale sollen möglichst unternehmensspezifisch sein. Allgemeine Marktberichte sind nur "
            "     als Hintergrundbeleg zulässig.\n"
            "   - Ergänze außerdem eine Liste verworfener oder niedrig priorisierter Kandidaten mit Ablehnungsgrund.\n"
            "\n"
            "WICHTIGE REGELN:\n"
            "   - Kein Halluzinieren bei News, Unternehmensbezug oder kommerzieller Traktion.\n"
            "   - Nicht jedes thematisch passende Unternehmen ist ein investierbarer Gewinner.\n"
            "   - Bevorzuge belastbare ökonomische Gewinner vor narrativ lauten Namen.\n"
            "   - Die finanzielle und quantitative Validierung erfolgt in einem separaten Quant-Audit nachgelagert.\n"
            "   - Verwende keine impliziten Aussagen über finanzielle Validierung, finanzielle Stabilität oder "
            "     quantitative Investierbarkeit, sofern diese nicht rein qualitativ und ohne Kennzahlenbezug "
            "     begründet werden können.\n"
            f"   - Berücksichtige das Mandat '{RISIKO_PROFIL}' bei einem Anlagehorizont von '{ANLAGE_HORIZONT}'. "
            "     Langfristig starke, thematisch reine und potenziell asymmetrische Ideen dürfen priorisiert werden, "
            "     selbst wenn kurzfristige Zyklik oder Volatilität höher ist."
        ),
        expected_output=(
            "Ein institutionelles DiscoveryContract im Stil eines Public-Equities-Origination-Memos mit: "
            "klar definierter Universe-Logik, intelligentem News-Sourcing, expliziter Exposure-Klassifikation, "
            "möglichst unternehmensspezifischen Katalysatoren, sauber hergeleitetem ökonomischem Link, "
            "Moat-Herleitung, harter Negativselektion und realistisch hergeleitetem Conviction-Grading je finalem Ticker."
        ),
        agent=discoverer,
        output_pydantic=DiscoveryContract,
        callback=audit.stream_callback
        )

    t2 = Task(
        description=(
            "Führe ein vollständiges quantitatives Audit für alle `shortlisted_assets` aus Task 1 durch.\n"
            "\n"
            "ARBEITSAUFTRAG:\n"
            "1. Extrahiere alle Ticker aus den `shortlisted_assets` von Task 1.\n"
            "2. Rufe für diese Ticker zwingend das Tool `bulk_financial_metrics` auf.\n"
            "3. Nutze ausschließlich die Tool-Ausgabe als Quelle für Rohmetriken.\n"
            "4. Dokumentiere pro Ticker mindestens folgende Kennzahlen, soweit verfügbar:\n"
            "   - P/E\n"
            "   - P/S\n"
            "   - EV/EBITDA\n"
            "   - Beta\n"
            "   - Dividend Yield\n"
            "   - ROE\n"
            "   - Net Margin\n"
            "   - Operating Margin\n"
            "   - Debt/Equity\n"
            "   - Current Ratio\n"
            "   - Revenue Growth\n"
            "   - FCF Growth\n"
            "5. PROAKTIVES TICKER-HANDLING: Falls das Tool `bulk_financial_metrics` für einen Ticker mit Suffix (z.B. .DE, .PA) "
            "keine Daten liefert, ist dies ein bekannter technischer Limitationseffekt. Du musst in diesem Fall zwingend "
            "einen zweiten Versuch mit dem Basis-Symbol ohne Suffix (z.B. SAP statt SAP.DE) unternehmen, um die Ausbeute "
            "an quantitativen Daten zu maximieren. Akzeptiere Daten von US-Äquivalenten/ADRs als Proxy.\n"
            "6. Beurteile zusätzlich je Ticker (und dokumentiere dies in der `FinancialValidation`): "
            "Bewertungsprofil, Qualitätsprofil, Bilanz- und Risikoprofil sowie institutionelle Investierbarkeit.\n"
            "7. Interpretiere Kennzahlen sektorsensitiv und nicht mechanisch. Eine hohe Verschuldung, ein Current Ratio "
            "   unter 1.0 oder negatives Wachstum sind nicht automatisch kritisch, sondern im Kontext des "
            "   Geschäftsmodells, der Kapitalintensität, der Zyklik, des Segmentmixes und der Branchenstruktur "
            "   zu bewerten.\n"
            "8. Leite den `quant_conviction_score` konsistent aus fünf Dimensionen ab:\n"
            "   - Profitabilität\n"
            "   - Wachstumsqualität\n"
            "   - Bilanzrobustheit\n"
            "   - Bewertungsrisiko\n"
            "   - Investierbarkeit\n"
            "9. Weise jedem Ticker einen `investability_score` und einen `quant_conviction_score` von 1 bis 10 zu.\n"
            "10. Wenn Kennzahlen fehlen, markiere sie explizit als None und benenne die daraus entstehende "
            "    Unsicherheit im Kommentartext.\n"
            "11. Die `summary` in `FinancialValidation` soll ein kompaktes Gesamturteil in 2-3 Sätzen sein und "
            "    nicht bloß alle Teilkommentare wiederholen.\n"
            "12. Wenn du im Kommentartext Kontext aus Task 1 nutzt (z.B. Segmentwachstum oder thematische Exposure), "
            "    kennzeichne dies sprachlich als Kontextintegration und nicht als Rohdatenbefund aus `bulk_financial_metrics`.\n"
            f"13. Berücksichtige das Mandat '{RISIKO_PROFIL}' bei einem Anlagehorizont von '{ANLAGE_HORIZONT}'. "
            "    Höhere Bewertung, höhere Volatilität oder temporäre Wachstumsdellen sind in einem aggressiven, "
            "    langfristigen Mandat tolerierbarer, sofern die langfristige Skalierbarkeit und Profit-Pool-Logik stark ist.\n"
            "\n"
            "WICHTIGE REGELN:\n"
            "   - Kein Schätzen fehlender Kennzahlen.\n"
            "   - Keine Zahlen aus Narrativen oder Fließtext übernehmen.\n"
            "   - Keine neue Titelauswahl treffen; prüfe nur die Shortlist aus Task 1.\n"
            "   - Die Bewertung soll streng datenbasiert, aber geschäftsmodell- und sektorsensitiv erfolgen.\n"
            "   - Ziel ist ein belastbares Quant-Audit für die weitere Portfolio-Konstruktion."
        ),
        expected_output=(
            "Ein QuantAuditContract mit einer quantitativen Einzelbewertung je Shortlist-Ticker, "
            "inklusive Rohmetriken, strukturierter FinancialValidation, sektorsensitiver Einordnung von "
            "Bewertung, Qualität, Bilanz und Risiko sowie konsistent hergeleitetem Investability-Score "
            "und Quant-Conviction-Score."
        ),
        agent=quant,
        context=[t1],
        output_pydantic=QuantAuditContract,
        callback=audit.stream_callback
        )

    t3 = Task(
        description=(
            f"Erstelle eine institutionelle Sector- und Macro-Intelligence-Synthese für das Investment-Thema '{SUCHE_THEMA}'.\n"
            "\n"
            "ARBEITSAUFTRAG:\n"
            "1. Nutze den `InstitutionalNewsScanner`, um die aktuelle Nachrichtenlage systematisch zu erfassen.\n"
            "2. Verwende eine kleine Zahl hochwertiger Suchanfragen, wenn dies für eine robustere Sektorabdeckung "
            "   erforderlich ist.\n"
            "3. Priorisiere Nachrichten ab 2026 und ignoriere ältere Evidenz, sofern sie nicht zwingend für Kontext "
            "   oder Regimewechsel erforderlich ist.\n"
            "4. Identifiziere und synthetisiere insbesondere:\n"
            "   - strukturelle Nachfrage- und Adoptionssignale\n"
            "   - regulatorische und politische Treiber\n"
            "   - geopolitische Einflüsse auf Lieferketten, Capex und Nachfrage\n"
            "   - Wettbewerbsdynamik und Marktstruktur\n"
            "   - technologische Reifegrade und Kommerzialisierungsmuster\n"
            "   - Investitions-, M&A- und Konsolidierungstrends\n"
            "5. Klassifiziere priorisierte Events explizit nach `event_type`:\n"
            "   - `policy_event`\n"
            "   - `company_event`\n"
            "   - `market_report`\n"
            "   - `industry_event`\n"
            "   - `macro_event`\n"
            "6. Behandle Marktberichte, Marktgrößenprognosen oder Research Reports niemals wie harte bestätigte "
            "   Company- oder Policy-Events.\n"
            "7. Arbeite mit dem tatsächlich verfügbaren Tool-Output und erfinde keine künstlichen Artikel-Indizes, "
            "   keine fiktiven Referenzsysteme und keine nicht belegbaren Mengenangaben.\n"
            "8. Verdichte die Nachrichtenlage in einen Bericht, der als Makro-Rahmen für die Einzeltitelanalyse "
            "   aus Task 4 dienen kann.\n"
            "9. Formuliere explizit `macro_implications_for_shortlist`, also welche Teile des Makrobilds die "
            "   Shortlist aus Task 1 stützen oder schwächen.\n"
            "\n"
            "WICHTIGE REGELN:\n"
            "   - Nicht bloß Headlines aneinanderreihen, sondern Muster extrahieren.\n"
            "   - Keine scheingenaue Referenzierung, wenn das Tool diese Struktur nicht explizit liefert.\n"
            "   - Trenne harte Evidenz, Marktreports und weiche Makrobeobachtungen sauber.\n"
            "   - Fokus auf entscheidungsrelevante Makro-Implikationen für Investoren."
        ),
        expected_output=(
            "Ein MacroNewsContract mit priorisierten Sektorevents, belastbarer Makro-Synthese, "
            "klaren Demand-/Regulatory-/Geopolitical-/Market-Structure-Observations und expliziten "
            "Implikationen für die Shortlist aus Task 1."
        ),
        agent=strategist,
        context=[t1],
        output_pydantic=MacroNewsContract,
        callback=audit.stream_callback
        )

    t4 = Task(
        description=(
            "Erstelle für JEDEN Titel aus der Shortlist einen institutionellen Equity-Research-Deep-Dive.\n"
            "\n"
            "ARBEITSAUFTRAG:\n"
            "1. Nutze die Discovery-Ergebnisse aus Task 1 als Ausgangspunkt für die qualitative Investmentthese.\n"
            "2. Nutze das Quant-Audit aus Task 2, um die These finanziell und investierbarkeitsseitig zu prüfen.\n"
            "3. Nutze die Sector-/Macro-Intelligence aus Task 3, um den Titel im aktuellen Markt- und Regimekontext "
            "   einzuordnen.\n"
            "4. Ziehe zusätzlich den `InstitutionalNewsScanner` heran, um pro Unternehmen gezielt "
            "   unternehmensspezifische Evidenz nachzurecherchieren.\n"
            "5. Erstelle pro Unternehmen einen Deep-Dive mit:\n"
            "   - verdichteter Investmentthese\n"
            "   - Micro-Analyse des Geschäftsmodells und des Moats\n"
            "   - Macro-Analyse im sektoralen und geopolitischen Kontext\n"
            "   - Quant-Integration\n"
            "   - Thesis-Consistency-Check: passen Discovery, Quant und Macro wirklich zusammen?\n"
            "   - zentralen Risiken\n"
            "6. Zitationen müssen belastbar und tool-grounded sein.\n"
            "7. Verwende nur solche URLs, Datumsangaben und Zitat-/Snippet-Elemente, die aus deiner Evidenzkette "
            "   tatsächlich ableitbar sind.\n"
            "8. Kennzeichne jede Citation mit `citation_type`:\n"
            "   - `scanner_direct` = direkt aus Scanner-Evidenz abgeleitet\n"
            "   - `scanner_derived` = aus Scanner-Ausgabe plausibel verdichtet\n"
            "   - `context_referenced` = aus früherem Task-Kontext referenziert, aber nicht direkt nachgezogen\n"
            "9. Gib keine Citation als hoch belastbar aus, wenn sie nur `context_referenced` ist.\n"
            "10. Erfinde keine Quellen, keine Zitate und keine URLs.\n"
            "\n"
            "WICHTIGE REGELN:\n"
            "   - Wiederhole nicht nur Task 1 oder Task 2, sondern integriere beide Ebenen analytisch.\n"
            "   - Company-specific evidence hat Vorrang vor generischen Branchenreferenzen.\n"
            "   - Die Research-These muss belegbasiert und gegliedert sein.\n"
            "   - Jede Analyse soll für einen nachgelagerten Bear-Case-Reviewer und den CIO verwendbar sein.\n"
            "   - Wenn die Evidenzlage schwach ist, benenne die Schwäche explizit statt sie mit Sprache zu kaschieren."
        ),
        expected_output=(
            "Ein ResearchContract mit individuellen Deep-Dives pro Ticker, jeweils mit "
            "Investment-These, Micro-Analyse, Macro-Einordnung, Quant-Integration, "
            "Thesis-Consistency-Check, Risiken und belastbaren Citations."
        ),
        agent=researcher,
        context=[t1, t2, t3],
        output_pydantic=ResearchContract,
        callback=audit.stream_callback
        )

    t5 = Task(
        description=(
            "Erstelle für jeden im ResearchContract enthaltenen Titel einen institutionellen Bear-Case.\n"
            "\n"
            "ARBEITSAUFTRAG:\n"
            "1. Nutze die Equity-Research-Deep-Dives aus Task 4 als Primärbasis.\n"
            "2. Berücksichtige zusätzlich die Discovery-These aus Task 1, das Quant-Audit aus Task 2 "
            "   und den Makro-Rahmen aus Task 3, sofern diese im Kontext verfügbar sind.\n"
            "3. Formuliere für jeden Titel nicht bloß allgemeine Risiken, sondern einen echten Bear-Case mit:\n"
            "   - klarer Failure-Mechanik\n"
            "   - zentraler Gegen-These zur Bull-Story\n"
            "   - geschätztem Downside-Potenzial in Prozent\n"
            "   - geschätzter Eintrittswahrscheinlichkeit des negativen Szenarios\n"
            "   - Benennung des wichtigsten Trigger-Risikos\n"
            "4. Prüfe insbesondere folgende Failure-Modes:\n"
            "   - überschätzter Moat\n"
            "   - zu optimistische Wachstumsannahmen\n"
            "   - Bewertungsdekompression / Multiple Compression\n"
            "   - Zyklik / Nachfragerückgang\n"
            "   - Margendruck / operative Enttäuschung\n"
            "   - Bilanz- oder Cashflow-Risiken\n"
            "   - Regulierungs- oder politische Risiken\n"
            "   - Wettbewerbsintensivierung\n"
            "   - Execution-Risiken / Verzögerungen / Fehlallokation von Kapital\n"
            "5. Der Bear-Case soll realistisch und investierbar sein; vermeide rein theoretische Weltuntergangsszenarien.\n"
            "6. Wenn ein Titel zwar grundsätzlich attraktiv bleibt, aber nur unter sehr engen Annahmen funktioniert, "
            "   muss der Bear-Case diese Fragilität klar benennen.\n"
            f"7. Kalibriere den Bear-Case auf das Mandat '{RISIKO_PROFIL}' und den Anlagehorizont '{ANLAGE_HORIZONT}'. "
            "   Langfristig tolerierbare kurzfristige Schwankungen sind anders zu gewichten als echte strukturelle Thesis-Break-Risiken.\n"
            "\n"
            "WICHTIGE REGELN:\n"
            "   - Nicht nur Risiken auflisten, sondern Failure-Mechanismen erklären.\n"
            "   - Der Bear-Case muss sich explizit gegen die Bull-These richten.\n"
            "   - Kein generischer Copy-Paste-Risiko-Text.\n"
            "   - Die Output-Qualität muss für den CIO direkt zur Positionsgrößenentscheidung nutzbar sein."
        ),
        expected_output=(
            "Ein ChallengerContract mit einem strukturierten Bear-Case je Titel, inklusive Gegen-These, "
            "Failure-Mechanik, Downside-Potenzial, Eintrittswahrscheinlichkeit und zentralem Trigger-Risiko."
        ),
        agent=challenger,
        context=[t1, t2, t3, t4],
        output_pydantic=ChallengerContract,
        callback=audit.stream_callback
        )

    t6 = Task(
        description=(
            f"Baue das finale Portfolio für {kapital} EUR auf Basis der bisherigen Pipeline.\n"
            "\n"
            "ARBEITSAUFTRAG:\n"
            "1. Berücksichtige die Discovery-Ergebnisse aus Task 1, das Quant-Audit aus Task 2, "
            "   die Sector-/Macro-Intelligence aus Task 3, die Equity-Research-Deep-Dives aus Task 4 "
            "   und die Bear-Cases aus Task 5.\n"
            "2. Wähle ausschließlich Titel aus, die im ResearchContract aus Task 4 enthalten sind.\n"
            "3. Prüfe für jeden potenziellen Portfoliotitel:\n"
            "   - thematische Reinheit / Fit zum Suchthema\n"
            "   - Belastbarkeit der qualitativen These\n"
            "   - Stärke des Quant-Profils\n"
            "   - Makro-/Sektorunterstützung oder Gegenwind\n"
            "   - Schwere und Wahrscheinlichkeit des Bear-Cases\n"
            "4. Nutze das Kelly-Tool zur Orientierung für die Positionsgröße, aber übernimm die Ergebnisse nicht blind. "
            "   Passe Gewichte an, wenn Bear-Case-Risiken, thematische Korrelationen oder Makro-Risiken dies erfordern.\n"
            "5. Jede Position muss enthalten:\n"
            "   - Symbol\n"
            "   - Gewicht\n"
            "   - Betrag in EUR\n"
            "   - Kelly Fraction\n"
            "   - finale Investmentthese\n"
            "6. Jede finale Investmentthese muss sich explizit auf die qualitative These aus Task 1, "
            "   die Quant-Einordnung aus Task 2 und die kritischste Gegenhypothese aus Task 5 beziehen.\n"
            "7. Wenn ein Titel zwar interessant ist, aber der Bear-Case oder das Quant-Profil zu schwach ausfällt, "
            "   reduziere die Positionsgröße oder schließe den Titel aus.\n"
            "8. Stelle sicher, dass die Summe aller Gewichte exakt 1.0 ergibt.\n"
            "9. Nutze das `strict_math_validator` Tool, um die finale Gewichtung zu prüfen.\n"
            "10. Wenn kein Portfolio mit ausreichender thematischer Sauberkeit und Evidenzqualität gebaut werden kann, "
            "    gib dies explizit an statt ein künstlich vollständiges Portfolio zu erzwingen.\n"
            f"11. Berücksichtige explizit das Mandat '{RISIKO_PROFIL}' und den Anlagehorizont '{ANLAGE_HORIZONT}'. "
            "    Ein aggressives Langfrist-Mandat darf konzentrierter sein, höhere Volatilität tolerieren und "
            "    mehr Upside-Asymmetrie suchen. Begründe dies explizit je Position.\n"
            "\n"
            "WICHTIGE REGELN:\n"
            f"   - Kein Titel außerhalb des Themas '{SUCHE_THEMA}'.\n"
            "   - Keine Titel außerhalb des ResearchContract aus Task 4.\n"
            "   - Keine mathematischen Inkonsistenzen.\n"
            "   - Kein mechanisches Kelly-Folgen ohne qualitative Risikoadjustierung.\n"
            "   - Das finale Portfolio muss auditierbar, logisch begründet und investitionskomitee-tauglich sein."
        ),
        expected_output=(
            "Ein vollständiger MasterAuditReport mit finalem Portfolio, risikoadjustierten Gewichten, "
            "Kelly-Referenz, mathematischer Validierung und einer konsistenten Zusammenfassung des "
            "gesamten Investmentprozesses."
        ),
        agent=cio,
        context=[t1, t2, t3, t4, t5],
        output_pydantic=MasterAuditReport,
        callback=audit.stream_callback
        )

    # --- CREW EXECUTION ---
    
    crew = Crew(
            agents=[discoverer, quant, strategist, researcher, challenger, cio],
            tasks=[t1, t2, t3, t4, t5, t6],
            process=Process.sequential,
            verbose=True
        )
        
    result = crew.kickoff()


    # --- REPORT RENDERING ---

    with open(audit.audit_file, "a", encoding="utf-8") as f:
        f.write("# 🏛️ FINAL MASTER PRE-AUDIT SUMMARY\n\n")
        f.write("✅ **Vollständiger Audit-Prozess (Discovery bis Portfolio) abgeschlossen.**\n\n")
        f.write(f"- Audit-Datei: `{os.path.basename(audit.audit_file)}`\n")
        f.write(f"- Report-Datei: `{os.path.basename(audit.report_file)}`\n")

    try:
        task_outputs = _extract_results_from_crew_result(result)

        if len(task_outputs) >= 6:
            discovery_obj = _get_task_pydantic(task_outputs[0])
            quant_obj = _get_task_pydantic(task_outputs[1])
            macro_obj = _get_task_pydantic(task_outputs[2])
            research_obj = _get_task_pydantic(task_outputs[3])
            bear_obj = _get_task_pydantic(task_outputs[4])
            portfolio_obj = _get_task_pydantic(task_outputs[5])

            if all([discovery_obj, quant_obj, macro_obj, research_obj, bear_obj, portfolio_obj]):
                render_investment_report(
                    discovery=discovery_obj,
                    quant=quant_obj,
                    macro=macro_obj,
                    research=research_obj,
                    bear=bear_obj,
                    portfolio=portfolio_obj,
                    output_file=audit.report_file,
                    suche_thema=SUCHE_THEMA,
                    kapital_eur=KAPITAL_EUR,
                    risiko_profil=RISIKO_PROFIL,
                    anlage_horizont=ANLAGE_HORIZONT
                )
                print(f"✅ Formatierter Investment Report erstellt: {audit.report_file}")
            else:
                print("⚠️ Report Rendering übersprungen: Nicht alle Task-Pydantic-Outputs verfügbar.")
                with open(audit.audit_file, "a", encoding="utf-8") as f:
                    f.write("\n## ⚠️ REPORT RENDERING SKIPPED\n")
                    f.write("Nicht alle Task-Pydantic-Outputs waren verfügbar.\n")
        else:
            print("⚠️ Report Rendering übersprungen: Task-Outputs konnten nicht vollständig extrahiert werden.")
            with open(audit.audit_file, "a", encoding="utf-8") as f:
                f.write("\n## ⚠️ REPORT RENDERING SKIPPED\n")
                f.write("Task-Outputs konnten nicht vollständig extrahiert werden.\n")
    except Exception as e:
        print(f"⚠️ Fehler beim Rendern des Investment Reports: {e}")
        with open(audit.audit_file, "a", encoding="utf-8") as f:
            f.write("\n## ⚠️ REPORT RENDERING ERROR\n")
            f.write(f"{str(e)}\n")

    if os.path.exists(audit.audit_file):
        print(f"✅ V33 Master Audit erfolgreich abgeschlossen: {audit.audit_file}")
    if os.path.exists(audit.report_file):
        print(f"✅ V33 Investment Report erfolgreich abgeschlossen: {audit.report_file}")

    return result


if __name__ == "__main__":
    run_v33_master_pipeline()
