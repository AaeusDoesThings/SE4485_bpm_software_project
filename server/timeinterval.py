from cattrs import structure
from datetime import datetime
from attrs import define

@define
class TimeInterval:
    start_at: datetime
    end_at: datetime

data={
    "start_at": "2026-11-09T00:00:00Z",
    "end_at": "2026-11-09T23:59:59Z"
}

interval = structure(data, TimeInterval)

print(interval.start_at)
print(interval.end_at)