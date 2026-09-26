# Original Bug Squad reproduction with synthetic inputs.
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "upstream"
sys.path.insert(0, str(SOURCE))

import datetime
from unittest.mock import patch
import schedule

RealDateTime = datetime.datetime
class Clock(RealDateTime):
    current = RealDateTime(2022, 6, 10, 20, 0)
    @classmethod
    def now(cls, tz=None):
        return cls.current

with patch.object(schedule.datetime, "datetime", Clock):
    job = schedule.every().day.at("21:30").do(lambda: None)
    Clock.current = RealDateTime(2022, 6, 11, 2, 0)
    job.run()
    assert job.next_run == RealDateTime(2022, 6, 11, 21, 30), job.next_run
