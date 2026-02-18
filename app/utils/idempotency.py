import hashlib
import json
from decimal import Decimal

from app.dto.webhook import TransactionWebhookIn


def _normalize_decimal(value: Decimal) -> str:
    # Use fixed precision canonical representation for stable hashes.
    return f"{value:.2f}"


def canonical_payload(data: TransactionWebhookIn) -> dict[str, str]:
    return {
        "transaction_id": data.transaction_id.strip(),
        "source_account": data.source_account.strip(),
        "destination_account": data.destination_account.strip(),
        "amount": _normalize_decimal(data.amount),
        "currency": data.currency.upper().strip(),
    }


def payload_hash(data: TransactionWebhookIn) -> str:
    payload = canonical_payload(data)
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
