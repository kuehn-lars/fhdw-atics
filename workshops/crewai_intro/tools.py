"""
🛠️ CREWAI TOOLS LIBRARY
========================
Zentrale Sammlung von echten, funktionalen Tools für CrewAI-Agenten.

Alle Tools erben von `crewai.tools.BaseTool` und können direkt in 
Agent-Konfigurationen verwendet werden:

    from workshops.crewai_intro.tools import wikipedia_tool, math_tool
    
    agent = Agent(
        role="Researcher",
        tools=[wikipedia_tool, math_tool],
        ...
    )

Verfügbare Tools:
    1.  RagSearchTool        – Sucht im lokalen RAG Vector Store
    2.  WikipediaTool        – Sucht auf Wikipedia (deutsch)
    3.  WebScraperTool       – Scrapt den Inhalt einer URL
    4.  FileReaderTool       – Liest lokale Dateien
    5.  FileWriterTool       – Schreibt Text in Dateien
    6.  MathTool             – Berechnet mathematische Ausdrücke
    7.  DateTimeTool         – Gibt aktuelles Datum und Uhrzeit zurück
    8.  JSONFormatterTool    – Formatiert Text/Dict als JSON
    9.  TextSummarizerTool   – Kürzt langen Text auf n Zeichen
    10. DirectoryListTool    – Listet Dateien in einem Verzeichnis
    11. PythonREPLTool       – Führt Python-Code aus (Sandbox)
    12. LiveStockDataTool    – Holt aktuelle Aktienkurse (Stooq)
    13. CurrentNewsTool      – Holt aktuelle News zu Ticker/Thema
    14. VisualizationTool    – Erstellt einfache Visualisierungen als PNG
"""

import csv
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile

# Root-Pfad sicherstellen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from crewai.tools import BaseTool


# =============================================================================
# 1. RAG SEARCH TOOL
# =============================================================================

class RagSearchTool(BaseTool):
    """Durchsucht den lokalen RAG Vector Store nach relevanten Dokumenten."""
    name: str = "Frage das RAG System"
    description: str = (
        "Durchsucht die lokale Wissensdatenbank (Vector Store) nach relevanten "
        "Informationen. Gib eine Suchfrage als String ein."
    )

    def _run(self, question: str) -> str:
        try:
            from src.rag_system.orchestration.factory import get_rag_pipeline
            pipeline = get_rag_pipeline()
            docs = pipeline.retrieve(question)
            if not docs:
                return "Keine relevanten Dokumente im Vector Store gefunden."
            context = "\n\n".join([
                f"📄 Quelle: {doc.metadata.get('source', 'Unbekannt')}\n{doc.content}"
                for doc in docs
            ])
            return f"Ergebnisse aus dem RAG System:\n\n{context}"
        except Exception as e:
            return f"Fehler beim RAG-Zugriff: {e}"


# =============================================================================
# 2. WIKIPEDIA TOOL
# =============================================================================

class WikipediaTool(BaseTool):
    """Sucht nach Artikeln auf Wikipedia und gibt eine Zusammenfassung zurück."""
    name: str = "Wikipedia Suche"
    description: str = (
        "Sucht auf Wikipedia nach einem Thema und gibt eine Zusammenfassung zurück. "
        "Eingabe: ein Suchbegriff als String (z.B. 'Künstliche Intelligenz')."
    )

    def _run(self, query: str) -> str:
        try:
            import wikipedia
            wikipedia.set_lang("de")
            results = wikipedia.search(query, results=3)
            if not results:
                return f"Keine Wikipedia-Artikel gefunden für: '{query}'"

            try:
                page = wikipedia.page(results[0], auto_suggest=False)
                summary = page.summary[:2000]
                return (
                    f"📖 Wikipedia: {page.title}\n"
                    f"🔗 {page.url}\n\n"
                    f"{summary}"
                )
            except wikipedia.DisambiguationError as e:
                options = ", ".join(e.options[:5])
                return f"Mehrdeutiger Begriff. Mögliche Artikel: {options}"
            except wikipedia.PageError:
                return f"Wikipedia-Seite nicht gefunden für: '{results[0]}'"
        except ImportError:
            return "Fehler: 'wikipedia' Paket nicht installiert. Bitte `pip install wikipedia` ausführen."
        except Exception as e:
            return f"Wikipedia-Fehler: {e}"


