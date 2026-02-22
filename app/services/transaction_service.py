from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.dto.transaction import TransactionOut
from app.repositories.transaction_repository import TransactionRepository


class TransactionService:
    def __init__(self, db: AsyncSession):
        self.repository = TransactionRepository(db)

    async def get_transaction_by_id(self, transaction_id: str) -> List[TransactionOut]:
        transactions = await self.repository.get_by_transaction_id(transaction_id)
        return [TransactionOut.model_validate(txn) for txn in transactions]
