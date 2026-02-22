from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.utils.db import get_db
from app.dto.transaction import TransactionOut
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/v1/transactions", tags=["transactions"])

def get_service(db: AsyncSession = Depends(get_db)) -> TransactionService:
    return TransactionService(db)

@router.get("/{transaction_id}", response_model=List[TransactionOut], status_code=status.HTTP_200_OK)
async def get_transaction(transaction_id: str, service: TransactionService = Depends(get_service)) -> List[TransactionOut]:
    transactions = await service.get_transaction_by_id(transaction_id)
    return transactions
