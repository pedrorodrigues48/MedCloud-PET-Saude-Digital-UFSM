import sys
from pathlib import Path

# A API fica em portal-laboratorio/api (formato exigido pela Vercel).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "portal-laboratorio" / "api"))
