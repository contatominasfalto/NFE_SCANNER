from datetime import datetime
from zoneinfo import ZoneInfo


SAO_PAULO_TZ = ZoneInfo("America/Sao_Paulo")


def local_now() -> datetime:
    return datetime.now(SAO_PAULO_TZ).replace(tzinfo=None)
