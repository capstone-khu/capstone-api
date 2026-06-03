from datetime import datetime, timedelta, timezone
from typing import Annotated

from pydantic import PlainSerializer

KST = timezone(timedelta(hours=9))


def _to_kst_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=KST)
    else:
        value = value.astimezone(KST)
    return value.isoformat()


KSTDateTime = Annotated[datetime, PlainSerializer(_to_kst_iso, return_type=str)]
