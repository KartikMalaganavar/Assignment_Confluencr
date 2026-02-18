from sqlalchemy.orm import Session

from app.dto.transaction import TransactionOut
from app.repositories.transaction_repository import TransactionRepository


class TransactionService:
    def __init__(self, db: Session):
        self.repository = TransactionRepository(db)

    def get_transaction_by_id(self, transaction_id: str) -> TransactionOut | None:
        transaction = self.repository.get_by_transaction_id(transaction_id)
        if transaction is None:
            return None
        return TransactionOut.model_validate(transaction)
