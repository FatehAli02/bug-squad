# Original Bug Squad reproduction with synthetic inputs.
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "upstream"
sys.path.insert(0, str(SOURCE))

import schedule

job = schedule.every().hour.at("17:43").do(lambda: None)
assert (job.at_time.minute, job.at_time.second) == (17, 43), job.at_time
