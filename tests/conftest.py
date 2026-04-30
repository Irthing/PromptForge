"""pytest configuration for PromptForge tests."""
import sys
from pathlib import Path

# Add project root to Python path so tests can import from src/
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
