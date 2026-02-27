#!/usr/bin/env python3
"""
🧪 SYSTEMATISCHER TEST ALLER CREWAI TOOLS
==========================================
Testet jedes Tool aus tools.py mit realen Inputs und zeigt den Output.
Externe Netzwerkaufrufe (Wikipedia / Web) werden deterministisch gemockt,
damit der Test offline und stabil läuft.

Aufruf:
    python workshops/crewai_intro/test_tools.py
"""
import os
import sys
import types
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Nur die Tools importieren, die NICHT die RAG-Pipeline benötigen
from workshops.crewai_intro.tools import (
    WikipediaTool, WebScraperTool, FileReaderTool, FileWriterTool,
    MathTool, DateTimeTool, JSONFormatterTool, TextSummarizerTool,
    DirectoryListTool, PythonREPLTool,
)

# Frische Instanzen (ohne RAG-Import)
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

sep = "=" * 70
passed = 0
failed = 0

def test(name, tool, input_str, input_desc=None, expect_in=None, validator=None):
    """Führt einen einzelnen Tool-Test aus."""
    global passed, failed
    print(sep)
    print(f"🧪 {name}")
    print(f"   INPUT:  {input_desc or repr(input_str)}")
    try:
        result = tool._run(input_str)
        print(f"   OUTPUT:")
        for line in result.split("\n")[:6]:
            print(f"   {line[:100]}")
        if expect_in and expect_in not in result:
            print(f"   ❌ FEHLT: Erwartet '{expect_in}' im Output")
            failed += 1
        elif validator and not validator(result):
            print("   ❌ VALIDATOR FEHLGESCHLAGEN")
            failed += 1
        else:
            print(f"   ✅ OK")
            passed += 1
    except Exception as e:
        print(f"   ❌ FEHLER: {e}")
        failed += 1
    print()


def _make_mock_wikipedia_module():
    module = types.ModuleType("wikipedia")

    class DisambiguationError(Exception):
        def __init__(self, options):
            self.options = options

    class PageError(Exception):
        pass

    class FakePage:
        title = "Python (Programmiersprache)"
        url = "https://de.wikipedia.org/wiki/Python_(Programmiersprache)"
        summary = (
            "Python ist eine interpretierte, höherwertige Programmiersprache "
            "mit Fokus auf Lesbarkeit."
        )

    def set_lang(_lang):
        return None

    def search(_query, results=3):
        return ["Python (Programmiersprache)"][:results]

    def page(_title, auto_suggest=False):
        return FakePage()

    module.DisambiguationError = DisambiguationError
    module.PageError = PageError
    module.set_lang = set_lang
    module.search = search
    module.page = page
    return module


def _make_mock_requests_module():
    module = types.ModuleType("requests")

    class FakeResponse:
        text = """
        <html>
          <head>
            <style>body { color: black; }</style>
            <script>console.log("ignore me");</script>
          </head>
          <body>
            <h1>Herman Melville</h1>
            <p>Moby-Dick is a novel by Herman Melville.</p>
          </body>
        </html>
        """

        def raise_for_status(self):
            return None

    def get(_url, headers=None, timeout=10):
        return FakeResponse()

    module.get = get
    return module


# ─── 1. WikipediaTool ────────────────────────────────────────────────────────
with patch.dict(sys.modules, {"wikipedia": _make_mock_wikipedia_module()}):
    test(
        "1. WikipediaTool",
        wikipedia_tool,
        "Python Programmiersprache",
        expect_in="Python",
    )

# ─── 2. WebScraperTool ───────────────────────────────────────────────────────
with patch.dict(sys.modules, {"requests": _make_mock_requests_module()}):
    test(
        "2. WebScraperTool",
        web_scraper_tool,
        "https://httpbin.org/html",
        expect_in="Herman Melville",
    )

# ─── 3. FileReaderTool ───────────────────────────────────────────────────────
test(
    "3. FileReaderTool – existierende Datei",
    file_reader_tool,
    "workshops/crewai_intro/tools.py",
    expect_in="CREWAI TOOLS LIBRARY",
)

test(
    "3b. FileReaderTool – nicht existierende Datei",
    file_reader_tool,
    "gibt_es_nicht.txt",
    expect_in="nicht gefunden",
)

test(
    "3c. FileReaderTool – verbotener Dateityp",
    file_reader_tool,
    "foto.jpg",
    expect_in="nicht erlaubt",
)

# ─── 4. FileWriterTool ──────────────────────────────────────────────────────
test_output_path = Path("workshops/crewai_intro/.tmp_crewai_test.txt")
test_output_content = "Dies ist ein automatischer Test vom FileWriterTool."
if test_output_path.exists():
    test_output_path.unlink()

