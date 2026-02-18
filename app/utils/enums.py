from enum import StrEnum


class TransactionStatus(StrEnum):
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
