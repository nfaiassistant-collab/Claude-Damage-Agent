import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DAMAGE_REPORTS_DIR = Path(os.getenv("DAMAGE_REPORTS_DIR", r"C:\Users\nwfar\Downloads\Damage Reports"))
COMPANY_LOGO_PATH = os.getenv("COMPANY_LOGO_PATH") or None
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", r"C:\Users\nwfar\Desktop\ClaudeCodeTest\reports"))
TEMP_PHOTOS_DIR = Path(__file__).parent / "temp_photos"

# Create directories if they don't exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
