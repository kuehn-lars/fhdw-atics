# Aufgabenstellung: Multi-Agent Finanzanalyse mit CrewAI

## Ziel
Entwickelt eine CrewAI-Pipeline, die aus einem Investment-Thema ein strukturiertes Analyseergebnis erzeugt.

Beispielthemen:
- Agriculture Technology US
- Defense Robotics Europe
- AI Infrastructure US
- Water Technology Global

---

## Erlaubte Tools
Für diese Aufgabe können folgende vordefinierte Tools verwendet werden:

- BulkFinancialTool
- InstitutionalNewsScanner

---

## Pflichtbestandteile der Pipeline

Eure Pipeline soll mindestens folgende Rollen bzw. Schritte enthalten:

1. **Discovery**
   - thematische Shortlist erzeugen
   - wirtschaftlichen Link beschreiben
   - Kandidaten verwerfen, wenn die Evidenz zu schwach ist

2. **Quant Audit**
   - Shortlist mit Finanzkennzahlen validieren
   - Bewertung, Qualität und Risiken kommentieren

3. **Macro / Sector View**
   - aktuelle Nachrichtenlage zusammenfassen
   - Nachfrage, Regulierung und Marktstruktur einordnen

4. **Equity Research**
   - pro Titel eine verdichtete Investmentthese formulieren
   - qualitative und quantitative Logik verbinden

5. **Bear Case**
   - Gegen-These je Titel
   - Downside und wichtigste Failure-Mechanik

6. **Portfolio Construction**
   - finale Gewichtung
   - Kelly nur als Orientierung
   - mathematische Validierung mit `StrictMathValidator`

---

## Pflicht-Output

Eine begründete Investment-Entscheidung für das Investment-Thema.

---

## Qualitätskriterien

### Gute Lösung
- klare Rollen für die Agenten
- sinnvolle Tool-Nutzung
- strukturierter Output mit Pydantic
- saubere Trennung von qualitativer und quantitativer Analyse
- nachvollziehbare Portfolio-Logik

### Schlechte Lösung
- Agenten halluzinieren statt Tools zu nutzen
- Zahlen werden erfunden
- allgemeine Marktberichte werden wie harte Company-Events behandelt
- Portfolio ist mathematisch inkonsistent
- Risiko- und Zeithorizont werden ignoriert