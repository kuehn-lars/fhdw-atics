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
from typing import List, Literal, Optional, Any, Dict
from pydantic import BaseModel, Field, conint, confloat
from dotenv import load_dotenv
from pathlib import Path
from textwrap import shorten

from workshops.crewai_intro.tools import (
    BulkFinancialTool, 
    InstitutionalNewsScanner, 
    KellyCriterionTool, 
    StrictMathValidator
    )

from config.settings import settings
from src.llm_backend.crew_factory import get_crew_llm

load_dotenv()
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"

from crewai import Agent, Crew, Task, LLM, Process
from crewai.tools import BaseTool


# ==========================================================
# Pydantic Models
# ==========================================================

# [ INSERT HERE ... ]


# ==========================================================
# Pipeline (incl. Agents, Tasks, Tools)
# ==========================================================
BACKEND = "nim"  # "nim" (NVIDIA) oder "local" (Ollama)
MODEL = None      # Falls None, wird settings.nvidia_model / settings.local_model genutzt
master_llm = get_crew_llm(backend=BACKEND, model=MODEL)


# --- AGENTS ---
   
# [INSERT AGENTS HERE]



# --- TASKS ---

# [INSERT TASKS HERE]



# --- CREW EXECUTION ---
    
crew = Crew(
            agents=[], # ADD AGENTS HERE
            tasks=[], # ADD TASKS HERE
            process=Process.sequential,
            verbose=True
        )
        
result = crew.kickoff()