# =============================================================================
# 3. WEB SCRAPER TOOL
# =============================================================================

class WebScraperTool(BaseTool):
    """Scrapt den Textinhalt einer Webseite."""
    name: str = "Webseite lesen"
    description: str = (
        "Liest den Textinhalt einer Webseite. "
        "Eingabe: eine vollständige URL als String (z.B. 'https://example.com')."
    )

    def _run(self, url: str) -> str:
        try:
            import requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) CrewAI-Agent/1.0"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # Einfacher HTML-zu-Text Parser (kein BeautifulSoup nötig)
            text = response.text
            # Script und Style Tags entfernen
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
            # HTML Tags entfernen
            text = re.sub(r'<[^>]+>', ' ', text)
            # Mehrfache Whitespaces bereinigen
            text = re.sub(r'\s+', ' ', text).strip()
            # Auf 3000 Zeichen begrenzen
            if len(text) > 3000:
                text = text[:3000] + "... [gekürzt]"

            return f"🌐 Inhalt von {url}:\n\n{text}"
        except ImportError:
            return "Fehler: 'requests' Paket nicht installiert."
        except Exception as e:
            return f"Fehler beim Scrapen von {url}: {e}"


# =============================================================================
# 4. FILE READER TOOL
# =============================================================================

class FileReaderTool(BaseTool):
    """Liest den Inhalt einer lokalen Datei."""
    name: str = "Datei lesen"
    description: str = (
        "Liest den Inhalt einer lokalen Datei und gibt ihn zurück. "
        "Eingabe: ein Dateipfad als String (relativ oder absolut)."
    )

    def _run(self, file_path: str) -> str:
        try:
            # Sicherheitscheck: Nur bestimmte Dateitypen erlauben
            allowed_extensions = {'.txt', '.md', '.py', '.json', '.csv', '.yaml', '.yml', '.html', '.xml', '.log', '.cfg', '.ini', '.toml'}
            _, ext = os.path.splitext(file_path)
            if ext.lower() not in allowed_extensions:
                return f"⚠️ Dateityp '{ext}' nicht erlaubt. Erlaubte Typen: {', '.join(sorted(allowed_extensions))}"

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if len(content) > 5000:
                content = content[:5000] + f"\n\n... [Datei gekürzt, insgesamt {len(content)} Zeichen]"

            return f"📄 Inhalt von '{file_path}':\n\n{content}"
        except FileNotFoundError:
            return f"❌ Datei nicht gefunden: '{file_path}'"
        except Exception as e:
            return f"Fehler beim Lesen: {e}"


# =============================================================================
# 5. FILE WRITER TOOL
# =============================================================================

class FileWriterTool(BaseTool):
    """Schreibt Text in eine lokale Datei."""
    name: str = "Datei schreiben"
    description: str = (
        "Schreibt Text in eine Datei. "
        "Eingabe: ein String im Format 'DATEIPFAD|||INHALT' "
        "(z.B. 'output.txt|||Dies ist der Inhalt')."
    )

    def _run(self, input_str: str) -> str:
        try:
            if "|||" not in input_str:
                return "⚠️ Falsches Format! Verwende: 'dateipfad|||inhalt'"

            file_path, content = input_str.split("|||", 1)
            file_path = file_path.strip()

            # Sicherheitscheck
            dangerous = ['/etc', '/usr', '/bin', '/sbin', '/var', '/System']
            if any(file_path.startswith(d) for d in dangerous):
                return f"⚠️ Schreiben in '{file_path}' ist nicht erlaubt (Sicherheitsrichtlinie)."

            os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return f"✅ Datei erfolgreich geschrieben: '{file_path}' ({len(content)} Zeichen)"
        except Exception as e:
            return f"Fehler beim Schreiben: {e}"


# =============================================================================
# 6. MATH TOOL
# =============================================================================

