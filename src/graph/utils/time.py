import datetime
from zoneinfo import ZoneInfo  # Python 3.9+ 내장 라이브러리
from pydantic import BaseModel, Field
import datetime


def get_current_utc_timestamp() -> datetime.datetime:
    """
    현재 시간을 UTC 기준의 timezone-aware datetime 객체로 반환합니다.
    이 객체는 Pydantic과 psycopg2에서 추가 가공 없이 바로 사용할 수 있습니다.
    """
    return datetime.datetime.now(tz=ZoneInfo('UTC'))


class EventModel(BaseModel):
    event_name: str
    # Pydantic 모델에 datetime.datetime 타입으로 필드 정의
    created_at: datetime.datetime = Field(default_factory=get_current_utc_timestamp)
