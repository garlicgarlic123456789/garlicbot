import os
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("GEMENI_API_KEY", "dummy")
os.environ.setdefault("train_timetable_api", "dummy-train-timetable-key")
os.environ.setdefault("train_arrivals_api", "dummy-train-arrivals-key")
