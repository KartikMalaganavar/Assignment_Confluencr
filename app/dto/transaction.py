from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer

from app.utils.enums import TransactionStatus
from app.utils.time import IST


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: str
    source_account: str
    destination_account: str
    amount: Decimal
    currency: str
    status: TransactionStatus
    created_at: datetime
    processed_at: datetime | None

    @field_serializer("created_at", "processed_at", when_used="json")
    def serialize_ist(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value.astimezone(IST)
