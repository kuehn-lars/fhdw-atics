# CrewAI Workshop Framework

Willkommen zum Agenten-Workshop! 🤖

In diesem Ordner findest du ein Framework, um deine eigenen KI-Agenten mit **CrewAI** zu bauen. 
Das Besondere: Deine Agenten können unser eigenes RAG-System (Retrieval Augmented Generation) als Werkzeug nutzen, um Fragen zu beantworten!

## 🚀 Setup

Bevor du loslegst, müssen wir sicherstellen, dass die nötigen Bibliotheken installiert sind.

1.  Aktiviere dein Virtual Environment (falls noch nicht geschehen):
    ```bash
    source ../../.venv/bin/activate
    ```

2.  Installiere CrewAI (falls noch nicht installiert):
    ```bash
    pip install crewai
    ```

3.  Stelle sicher, dass du im Root-Verzeichnis `.env` deine Keys (z.B. OpenAI oder Nvidia) eingetragen hast, da CrewAI standardmäßig OpenAI nutzt (oder konfiguriert werden muss).

## 🎮 Wie benutze ich das Framework?

Öffne die Datei `framework.py` in deinem Editor.

### 1. Verstehe den Aufbau
Der Code ist in 3 Teile gegliedert:
*   **Teil 1: Werkzeuge**: Hier ist das `ask_rag` Tool definiert. Das musst du meistens nicht anfassen.
*   **Teil 2: Studenten Area**: **HIER SPIELT DIE MUSIK!** Hier definierst du Agenten und Aufgaben.
*   **Teil 3: Challenge Execution**: Hier legst du fest, welche Fragen (Input) deine Agenten lösen sollen.

### 2. Deine Mission 🕵️‍♀️
Baue eine Crew von Agenten, die eine komplexe Aufgabe löst.

**Beispiele:**
*   Ein **"Support Agent"**, der eine Frage liest, und ein **"Quality Agent"**, der die Antwort prüft.
*   Ein **"Marketing Agent"**, der einen Tweet schreibt basierend auf RAG-Daten.

### 3. Agenten anpassen
Suche nach `Task` und `Agent` Definitionen in `framework.py`.

```python
mein_agent = Agent(
    role='Super Held',
    goal='Rette die Welt',
    backstory='Kam von Krypton...',
    tools=[RagTools.ask_rag] # Gib ihm Tools!
)
```

### 4. Ausführen
Starte das Skript einfach mit Python:

```bash
python workshops/crewai_intro/framework.py
```

## ⚠️ Wichtige Hinweise
*   CrewAI nutzt standardmäßig GPT-4 von OpenAI. Das kostet Geld. Stelle sicher, dass `OPENAI_API_KEY` in der `.env` gesetzt ist.
*   Wende dich bei Fragen an deinen Betreuer!

Viel Erfolg! 🚀
