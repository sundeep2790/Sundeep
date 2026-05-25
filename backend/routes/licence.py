import re
import datetime
from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datarescue.backend.database import get_db
from datarescue.backend.models import Transaction
from datarescue.backend.crud import upsert_user

router = APIRouter(prefix="/api/licence", tags=["licence"])

class ValidateRequest(BaseModel):
    device_token: str
    email: EmailStr

class AppSumoRequest(BaseModel):
    code: str
    device_token: str
    email: EmailStr

@router.post("/validate")
async def validate_licence(req: ValidateRequest, db: AsyncSession = Depends(get_db)):
    user = await upsert_user(db, req.email, req.device_token)
    
    # Licence is valid if they have a lifetime licence or a positive credit balance
    valid = user.is_lifetime or user.credit_balance > 0
    
    return {
        "valid": valid,
        "balance": user.credit_balance,
        "is_lifetime": user.is_lifetime
    }

@router.post("/appsumo")
async def redeem_appsumo(req: AppSumoRequest, db: AsyncSession = Depends(get_db)):
    code = req.code.upper().strip()
    
    # Validate AppSumo code format (DRESC-XXXXXX) where XXXXXX is 6 alphanumeric characters
    if not re.match(r"^DRESC-[A-Z0-9]{6}$", code):
        raise HTTPException(
            status_code=400,
            detail="Invalid AppSumo code format. Format must be DRESC-XXXXXX (6 alphanumeric characters after dash)."
        )
        
    # Prevent double redemption by checking if transaction with this code as stripe_session_id exists
    stmt = select(Transaction).where(Transaction.stripe_session_id == code)
    res = await db.execute(stmt)
    existing_tx = res.scalars().first()
    if existing_tx:
        raise HTTPException(
            status_code=400,
            detail="This AppSumo code has already been redeemed."
        )
        
    # Upsert user record
    user = await upsert_user(db, req.email, req.device_token)
    
    # Mark is_lifetime=True and add 500 credits
    user.is_lifetime = True
    user.credit_balance += 500
    user.last_seen_at = datetime.datetime.now(timezone.utc)
    
    # Log Transaction
    tx = Transaction(
        user_id=user.id,
        type="lifetime",
        amount=500,
        stripe_session_id=code,
        pack_id="appsumo"
    )
    db.add(tx)
    await db.commit()
    await db.refresh(user)
    
    return {
        "valid": True,
        "balance": user.credit_balance,
    }
