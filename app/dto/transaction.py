from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.utils.enums import TransactionStatus


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
