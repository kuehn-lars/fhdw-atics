"""
🛠️ CREWAI TOOLS LIBRARY – FINANCE FOCUSED
"""

# ==========================================================
# IMPORTS & HELPERS
# ==========================================================

import concurrent.futures
import json
import os
import re
import sys
from pathlib import Path
from typing import List, Type, Union

from pydantic import BaseModel, Field

# Root-Pfad sicherstellen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from crewai.tools import BaseTool


SYSTEM_PATH_PREFIXES = ("/etc", "/usr", "/bin", "/sbin", "/var", "/System")
ALLOWED_FILE_EXTENSIONS = {".txt", ".md", ".py", ".json", ".csv", ".yaml", ".yml", ".html", ".xml", ".log", ".cfg", ".ini", ".toml"}
MAX_FILE_TEXT_CHARS = 5000

def _ensure_safe_write_path(file_path: str) -> Path:
    resolved = Path(file_path).expanduser()
    normalized = str(resolved)
    if normalized.startswith(SYSTEM_PATH_PREFIXES):
        raise ValueError(f"Schreiben in '{file_path}' ist nicht erlaubt.")
    return resolved


# ==========================================================
# TOOL SCHEMAS
# ==========================================================

class RagSearchToolInput(BaseModel):
    question: str = Field(..., min_length=3, description="Natürliche Suchfrage für das lokale RAG-System.")

class WikipediaToolInput(BaseModel):
    query: str = Field(..., min_length=2, description="Wikipedia-Suchbegriff.")

class FileReaderToolInput(BaseModel):
    file_path: str = Field(..., description="Relativer oder absoluter Dateipfad.")
    max_chars: int = Field(default=MAX_FILE_TEXT_CHARS, ge=200, le=50000, description="Maximale Rückgabemenge an Zeichen.")

class FileWriterToolInput(BaseModel):
    file_path: str = Field(..., description="Relativer oder absoluter Dateipfad für den Schreibvorgang.")
    content: str = Field(..., description="Vollständiger Dateiinhalt.")

class BulkFinancialToolInput(BaseModel):
    tickers: Union[List[str], str] = Field(..., description="Liste von Aktien-Tickern oder komma-separierte Ticker (z.B. AAPL, MSFT, SAP.DE).")

class InstitutionalNewsScannerInput(BaseModel):
    query: str = Field(..., min_length=2, description="Die Suchanfrage für den News-Deep-Scan (z.B. 'Dronen Sektor EU').")

class KellyCriterionToolInput(BaseModel):
    upside: float = Field(..., description="Geschätztes Aufwärtspotenzial (prozentual oder Faktor).")
    win_prob: float = Field(..., description="Geschätzte Eintrittswahrscheinlichkeit (0.0 bis 1.0).")
    downside: float = Field(..., description="Geschätztes Verlustrisiko (prozentual oder Faktor).")

class StrictMathValidatorInput(BaseModel):
    data: str = Field(
        ...,
        description="JSON-String mit total_capital und portfolio."
    )

