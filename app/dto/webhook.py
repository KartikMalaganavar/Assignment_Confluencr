from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionWebhookIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    transaction_id: str = Field(min_length=1, max_length=128)
    source_account: str = Field(min_length=1, max_length=128)
    destination_account: str = Field(min_length=1, max_length=128)
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class TransactionWebhookAck(BaseModel):
    status_code: int = 202
    acknowledged: bool = True
    transaction_id: str
    response_time_ms: float
