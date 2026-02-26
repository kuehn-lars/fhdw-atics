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
    11. ShellCommandTool     – Führt sichere Shell-Befehle aus
    12. PythonREPLTool       – Führt Python-Code aus (Sandbox)
"""

import datetime
import json
import os
import re
import subprocess
import sys
from typing import ClassVar, Set

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
# 11. SHELL COMMAND TOOL
# =============================================================================

class ShellCommandTool(BaseTool):
    """Führt sichere Shell-Befehle aus und gibt das Ergebnis zurück."""
    name: str = "Shell Befehl"
    description: str = (
        "Führt einen Shell-Befehl aus und gibt stdout zurück. "
        "Eingabe: der auszuführende Befehl als String. "
        "⚠️ Nur sichere, nicht-destruktive Befehle sind erlaubt (ls, cat, echo, wc, head, tail, grep, find, date, whoami, pwd, uname, df, du)."
    )

    # Whitelist sicherer Befehle
    SAFE_COMMANDS: ClassVar[Set[str]] = {
        'ls', 'cat', 'echo', 'wc', 'head', 'tail', 'grep', 'find',
        'date', 'whoami', 'pwd', 'uname', 'df', 'du', 'sort', 'uniq',
        'tr', 'cut', 'awk', 'sed', 'which', 'env', 'printenv',
        'python3', 'python', 'pip', 'git'
    }

    def _run(self, command: str) -> str:
        # Sicherheitscheck: Erstes Wort muss in der Whitelist sein
        first_word = command.strip().split()[0] if command.strip() else ""
        if first_word not in self.SAFE_COMMANDS:
            return (
                f"⚠️ Befehl '{first_word}' ist nicht erlaubt.\n"
                f"Erlaubte Befehle: {', '.join(sorted(self.SAFE_COMMANDS))}"
            )

        # Gefährliche Patterns blocken
        dangerous_patterns = ['rm ', 'rm\t', 'rmdir', '> /', 'sudo', 'chmod', 'chown', 'mkfs', 'dd ']
        if any(p in command for p in dangerous_patterns):
            return "⚠️ Dieser Befehl enthält potenziell gefährliche Operationen und wird blockiert."

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=15,
                cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
            )
            output = result.stdout[:3000] if result.stdout else ""
            errors = result.stderr[:500] if result.stderr else ""

            response = f"💻 $ {command}\n"
            if output:
                response += f"\n{output}"
            if errors:
                response += f"\n⚠️ stderr:\n{errors}"
            if result.returncode != 0:
                response += f"\n❌ Exit Code: {result.returncode}"

            return response
        except subprocess.TimeoutExpired:
            return f"⏰ Timeout: Befehl '{command}' hat länger als 15 Sekunden gedauert."
        except Exception as e:
            return f"Fehler: {e}"


# =============================================================================
# 12. PYTHON REPL TOOL
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
shell_command_tool = ShellCommandTool()
python_repl_tool = PythonREPLTool()

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
    shell_command_tool,
    python_repl_tool,
]

# Gruppierte Tool-Sets für verschiedene Anwendungsfälle
RESEARCH_TOOLS = [rag_search_tool, wikipedia_tool, web_scraper_tool]
FILE_TOOLS = [file_reader_tool, file_writer_tool, directory_list_tool]
UTILITY_TOOLS = [math_tool, datetime_tool, json_formatter_tool, text_summarizer_tool]
DEVELOPER_TOOLS = [shell_command_tool, python_repl_tool, file_reader_tool, file_writer_tool]
