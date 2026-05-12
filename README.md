# EST Time Format Patch

Use this logic in your main app:

from datetime import datetime
from zoneinfo import ZoneInfo

est_now = datetime.now(ZoneInfo("America/New_York"))
formatted_time = est_now.strftime("%I:%M:%S %p EST")

This converts:
- 24-hour time
to
- EST/EDT 12-hour AM/PM time