class StrictMathValidator(BaseTool):
    """
    Validiert die mathematische Korrektheit der Portfolio-Zusammensetzung.
    Erwartet JSON mit total_capital und portfolio.
    """

    name: str = "strict_math_validator"
    description: str = (
        "Validiert Portfolio-Gewichte, Beträge und Konsistenz der Allokation. "
        "Erwartet JSON mit total_capital und portfolio."
    )
    args_schema: Type[BaseModel] = StrictMathValidatorInput

    def _run(self, data: str) -> str:
        try:
            payload = json.loads(data)
        except json.JSONDecodeError as exc:
            raise ValueError("StrictMathValidator erwartet validen JSON-Input.") from exc

        total_capital = payload.get("total_capital")
        portfolio = payload.get("portfolio")

        if total_capital is None:
            raise ValueError("Feld 'total_capital' fehlt.")
        if not isinstance(total_capital, (int, float)) or total_capital <= 0:
            raise ValueError("'total_capital' muss eine positive Zahl sein.")

        if not isinstance(portfolio, list) or not portfolio:
            raise ValueError("'portfolio' muss eine nicht-leere Liste sein.")

        issues = []
        warnings = []

        weight_sum = 0.0
        amount_sum = 0.0
        seen_symbols = set()

        for i, pos in enumerate(portfolio):
            symbol = pos.get("symbol")
            weight = pos.get("weight")
            amount = pos.get("amount_eur")
            kelly = pos.get("kelly_fraction")

            if not symbol:
                issues.append(f"Position {i}: symbol fehlt.")
            elif symbol in seen_symbols:
                issues.append(f"Doppeltes Symbol gefunden: {symbol}")
            else:
                seen_symbols.add(symbol)

            if not isinstance(weight, (int, float)):
                issues.append(f"Position {symbol or i}: weight fehlt oder ist nicht numerisch.")
                continue

            if not isinstance(amount, (int, float)):
                issues.append(f"Position {symbol or i}: amount_eur fehlt oder ist nicht numerisch.")
                continue

            if not isinstance(kelly, (int, float)):
                warnings.append(f"Position {symbol or i}: kelly_fraction fehlt oder ist nicht numerisch.")
                kelly = None

            if weight < 0:
                issues.append(f"Position {symbol or i}: negatives Gewicht.")
            if amount < 0:
                issues.append(f"Position {symbol or i}: negativer Betrag.")
            if weight > 1:
                warnings.append(f"Position {symbol or i}: Gewicht > 1.0 ({weight}).")
            if kelly is not None and kelly < 0:
                warnings.append(f"Position {symbol or i}: negative Kelly Fraction ({kelly}).")

            weight_sum += float(weight)
            amount_sum += float(amount)

            expected_amount = float(weight) * float(total_capital)
            if abs(expected_amount - float(amount)) > max(1.0, total_capital * 0.001):
                issues.append(
                    f"Position {symbol or i}: amount_eur ({amount}) passt nicht zu weight ({weight}) "
                    f"bei total_capital={total_capital}."
                )

        if abs(weight_sum - 1.0) > 0.0001:
            issues.append(f"Gewichtssumme ist {weight_sum:.6f} statt 1.0.")

        if abs(amount_sum - float(total_capital)) > max(1.0, total_capital * 0.001):
            issues.append(
                f"Betragssumme ist {amount_sum:.2f} statt {float(total_capital):.2f}."
            )

        if len(portfolio) == 1:
            warnings.append("Portfolio besteht nur aus einer Position.")
        if any(pos.get("weight", 0) > 0.5 for pos in portfolio):
            warnings.append("Mindestens eine Position hat mehr als 50% Gewicht.")

        result = {
            "passed": len(issues) == 0,
            "weight_sum": round(weight_sum, 6),
            "amount_sum": round(amount_sum, 2),
            "issues": issues,
            "warnings": warnings,
        }

        return json.dumps(result, indent=2, ensure_ascii=False)


# ==========================================================
# TOOLS
# ==========================================================

class RagSearchTool(BaseTool):
    """Durchsucht den lokalen RAG Vector Store nach relevanten Dokumenten."""

    name: str = "Frage das RAG System"
    description: str = (
        "Durchsucht die lokale Wissensdatenbank. "
        "Input-Feld: question. Liefert strukturierte Treffer als JSON."
    )
    args_schema: Type[BaseModel] = RagSearchToolInput

    def _run(self, question: str) -> str:
        from src.rag_system.orchestration.factory import get_rag_pipeline

        pipeline = get_rag_pipeline()
        docs = pipeline.retrieve(question)
        results = [
            {
                "source": doc.metadata.get("source", "unknown"),
                "metadata": doc.metadata,
                "content": doc.content,
            }
            for doc in docs
        ]
        return json.dumps({"question": question, "results": results}, indent=2, ensure_ascii=False)

class WikipediaTool(BaseTool):
    """Sucht nach Artikeln auf Wikipedia und gibt strukturierte Daten zurück."""

    name: str = "Wikipedia Suche"
    description: str = (
        "Sucht auf Wikipedia nach einem Thema. "
        "Input-Feld: query. Liefert JSON mit Titel, URL und Zusammenfassung."
    )
    args_schema: Type[BaseModel] = WikipediaToolInput

    def _run(self, query: str) -> str:
        try:
            import wikipedia
        except ImportError as exc:
            raise RuntimeError("Paket 'wikipedia' ist nicht installiert.") from exc

        wikipedia.set_lang("de")
        results = wikipedia.search(query, results=5)
        if not results:
            return json.dumps({"query": query, "results": []}, indent=2, ensure_ascii=False)

        try:
            page = wikipedia.page(results[0], auto_suggest=False)
            payload = {
                "query": query,
                "title": page.title,
                "url": page.url,
                "summary": page.summary[:2000],
            }
            return json.dumps(payload, indent=2, ensure_ascii=False)
        except wikipedia.DisambiguationError as exc:
            payload = {
                "query": query,
                "status": "disambiguation",
                "options": exc.options[:10],
            }
            return json.dumps(payload, indent=2, ensure_ascii=False)
        except wikipedia.PageError as exc:
            raise RuntimeError(f"Wikipedia-Seite nicht gefunden für: {query}") from exc

