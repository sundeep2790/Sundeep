import uuid
import datetime
from datetime import timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datarescue.backend.models import User, Transaction

async def upsert_user(db: AsyncSession, email: str, device_token: str) -> User:
    # First, find by email
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        # Check by device_token to avoid UniqueConstraint violation on device_token
        stmt = select(User).where(User.device_token == device_token)
        result = await db.execute(stmt)
        user = result.scalars().first()
        
    if user:
        # User exists — update last_seen_at.
        user.last_seen_at = datetime.datetime.now(timezone.utc)
        # If the stored token is a webhook-generated sentinel ("pending_..."),
        # replace it with the real device token now that the user has authenticated.
        if user.device_token and user.device_token.startswith("pending_"):
            user.device_token = device_token
        await db.commit()
        await db.refresh(user)
    else:
        # Create new user
        user = User(
            email=email,
            device_token=device_token,
            credit_balance=0,
            is_lifetime=False
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
    return user

async def process_successful_payment(
    db: AsyncSession,
    email: str,
    stripe_session_id: str,
    pack_id: str,
    device_token: str = None
) -> User:
    # Check if transaction already processed to prevent double redemption
    stmt = select(Transaction).where(Transaction.stripe_session_id == stripe_session_id)
    res = await db.execute(stmt)
    existing_tx = res.scalars().first()
    
    if existing_tx:
        # Already processed, return user
        stmt = select(User).where(User.email == email)
        res_user = await db.execute(stmt)
        user = res_user.scalars().first()
        if user:
            return user
            
    # Get user
    if device_token:
        user = await upsert_user(db, email, device_token)
    else:
        stmt = select(User).where(User.email == email)
        res_user = await db.execute(stmt)
        user = res_user.scalars().first()
        if not user:
            # Create a stub user. device_token is left as a sentinel ("pending_<uuid>")
            # and will be replaced with the real token when the user first authenticates
            # from the desktop app via upsert_user().
            user = User(
                email=email,
                device_token=f"pending_{uuid.uuid4()}",
                credit_balance=0,
                is_lifetime=False
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

    # Determine credits and lifetime status based on pack_id
    credits_to_add = 0
    is_lifetime = False
    tx_type = "purchase"

    if pack_id == "starter":
        credits_to_add = 100
    elif pack_id == "standard":
        credits_to_add = 250
    elif pack_id == "plus":
        credits_to_add = 500
    elif pack_id == "unlimited":
        credits_to_add = 0
        is_lifetime = True
        tx_type = "lifetime"
    elif pack_id == "appsumo":
        credits_to_add = 500
        is_lifetime = True
        tx_type = "lifetime"
    else:
        # Default fallback
        credits_to_add = 100

    user.credit_balance += credits_to_add
    if is_lifetime:
        user.is_lifetime = True
    user.last_seen_at = datetime.datetime.now(timezone.utc)

    # Log Transaction
    tx = Transaction(
        user_id=user.id,
        type=tx_type,
        amount=credits_to_add,
        stripe_session_id=stripe_session_id,
        pack_id=pack_id
    )
    db.add(tx)
    await db.commit()
    await db.refresh(user)
    return user
