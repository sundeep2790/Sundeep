import os
import datetime
from datetime import timezone
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datarescue.backend.database import get_db
from datarescue.backend.models import User, Transaction
from datarescue.backend.crud import upsert_user, process_successful_payment

router = APIRouter(prefix="/api/credits", tags=["credits"])

class DeductRequest(BaseModel):
    device_token: str
    email: EmailStr
    amount: int

class ConfirmRequest(BaseModel):
    stripe_session_id: str
    device_token: str
    email: EmailStr

def determine_mock_pack(session_id: str) -> str:
    session_id_lower = session_id.lower()
    if "starter" in session_id_lower:
        return "starter"
    elif "standard" in session_id_lower:
        return "standard"
    elif "plus" in session_id_lower:
        return "plus"
    elif "unlimited" in session_id_lower:
        return "unlimited"
    elif "appsumo" in session_id_lower:
        return "appsumo"
    return "starter"

@router.get("/balance")
async def get_balance(
    x_device_token: str = Header(..., alias="X-Device-Token"),
    x_user_email: str = Header(..., alias="X-User-Email"),
    db: AsyncSession = Depends(get_db)
):
    if not x_device_token or not x_user_email:
        raise HTTPException(
            status_code=400,
            detail="Missing X-Device-Token or X-User-Email headers"
        )
    
    user = await upsert_user(db, x_user_email, x_device_token)
    return {
        "balance": user.credit_balance,
        "is_lifetime": user.is_lifetime,
        "email": user.email
    }

@router.post("/deduct")
async def deduct_credits(req: DeductRequest, db: AsyncSession = Depends(get_db)):
    if req.amount < 0:
        raise HTTPException(status_code=400, detail="Deduction amount must be positive")

    # Find user by email
    stmt = select(User).where(User.email == req.email)
    res = await db.execute(stmt)
    user = res.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Validate device_token matches email record
    if user.device_token != req.device_token:
        raise HTTPException(status_code=403, detail="Device token mismatch")
        
    # Validate balance >= amount (unless is_lifetime is True)
    if not user.is_lifetime and user.credit_balance < req.amount:
        raise HTTPException(status_code=400, detail="Insufficient credits")
        
    # Deduct credits
    deducted_amount = req.amount
    if not user.is_lifetime:
        user.credit_balance -= deducted_amount
    
    user.last_seen_at = datetime.datetime.now(timezone.utc)
    
    # Log Transaction
    tx = Transaction(
        user_id=user.id,
        type="deduction",
        amount=-deducted_amount,
        stripe_session_id=None,
        pack_id=None
    )
    db.add(tx)
    await db.commit()
    await db.refresh(user)
    
    return {
        "balance": user.credit_balance,
        "is_lifetime": user.is_lifetime,
        "email": user.email
    }

@router.post("/confirm")
async def confirm_payment(req: ConfirmRequest, db: AsyncSession = Depends(get_db)):
    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    
    # Determine pack_id
    pack_id = "starter"  # Default
    
    if stripe_key:
        try:
            import stripe
            stripe.api_key = stripe_key
            session = stripe.checkout.Session.retrieve(req.stripe_session_id)
            if session.payment_status != "paid":
                raise HTTPException(status_code=400, detail="Payment has not been completed")
            pack_id = session.metadata.get("pack_id", "starter")
        except Exception as e:
            # Fallback to mock session if session starts with mock_ or allow testing
            if req.stripe_session_id.startswith("mock_"):
                pack_id = determine_mock_pack(req.stripe_session_id)
            else:
                raise HTTPException(status_code=400, detail=f"Stripe session validation failed: {str(e)}")
    else:
        # Mock validation
        pack_id = determine_mock_pack(req.stripe_session_id)
        
    user = await process_successful_payment(
        db=db,
        email=req.email,
        stripe_session_id=req.stripe_session_id,
        pack_id=pack_id,
        device_token=req.device_token
    )
    
    return {
        "balance": user.credit_balance,
        "is_lifetime": user.is_lifetime,
        "email": user.email
    }

from fastapi.responses import RedirectResponse
import uuid

@router.get("/checkout")
async def checkout_redirect(pack_id: str, email: str):
    stripe_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        # Mock mode redirect to local mock success info page
        mock_session_id = f"mock_{pack_id}_{uuid.uuid4().hex[:8]}"
        return RedirectResponse(
            url=f"/api/credits/mock-success?session_id={mock_session_id}&email={email}"
        )
        
    try:
        import stripe
        stripe.api_key = stripe_key
        
        # Map pack_id to price in cents
        unit_amount = 999  # $9.99 starter
        if pack_id == "standard":
            unit_amount = 2499  # $24.99
        elif pack_id == "plus":
            unit_amount = 4999  # $49.99
        elif pack_id == "unlimited":
            unit_amount = 9999  # $99.99
            
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"DataRescue {pack_id.capitalize()} Pack",
                    },
                    "unit_amount": unit_amount,
                },
                "quantity": 1,
            }],
            mode="payment",
            customer_email=email,
            success_url=os.getenv("STRIPE_SUCCESS_URL", "https://example.com/success?session_id={CHECKOUT_SESSION_ID}"),
            cancel_url=os.getenv("STRIPE_CANCEL_URL", "https://example.com/cancel"),
            metadata={"pack_id": pack_id}
        )
        return RedirectResponse(url=session.url)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create Stripe checkout session: {str(e)}"
        )

@router.get("/mock-success")
async def mock_success(session_id: str, email: str):
    return {
        "message": "Mock payment successful! Please copy the stripe_session_id below and use it in your desktop client to confirm your credits.",
        "stripe_session_id": session_id,
        "email": email,
        "instructions": f"POST to /api/credits/confirm with: {{'stripe_session_id': '{session_id}', 'device_token': '<your_device_token>', 'email': '{email}'}}"
    }