class FileReaderTool(BaseTool):
    """Liest den Inhalt einer lokalen Datei."""

    name: str = "Datei lesen"
    description: str = (
        "Liest den Inhalt einer lokalen Datei. "
        "Input-Felder: file_path, optional max_chars. Liefert JSON mit Dateiinhalt."
    )
    args_schema: Type[BaseModel] = FileReaderToolInput

    def _run(self, file_path: str, max_chars: int = MAX_FILE_TEXT_CHARS) -> str:
        path = Path(file_path)
        if path.suffix.lower() not in ALLOWED_FILE_EXTENSIONS:
            raise ValueError(
                f"Dateityp '{path.suffix}' ist nicht erlaubt. Erlaubt sind: {', '.join(sorted(ALLOWED_FILE_EXTENSIONS))}"
            )
        if not path.exists():
            raise FileNotFoundError(f"Datei nicht gefunden: {file_path}")

        content = path.read_text(encoding="utf-8")
        truncated = content[:max_chars]
        payload = {
            "file_path": str(path),
            "truncated": len(content) > max_chars,
            "char_count": len(truncated),
            "content": truncated,
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

class FileWriterTool(BaseTool):
    """Schreibt Text in eine lokale Datei."""

    name: str = "Datei schreiben"
    description: str = (
        "Schreibt Text in eine Datei. "
        "Input-Felder: file_path, content. Liefert JSON mit Zielpfad und Byte-Anzahl."
    )
    args_schema: Type[BaseModel] = FileWriterToolInput

    def _run(self, file_path: str, content: str) -> str:
        path = _ensure_safe_write_path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        payload = {
            "file_path": str(path),
            "bytes_written": len(content.encode("utf-8")),
        }
        return json.dumps(payload, indent=2, ensure_ascii=False)

class BulkFinancialTool(BaseTool):
    """
    Holt fortgeschrittene Finanzdaten für Ticker-Listen via Finnhub.
    Eingabe: Liste von Tickern.
    Ausgabe: JSON-String mit Metriken wie P/E, P/S, ROE, Margen etc.
    """

    name: str = "bulk_financial_metrics"
    description: str = (
        "Holt fundamentale Finanzkennzahlen für mehrere Aktien gleichzeitig. "
        "Input: Liste von Ticker-Symbolen. Liefert JSON mit detaillierten Metriken."
    )
    args_schema: Type[BaseModel] = BulkFinancialToolInput

    def _fetch_single(self, ticker: str, token: str) -> dict:
        import requests

        t = str(ticker).strip().upper()
        url = f"https://finnhub.io/api/v1/stock/metric?symbol={t}&metric=all&token={token}"
        try:
            resp = requests.get(url, timeout=7)
            if resp.status_code != 200:
                return None
            m = resp.json().get("metric", {})
            if not m:
                return None

            return {
                "symbol": t,
                "pe": m.get("peBasicExclExtraTTM"),
                "ps": m.get("psTTM"),
                "ev_ebitda": m.get("evEbitdaTTM"),
                "beta": m.get("beta"),
                "yield_pct": m.get("dividendYieldIndicatedAnnual"),
                "roe": m.get("roeTTM"),
                "net_margin": m.get("netProfitMarginTTM"),
                "op_margin": m.get("operatingMarginTTM"),
                "debt_to_equity": m.get("totalDebt/totalEquityAnnual") or m.get("longTermDebt/equityAnnual"),
                "current_ratio": m.get("currentRatioQuarterly"),
                "rev_growth": m.get("revenueGrowthTTMYoy"),
                "fcf_growth": m.get("focfCagr5Y") or m.get("epsGrowthTTMYoy"),
            }
        except Exception:
            return None

    def _run(self, tickers: Union[List[str], str]) -> str:
        from concurrent.futures import ThreadPoolExecutor
        from config.settings import settings

        # Robustes Input-Handling (falls Agent String statt Liste sendet)
        if isinstance(tickers, str):
            try:
                # Versuche JSON-Parsing
                tickers = json.loads(tickers)
            except:
                # Fallback: Komma-separierter String
                tickers = [t.strip().strip('"').strip("'") for t in tickers.replace("[","").replace("]","").split(",") if t.strip()]
        
        if not isinstance(tickers, list):
            return json.dumps([{"error": "Invalid input format. Expected list of tickers."}], indent=2)

        token = settings.finnhub_api_key
        if not token:
            return "Error: No Finnhub API Key found."

        print(f"📊 [Quant Data] Lade Daten für {len(tickers)} Ticker parallel...")
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {executor.submit(self._fetch_single, t, token): t for t in tickers}
            for future in concurrent.futures.as_completed(future_to_ticker):
                res = future.result()
                if res:
                    results.append(res)
                else:
                    # Optional: Füge Ticker mit Null-Werten hinzu, damit Agent sieht, dass wir gesucht haben
                    t_name = future_to_ticker[future]
                    results.append({"symbol": t_name.upper(), "note": "No metrics found in Finnhub (check ticker/region)"})

        # Immer eine Liste zurückgeben (auch wenn leer), um Pydantic-Stabilität zu wahren
        return json.dumps(results, indent=2, ensure_ascii=False)

class InstitutionalNewsScanner(BaseTool):
    """
    Scannt aktuelle News-Beiträge zu einer Suchanfrage.
    Eingabe: Suchstring (str).
    Ausgabe: Schlagzeilen mit Datum und Quelle.
    Zusatznutzen: Archiviert die Volltexte in 'news_archive.json'.
    """

    name: str = "institutional_news_scanner"
    description: str = (
        "Tiefer Scan von News-Quellen. Erwartet eine Suchanfrage. "
        "Liefert eine Liste von Schlagzeilen und archiviert Volltexte lokal."
    )
    args_schema: Type[BaseModel] = InstitutionalNewsScannerInput

    def _run(self, query: str) -> str:
        import requests
        from config.settings import settings

        token = settings.newsapi_api_key

        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(base_dir, "outputs")
        os.makedirs(output_dir, exist_ok=True)
        json_archive_path = os.path.join(output_dir, "news_archive.json")

        q_clean = str(query).strip().strip('"').strip("'")
        all_results = []
        print(f"🚀 [Deep Scan] Hole aktuelle Artikel für: '{q_clean}'...")

        if token:
            url = f"https://newsapi.org/v2/everything?q={q_clean}&sortBy=publishedAt&pageSize=100&page=1&apiKey={token}"
            try:
                resp = requests.get(url, timeout=15)
                if resp.status_code == 200:
                    articles = resp.json().get("articles", [])

                    if not articles and len(q_clean.split()) > 3:
                        fallback_q = " ".join(q_clean.split()[:4])
                        print(f"⚠️ 0 Treffer. Versuche Fallback-Suche: '{fallback_q}'...")
                        fallback_url = f"https://newsapi.org/v2/everything?q={fallback_q}&sortBy=publishedAt&pageSize=100&page=1&apiKey={token}"
                        f_resp = requests.get(fallback_url, timeout=15)
                        if f_resp.status_code == 200:
                            articles = f_resp.json().get("articles", [])

                    for art in articles:
                        full_text = (art.get("description") or "") + " " + (art.get("content") or "")
                        all_results.append(
                            {
                                "title": art["title"],
                                "source": art["source"]["name"],
                                "date": art["publishedAt"],
                                "full_text": full_text[:2500],
                                "url": art["url"],
                            }
                        )
                elif resp.status_code == 429:
                    error_msg = "NewsAPI Error 429: RATE_LIMIT_EXCEEDED. Täglich verfügbares Kontingent erschöpft oder zu viele Anfragen in kurzer Zeit. Bitte API-Key prüfen oder später versuchen."
                    print(f"❌ {error_msg}")
                    return error_msg
                else:
                    print(f"NewsAPI Error: {resp.status_code}")
            except Exception as e:
                print(f"Error connecting to NewsAPI: {e}")

        with open(json_archive_path, "w", encoding="utf-8") as jf:
            json.dump(all_results, jf, indent=2, ensure_ascii=False)

        if not all_results:
            return "Keine aktuellen News gefunden oder technischer Fehler (Limit erreicht). Nutze ggf. vorhandenes Wissen oder Wikipedia als Fallback."

        print(f"📁 [Deep Archive] {len(all_results)} Artikel in {json_archive_path} archiviert.")

        summary = []
        for i, r in enumerate(all_results[:20]): # Limit summary to first 20 for prompt space
            summary.append(f"[{i+1}] {r['date']} | {r['title']} ({r['source']})")

        return "\n".join(summary)

class KellyCriterionTool(BaseTool):
    """
    Berechnet die optimale Positionsgröße basierend auf der Kelly-Formel.
    """

    name: str = "kelly_calculator"
    description: str = "Berechnet die optimale Positionsgröße (Kelly-Formel)."
    args_schema: Type[BaseModel] = KellyCriterionToolInput

    def _run(self, upside: float, win_prob: float, downside: float) -> str:
        q = 1.0 - win_prob
        b = (upside / abs(downside)) if downside != 0 else 1.0
        kelly_f = win_prob - (q / b) if b > 0 else 0.05
        return f"KELLY FRACTION: {round(min(1.0, max(0, kelly_f)), 4)}"
