# Original Bug Squad reproduction with synthetic inputs.
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "upstream"
sys.path.insert(0, str(SOURCE))

import schedule

job = schedule.every().minute
job.do(lambda current_job: None, job)
text = repr(job)
assert isinstance(text, str) and len(text) < 10000