class MathTool(BaseTool):
    """Berechnet mathematische Ausdrücke sicher."""
    name: str = "Taschenrechner"
    description: str = (
        "Berechnet einen mathematischen Ausdruck und gibt das Ergebnis zurück. "
        "Eingabe: ein mathematischer Ausdruck als String (z.B. '(15 * 3) + 42 / 7')."
    )

    def _run(self, expression: str) -> str:
        try:
            # Nur sichere mathematische Zeichen erlauben
            allowed = set('0123456789+-*/.() %,eE')
            clean = expression.replace(',', '.').strip()
            if not all(c in allowed or c.isspace() for c in clean):
                return f"⚠️ Ungültiger Ausdruck: '{expression}'. Nur Zahlen und Operatoren (+, -, *, /, **, %) erlaubt."

            result = eval(clean, {"__builtins__": {}}, {})
            return f"🧮 {expression} = {result}"
        except ZeroDivisionError:
            return "⚠️ Division durch Null!"
        except Exception as e:
            return f"Rechenfehler: {e}"


# =============================================================================
# 7. DATETIME TOOL
# =============================================================================

class DateTimeTool(BaseTool):
    """Gibt das aktuelle Datum und die Uhrzeit zurück."""
    name: str = "Datum und Uhrzeit"
    description: str = (
        "Gibt das aktuelle Datum, die Uhrzeit und den Wochentag zurück. "
        "Keine Eingabe nötig – einfach aufrufen."
    )

    def _run(self, _input: str = "") -> str:
        now = datetime.datetime.now()
        wochentage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        tag = wochentage[now.weekday()]
        return (
            f"📅 Heute ist {tag}, der {now.strftime('%d.%m.%Y')}\n"
            f"🕐 Uhrzeit: {now.strftime('%H:%M:%S')}\n"
            f"📆 Kalenderwoche: {now.isocalendar()[1]}"
        )


# =============================================================================
# 8. JSON FORMATTER TOOL
# =============================================================================

