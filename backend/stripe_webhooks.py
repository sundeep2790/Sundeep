import os
import json
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
import stripe
from datarescue.backend.database import get_db
from datarescue.backend.crud import process_successful_payment

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db)
):
    payload = await request.body()
    stripe_secret = os.getenv("STRIPE_SECRET_KEY", "")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    
    event_type = None
    event_data = {}
    
    if stripe_secret and webhook_secret:
        # Real Stripe validation
        if not stripe_signature:
            raise HTTPException(
                status_code=400,
                detail="Missing Stripe-Signature header"
            )
        try:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, webhook_secret
            )
            event_type = event.get("type")
            event_data = event.get("data", {}).get("object", {})
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Webhook signature verification failed: {str(e)}"
            )
    else:
        # Mock mode / fallback mode when credentials are not configured
        try:
            event = json.loads(payload)
            event_type = event.get("type")
            event_data = event.get("data", {}).get("object", {})
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON payload for mock webhook: {str(e)}"
            )
            
    if event_type == "checkout.session.completed":
        session = event_data
        stripe_session_id = session.get("id")
        
        # Extract email from checkout session
        email = session.get("customer_email")
        if not email:
            customer_details = session.get("customer_details") or {}
            email = customer_details.get("email")
            
        if not stripe_session_id:
            raise HTTPException(
                status_code=400,
                detail="Missing session id in event data"
            )
        if not email:
            raise HTTPException(
                status_code=400,
                detail="Missing customer email in event data"
            )
            
        metadata = session.get("metadata") or {}
        pack_id = metadata.get("pack_id", "starter")
        
        # Process the successful payment (adds credits, marks lifetime, prevents duplicate transactions)
        await process_successful_payment(
            db=db,
            email=email,
            stripe_session_id=stripe_session_id,
            pack_id=pack_id
        )
        
    return {"status": "success"}
