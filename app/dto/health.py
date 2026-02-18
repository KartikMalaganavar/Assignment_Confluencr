from datetime import datetime

from pydantic import BaseModel, field_serializer

from app.utils.time import IST


class HealthResponse(BaseModel):
    status: str
    current_time: datetime

    @field_serializer("current_time", when_used="json")
    def serialize_ist(self, value: datetime) -> datetime:
        return value.astimezone(IST)