test(
    "4. FileWriterTool – Datei schreiben",
    file_writer_tool,
    f"{test_output_path}|||{test_output_content}",
    expect_in="erfolgreich",
    validator=lambda _: test_output_path.exists()
    and test_output_path.read_text(encoding="utf-8") == test_output_content,
)

test(
    "4b. FileWriterTool – Sicherheitscheck",
    file_writer_tool,
    "/etc/passwd|||hacked",
    expect_in="nicht erlaubt",
)

test(
    "4c. FileWriterTool – falsches Format",
    file_writer_tool,
    "kein Trennzeichen hier",
    expect_in="Falsches Format",
)

# ─── 5. MathTool ─────────────────────────────────────────────────────────────
test(
    "5. MathTool – Grundrechenarten",
    math_tool,
    "(15 * 3) + 42 / 7",
    expect_in="51.0",
)

test(
    "5b. MathTool – Potenz",
    math_tool,
    "2 ** 10",
    expect_in="1024",
)

test(
    "5c. MathTool – Division durch Null",
    math_tool,
    "1 / 0",
    expect_in="Division durch Null",
)

test(
    "5d. MathTool – Ungültiger Ausdruck",
    math_tool,
    "import os",
    expect_in="Ungültiger Ausdruck",
)

# ─── 6. DateTimeTool ─────────────────────────────────────────────────────────
test(
    "6. DateTimeTool",
    datetime_tool,
    "",
    input_desc="(kein Input nötig)",
    expect_in="Heute ist",
)

# ─── 7. JSONFormatterTool ────────────────────────────────────────────────────
test(
    "7. JSONFormatterTool – JSON String",
    json_formatter_tool,
    '{"name": "Max", "alter": 21, "fach": "Informatik"}',
    expect_in='"name": "Max"',
)

test(
    "7b. JSONFormatterTool – key=value Format",
    json_formatter_tool,
    "name=Max\nalter=21\nfach=Informatik",
    expect_in='"name"',
)

# ─── 8. TextSummarizerTool ──────────────────────────────────────────────────
long_text = (
    "Machine Learning ist ein Teilgebiet der Künstlichen Intelligenz. "
    "Es ermöglicht Computern, aus Daten zu lernen, ohne explizit programmiert zu werden. "
    "Dabei werden statistische Methoden eingesetzt, um Muster in großen Datenmengen zu erkennen. "
    "Deep Learning ist eine spezielle Form des Machine Learning, die neuronale Netze verwendet."
)
test(
    "8. TextSummarizerTool – Text kürzen auf 100 Zeichen",
    text_summarizer_tool,
    f"100|||{long_text}",
    input_desc=f'"100|||{long_text[:50]}..."',
    expect_in="gekürzt",
)

test(
    "8b. TextSummarizerTool – kurzer Text (kein Kürzen nötig)",
    text_summarizer_tool,
    "Kurzer Satz.",
    expect_in="bereits kurz genug",
)

# ─── 9. DirectoryListTool ───────────────────────────────────────────────────
test(
    "9. DirectoryListTool – existierendes Verzeichnis",
    directory_list_tool,
    "workshops/crewai_intro",
    expect_in="tools.py",
)

test(
    "9b. DirectoryListTool – nicht existierendes Verzeichnis",
    directory_list_tool,
    "gibt_es_nicht/",
    expect_in="nicht gefunden",
)

# ─── 10. PythonREPLTool ─────────────────────────────────────────────────────
test(
    "10. PythonREPLTool – Berechnung",
    python_repl_tool,
    'zahlen = [1, 2, 3, 4, 5]\nprint(f"Summe: {sum(zahlen)}")\nprint(f"Mittelwert: {sum(zahlen)/len(zahlen)}")',
    input_desc='zahlen = [1,2,3,4,5]; print(Summe, Mittelwert)',
    expect_in="Summe: 15",
)

test(
    "10b. PythonREPLTool – Sicherheitscheck",
    python_repl_tool,
    "import os\nos.system('ls')",
    expect_in="nicht erlaubt",
)

test(
    "10c. PythonREPLTool – math Modul",
    python_repl_tool,
    "print(f\"Pi = {math.pi:.4f}\")\nprint(f\"sqrt(144) = {math.sqrt(144)}\")",
    input_desc="math.pi, math.sqrt(144)",
    expect_in="3.1416",
)

if test_output_path.exists():
    test_output_path.unlink()

# ─── ZUSAMMENFASSUNG ─────────────────────────────────────────────────────────
print(sep)
print(f"\n📊 ERGEBNIS: {passed} bestanden, {failed} fehlgeschlagen")
if failed == 0:
    print("✅ ALLE TESTS BESTANDEN!")
else:
    print(f"❌ {failed} Tests fehlgeschlagen!")
    sys.exit(1)
