from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.db import get_db
from app.dto.transaction import TransactionOut
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/v1/transactions", tags=["transactions"])

def get_service(db: AsyncSession = Depends(get_db)) -> TransactionService:
    return TransactionService(db)

@router.get("/{transaction_id}", response_model=TransactionOut, status_code=status.HTTP_200_OK)
async def get_transaction(transaction_id: str, service: TransactionService = Depends(get_service)) -> TransactionOut:
    transaction = await service.get_transaction_by_id(transaction_id)
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    return transaction