class JSONFormatterTool(BaseTool):
    """Formatiert einen Text oder ein Dict als hübsches JSON."""
    name: str = "JSON Formatierer"
    description: str = (
        "Formatiert einen gegebenen Text als valides, hübsch formatiertes JSON. "
        "Eingabe: ein JSON-String oder ein key=value Format."
    )

    def _run(self, text: str) -> str:
        try:
            # Versuche, den Text als JSON zu parsen
            data = json.loads(text)
            return json.dumps(data, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            # Versuche key=value Paare zu parsen
            try:
                pairs = {}
                for line in text.strip().split('\n'):
                    if '=' in line:
                        key, val = line.split('=', 1)
                        pairs[key.strip()] = val.strip()
                    elif ':' in line:
                        key, val = line.split(':', 1)
                        pairs[key.strip()] = val.strip()
                if pairs:
                    return json.dumps(pairs, indent=2, ensure_ascii=False)
            except Exception:
                pass
            return f"⚠️ Konnte den Text nicht als JSON formatieren:\n{text}"


# =============================================================================
# 9. TEXT SUMMARIZER TOOL
# =============================================================================

class TextSummarizerTool(BaseTool):
    """Kürzt einen langen Text auf eine bestimmte Zeichenanzahl."""
    name: str = "Text kürzen"
    description: str = (
        "Kürzt einen langen Text auf eine bestimmte Länge. "
        "Eingabe: der zu kürzende Text. Optionale Länge am Anfang im Format '500|||Text hier...'"
    )

    def _run(self, text: str) -> str:
        max_chars = 500
        if "|||" in text:
            parts = text.split("|||", 1)
            try:
                max_chars = int(parts[0].strip())
                text = parts[1]
            except ValueError:
                pass

        if len(text) <= max_chars:
            return f"✅ Text ist bereits kurz genug ({len(text)} Zeichen):\n{text}"

        # An Satzgrenze kürzen
        truncated = text[:max_chars]
        last_period = truncated.rfind('.')
        if last_period > max_chars // 2:
            truncated = truncated[:last_period + 1]

        return (
            f"✂️ Text gekürzt von {len(text)} auf {len(truncated)} Zeichen:\n\n"
            f"{truncated}"
        )


# =============================================================================
# 10. DIRECTORY LIST TOOL
# =============================================================================

class DirectoryListTool(BaseTool):
    """Listet alle Dateien in einem Verzeichnis auf."""
    name: str = "Verzeichnis auflisten"
    description: str = (
        "Listet alle Dateien und Ordner in einem Verzeichnis auf. "
        "Eingabe: ein Verzeichnispfad als String."
    )

    def _run(self, directory: str) -> str:
        try:
            if not os.path.isdir(directory):
                return f"❌ Verzeichnis nicht gefunden: '{directory}'"

            entries = sorted(os.listdir(directory))
            result_lines = []
            for entry in entries[:50]:  # Max 50 Einträge
                full_path = os.path.join(directory, entry)
                if os.path.isdir(full_path):
                    result_lines.append(f"📁 {entry}/")
                else:
                    size = os.path.getsize(full_path)
                    if size > 1024 * 1024:
                        size_str = f"{size / (1024*1024):.1f} MB"
                    elif size > 1024:
                        size_str = f"{size / 1024:.1f} KB"
                    else:
                        size_str = f"{size} B"
                    result_lines.append(f"📄 {entry} ({size_str})")

            total = len(entries)
            header = f"📂 Inhalt von '{directory}' ({total} Einträge):\n"
            if total > 50:
                header += f"⚠️ Zeige nur die ersten 50 von {total} Einträgen.\n"

            return header + "\n".join(result_lines)
        except PermissionError:
            return f"⚠️ Keine Berechtigung für: '{directory}'"
        except Exception as e:
            return f"Fehler: {e}"


# =============================================================================
# 11. PYTHON REPL TOOL
# =============================================================================

class PythonREPLTool(BaseTool):
    """Führt Python-Code in einer eingeschränkten Sandbox aus."""
    name: str = "Python Ausführen"
    description: str = (
        "Führt Python-Code aus und gibt das Ergebnis zurück. "
        "Eingabe: Python-Code als String. "
        "Verfügbar: math, statistics, json, datetime, re, collections, itertools."
    )

    def _run(self, code: str) -> str:
        import io
        import math
        import statistics
        import collections
        import itertools

        # Gefährliche Imports/Funktionen blockieren
        forbidden = ['import os', 'import sys', 'import subprocess', '__import__',
                      'open(', 'exec(', 'eval(', 'compile(', 'globals(', 'locals(',
                      'import shutil', 'import socket', 'import http']
        for f in forbidden:
            if f in code:
                return f"⚠️ '{f}' ist in der Sandbox nicht erlaubt."

        # Sandbox-Globals
        safe_globals = {
            "__builtins__": {
                "print": print, "len": len, "range": range, "int": int,
                "float": float, "str": str, "list": list, "dict": dict,
                "tuple": tuple, "set": set, "bool": bool, "abs": abs,
                "max": max, "min": min, "sum": sum, "sorted": sorted,
                "round": round, "enumerate": enumerate, "zip": zip,
                "map": map, "filter": filter, "type": type, "isinstance": isinstance,
                "True": True, "False": False, "None": None,
            },
            "math": math,
            "statistics": statistics,
            "json": json,
            "datetime": datetime,
            "re": re,
            "collections": collections,
            "itertools": itertools,
        }

        # stdout umleiten
        old_stdout = sys.stdout
        sys.stdout = captured = io.StringIO()

        try:
            exec(code, safe_globals)
            output = captured.getvalue()
            if not output:
                output = "(kein Output)"
            return f"🐍 Python Output:\n\n{output[:3000]}"
        except Exception as e:
            return f"❌ Python Fehler:\n{type(e).__name__}: {e}"
        finally:
            sys.stdout = old_stdout


# =============================================================================
# 12. LIVE STOCK DATA TOOL
# =============================================================================

class LiveStockDataTool(BaseTool):
    """Holt aktuelle Aktiendaten fuer eine Liste von Tickersymbolen."""
    name: str = "Live Aktien Daten"
    description: str = (
        "Holt aktuelle Aktienkurse ueber Stooq. "
        "Eingabe: kommaseparierte Ticker als String (z.B. 'MSFT,NVDA,SAP')."
    )

    def _run(self, tickers: str) -> str:
        try:
            import requests
        except ImportError:
            return "Fehler: 'requests' Paket nicht installiert."

        try:
            now_iso = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
            ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
            if not ticker_list:
                return "⚠️ Keine Ticker uebergeben. Format: 'MSFT,NVDA,SAP'"

            def symbol_candidates(ticker: str):
                base = ticker.upper()
                candidates = [base]
                if "." not in base:
                    candidates.extend([f"{base}.US", f"{base}.DE", f"{base}.SW", f"{base}.IT"])
                dedup = []
                for symbol in candidates:
                    if symbol not in dedup:
                        dedup.append(symbol)
                return dedup

            quotes = []
            errors = []

            for ticker in ticker_list:
                found = None
                for symbol in symbol_candidates(ticker):
                    try:
                        url = f"https://stooq.com/q/l/?s={symbol.lower()}&f=sd2t2ohlcvn&e=csv"
                        response = requests.get(url, timeout=8)
                        response.raise_for_status()
                        reader = csv.DictReader(response.text.splitlines())
                        row = next(reader, None)
                        if not row:
                            continue

                        close_str = str(row.get("Close", "")).strip()
                        open_str = str(row.get("Open", "")).strip()
                        if close_str in {"", "N/D"}:
                            continue

                        close_value = float(close_str)
                        change_pct = 0.0
                        if open_str not in {"", "N/D"}:
                            open_value = float(open_str)
                            if open_value > 0:
                                change_pct = ((close_value / open_value) - 1.0) * 100.0

                        found = {
                            "ticker": ticker,
                            "symbol_used": symbol,
                            "last_price": close_value,
                            "change_pct_1d": round(change_pct, 2),
                            "source": "stooq",
                            "as_of_utc": now_iso,
                        }
                        break
                    except Exception:
                        continue

                if found:
                    quotes.append(found)
                else:
                    errors.append(f"{ticker}: kein Live-Quote gefunden")

            payload = {"as_of_utc": now_iso, "quotes": quotes, "errors": errors}
            return json.dumps(payload, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"Fehler beim Abrufen von Live-Aktiendaten: {e}"


# =============================================================================
# 13. CURRENT NEWS TOOL
# =============================================================================

class CurrentNewsTool(BaseTool):
    """Sucht aktuelle Nachrichten (RSS) zu einem Thema oder Ticker."""
    name: str = "Aktuelle News suchen"
    description: str = (
        "Sucht aktuelle News via Google News RSS. "
        "Eingabe: Suchbegriff als String (z.B. 'NVIDIA Aktie')."
    )

    def _run(self, query: str) -> str:
        try:
            import requests
        except ImportError:
            return "Fehler: 'requests' Paket nicht installiert."

        try:
            from urllib.parse import quote_plus

            q = (query or "").strip()
            if not q:
                return "⚠️ Kein Suchbegriff uebergeben."

            url = f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=de&gl=DE&ceid=DE:de"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            xml = response.text

            items = re.findall(r"<item>(.*?)</item>", xml, flags=re.DOTALL | re.IGNORECASE)
            if not items:
                return f"Keine News gefunden fuer: {q}"

            out = []
            for item in items[:5]:
                title_match = re.search(r"<title>(.*?)</title>", item, flags=re.DOTALL | re.IGNORECASE)
                link_match = re.search(r"<link>(.*?)</link>", item, flags=re.DOTALL | re.IGNORECASE)
                pub_match = re.search(r"<pubDate>(.*?)</pubDate>", item, flags=re.DOTALL | re.IGNORECASE)

                title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else "(ohne Titel)"
                link = link_match.group(1).strip() if link_match else ""
                pub = pub_match.group(1).strip() if pub_match else "unbekannt"

                out.append({"title": title, "link": link, "published": pub})

            payload = {
                "query": q,
                "source": "google_news_rss",
                "items": out,
            }
            return json.dumps(payload, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"Fehler bei News-Suche: {e}"


# =============================================================================
# 14. VISUALIZATION TOOL
# =============================================================================

class VisualizationTool(BaseTool):
    """Erstellt einfache Charts (bar/line/pie) aus JSON-Daten."""
    name: str = "Visualisierung erstellen"
    description: str = (
        "Erstellt ein PNG-Chart aus JSON-Eingaben. "
        "Eingabe: JSON-String mit chart_type ('bar'|'line'|'pie'), "
        "labels (Liste), values (Liste), title (optional), output_path (optional)."
    )

    def _run(self, payload: str) -> str:
        try:
            data = json.loads(payload)
        except Exception as e:
            return f"⚠️ Ungueltiges JSON fuer Visualization Tool: {e}"

        chart_type = str(data.get("chart_type", "bar")).lower()
        labels = data.get("labels", [])
        values = data.get("values", [])
        title = data.get("title", "Visualisierung")
        output_path = data.get(
            "output_path",
            "workshops/crewai_intro/outputs/visualization_chart.png",
        )

        if not isinstance(labels, list) or not isinstance(values, list):
            return "⚠️ 'labels' und 'values' muessen Listen sein."
        if not labels or len(labels) != len(values):
            return "⚠️ 'labels' und 'values' muessen gleich lang und nicht leer sein."

        numeric_values = []
        for value in values:
            try:
                numeric_values.append(float(value))
            except Exception:
                return f"⚠️ Ungueltiger Zahlenwert in values: {value}"

        dangerous = ["/etc", "/usr", "/bin", "/sbin", "/var", "/System"]
        if any(str(output_path).startswith(d) for d in dangerous):
            return f"⚠️ Schreiben in '{output_path}' ist nicht erlaubt."

        try:
            os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "matplotlib-cache"))
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            return "Fehler: 'matplotlib' Paket nicht installiert."

        try:
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            fig, ax = plt.subplots(figsize=(9, 4))

            if chart_type == "line":
                ax.plot(labels, numeric_values, marker="o", color="#2E86AB")
                ax.set_ylabel("Wert")
            elif chart_type == "pie":
                ax.clear()
                ax.pie(numeric_values, labels=labels, autopct="%1.1f%%", startangle=100)
            else:
                ax.bar(labels, numeric_values, color="#2E86AB")
                ax.set_ylabel("Wert")

            ax.set_title(title)
            if chart_type in {"bar", "line"}:
                ax.set_ylim(bottom=0)
                ax.grid(axis="y", linestyle="--", alpha=0.3)
            fig.tight_layout()
            fig.savefig(output_path, dpi=160)
            plt.close(fig)
            return f"✅ Visualisierung gespeichert: '{output_path}'"
        except Exception as e:
            return f"Fehler beim Erstellen des Charts: {e}"


# =============================================================================
# 📦 TOOL-INSTANZEN (bereit zur Verwendung)
# =============================================================================

# Jedes Tool einmal instanziieren – diese Variablen können direkt importiert werden.
rag_search_tool = RagSearchTool()
wikipedia_tool = WikipediaTool()
web_scraper_tool = WebScraperTool()
file_reader_tool = FileReaderTool()
file_writer_tool = FileWriterTool()
math_tool = MathTool()
datetime_tool = DateTimeTool()
json_formatter_tool = JSONFormatterTool()
text_summarizer_tool = TextSummarizerTool()
directory_list_tool = DirectoryListTool()
python_repl_tool = PythonREPLTool()
live_stock_data_tool = LiveStockDataTool()
current_news_tool = CurrentNewsTool()
visualization_tool = VisualizationTool()
# Rueckwaertskompatibler Alias
portfolio_plot_tool = visualization_tool

# Alle Tools in einer Liste (praktisch für Agenten, die "alles können" sollen)
ALL_TOOLS = [
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
    live_stock_data_tool,
    current_news_tool,
    visualization_tool,
]

# Gruppierte Tool-Sets für verschiedene Anwendungsfälle
RESEARCH_TOOLS = [rag_search_tool, wikipedia_tool, web_scraper_tool, live_stock_data_tool, current_news_tool]
FILE_TOOLS = [file_reader_tool, file_writer_tool, directory_list_tool]
UTILITY_TOOLS = [math_tool, datetime_tool, json_formatter_tool, text_summarizer_tool, visualization_tool]
DEVELOPER_TOOLS = [python_repl_tool, file_reader_tool, file_writer_tool]
