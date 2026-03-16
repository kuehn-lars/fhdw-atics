import subprocess
import os
import sys
import time
import webbrowser

def start_all():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "frontend")

    print("🚀 Starte Fullstack-Anwendung...")

    # 1. Backend starten
    print("📡 Starte Backend (FastAPI)...")
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=root_dir
    )

    # Kurz warten, bis Backend bereit ist
    time.sleep(2)

    # 2. Frontend starten
    print("🎨 Starte Frontend (Next.js)...")
    # Prüfen ob node_modules existieren
    if not os.path.exists(os.path.join(frontend_dir, "node_modules")):
        print("📦 Installiere Frontend-Abhängigkeiten (npm install)...")
        subprocess.run(["npm", "install"], cwd=frontend_dir)

    frontend_process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir
    )

    print("\n✅ Alles gestartet!")
    print("🔗 Backend: http://localhost:8000")
    print("🔗 Frontend: http://localhost:3000")
    
    # Browser öffnen
    time.sleep(3)
    webbrowser.open("http://localhost:3000")

    try:
        # Prozesse am Laufen halten
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Beende Prozesse...")
        backend_process.terminate()
        frontend_process.terminate()

if __name__ == "__main__":
    start_all()
