import os, sys
from pathlib import Path

if os.environ.get("USE_SPARK_SHIM") == "1":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from spark_shim import spark
