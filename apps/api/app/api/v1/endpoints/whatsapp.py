import logging
import os
from typing import List, Optional
from fastapi import APIRouter, Request, Header, HTTPException, status, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.db.session import get_db
from app.models.whatsapp import (
    AuthorizedDeveloperModel,
    WhatsAppConversationModel,
    WhatsAppMessageModel,
)
from app.schemas.whatsapp import (
    AuthorizedDeveloperCreate,
    AuthorizedDeveloperResponse,
    WhatsAppConversationResponse,
    WhatsAppMessageResponse,
    WhatsAppProviderStatusResponse,
    WhatsAppSimulateRequest,
    WhatsAppSimulateResponse,
)
from app.services.integrations.whatsapp.client import WhatsAppCloudClient
from app.services.integrations.whatsapp.manager import WhatsAppManager
from app.services.integrations.whatsapp.mock_provider import MockWhatsAppProvider
from app.services.integrations.whatsapp.webhook import WhatsAppWebhookHandler

logger = logging.getLogger("devoncall.endpoints.whatsapp")
router = APIRouter()


@router.get("/webhooks/whatsapp", response_class=PlainTextResponse)
async def verify_whatsapp_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    """Meta WhatsApp Cloud API Webhook Challenge Verification."""
    expected_verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "devoncall_whatsapp_verify_token")

    challenge = WhatsAppWebhookHandler.verify_hub_challenge(
        mode=hub_mode,
        token=hub_verify_token,
        challenge=hub_challenge,
        expected_token=expected_verify_token,
    )

    if challenge is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="WhatsApp webhook verification failed: Token mismatch or invalid mode.",
        )

    return PlainTextResponse(content=challenge)


@router.post("/webhooks/whatsapp")
async def handle_whatsapp_webhook(
    request: Request,
    x_hub_signature: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
    db: AsyncSession = Depends(get_db),
):
    """Meta WhatsApp Cloud API Inbound Webhook Event Handler."""
    raw_body = await request.body()
    app_secret = os.environ.get("WHATSAPP_APP_SECRET")

    # 1. Verify HMAC SHA256 Signature (if app secret is set)
    if app_secret:
        if not WhatsAppWebhookHandler.verify_signature(raw_body, x_hub_signature, app_secret):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid WhatsApp webhook signature",
            )

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON body")

    # 2. Extract messages from Meta payload
    extracted = WhatsAppWebhookHandler.parse_inbound_messages(payload)

    if not extracted:
        # Acknowledge delivery receipts / status updates gracefully
        return {"status": "ACKNOWLEDGED", "processed_messages": 0}

    results = []
    # Real provider client if configured, otherwise mock provider
    real_client = WhatsAppCloudClient()
    provider = real_client if real_client.is_configured else MockWhatsAppProvider()
    manager = WhatsAppManager(provider=provider, db_session=db)

    for msg in extracted:
        sender_phone = msg.get("from", "")
        raw_text = msg.get("text", "")
        msg_id = msg.get("id")

        sim_req = WhatsAppSimulateRequest(
            sender_phone=sender_phone,
            raw_text=raw_text,
            use_mock=not real_client.is_configured,
        )

        res = await manager.handle_inbound_message(
            sender_phone=sender_phone,
            raw_text=raw_text,
            provider_message_id=msg_id,
        )
        results.append(res.model_dump())

    return {
        "status": "PROCESSED",
        "processed_messages": len(results),
        "results": results,
    }


@router.get("/status", response_class=None, response_model=WhatsAppProviderStatusResponse)
async def get_whatsapp_status(db: AsyncSession = Depends(get_db)):
    """Retrieve current WhatsApp integration status and developer stats."""
    client = WhatsAppCloudClient()
    devs_res = await db.execute(select(func.count(AuthorizedDeveloperModel.id)))
    devs_count = devs_res.scalar() or 0

    convs_res = await db.execute(select(func.count(WhatsAppConversationModel.id)))
    convs_count = convs_res.scalar() or 0

    return WhatsAppProviderStatusResponse(
        provider_type="OFFICIAL_META_CLOUD_API" if client.is_configured else "MOCK_SIMULATION",
        is_configured=client.is_configured,
        webhook_url="/api/v1/webhooks/whatsapp",
        developers_count=devs_count,
        active_conversations_count=convs_count,
        production_deployments_allowed=False,
    )


@router.get("/developers", response_model=List[AuthorizedDeveloperResponse])
async def list_authorized_developers(db: AsyncSession = Depends(get_db)):
    """List all authorized on-call developers."""
    res = await db.execute(select(AuthorizedDeveloperModel))
    devs = res.scalars().all()
    return [
        AuthorizedDeveloperResponse(
            id=d.id,
            phone_number=d.phone_number,
            identity_hash=d.identity_hash,
            name=d.name,
            role=d.role,
            enabled=d.enabled,
            created_at=d.created_at,
        )
        for d in devs
    ]


@router.post("/developers", response_model=AuthorizedDeveloperResponse)
async def register_authorized_developer(
    req: AuthorizedDeveloperCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register or update an authorized on-call developer."""
    identity_hash = WhatsAppManager.compute_identity_hash(req.phone_number)

    res = await db.execute(
        select(AuthorizedDeveloperModel).where(
            (AuthorizedDeveloperModel.phone_number == req.phone_number)
            | (AuthorizedDeveloperModel.identity_hash == identity_hash)
        )
    )
    existing = res.scalar_one_or_none()

    if existing:
        existing.name = req.name
        existing.role = req.role.upper()
        existing.enabled = req.enabled
        await db.commit()
        await db.refresh(existing)
        return AuthorizedDeveloperResponse(
            id=existing.id,
            phone_number=existing.phone_number,
            identity_hash=existing.identity_hash,
            name=existing.name,
            role=existing.role,
            enabled=existing.enabled,
            created_at=existing.created_at,
        )

    dev = AuthorizedDeveloperModel(
        phone_number=req.phone_number,
        identity_hash=identity_hash,
        name=req.name,
        role=req.role.upper(),
        enabled=req.enabled,
    )
    db.add(dev)
    await db.commit()
    await db.refresh(dev)

    logger.info(f"Registered new authorized developer '{dev.name}' ({dev.phone_number}, role={dev.role})")
    return AuthorizedDeveloperResponse(
        id=dev.id,
        phone_number=dev.phone_number,
        identity_hash=dev.identity_hash,
        name=dev.name,
        role=dev.role,
        enabled=dev.enabled,
        created_at=dev.created_at,
    )


@router.post("/simulate", response_model=WhatsAppSimulateResponse)
async def simulate_whatsapp_command(
    req: WhatsAppSimulateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Simulate receiving a WhatsApp command from a developer in offline/test mode."""
    real_client = WhatsAppCloudClient()
    provider = MockWhatsAppProvider() if (req.use_mock or not real_client.is_configured) else real_client
    manager = WhatsAppManager(provider=provider, db_session=db)

    res = await manager.handle_inbound_message(
        sender_phone=req.sender_phone,
        raw_text=req.raw_text,
    )
    return res


@router.get("/conversations", response_model=List[WhatsAppConversationResponse])
async def list_whatsapp_conversations(db: AsyncSession = Depends(get_db)):
    """List WhatsApp conversations and message history."""
    res = await db.execute(select(WhatsAppConversationModel))
    convs = res.scalars().all()

    out = []
    for c in convs:
        dev_res = await db.execute(select(AuthorizedDeveloperModel).where(AuthorizedDeveloperModel.id == c.developer_id))
        dev = dev_res.scalar_one_or_none()
        dev_name = dev.name if dev else "Unknown"

        msgs_res = await db.execute(
            select(WhatsAppMessageModel)
            .where(WhatsAppMessageModel.conversation_id == c.id)
            .order_by(WhatsAppMessageModel.created_at.asc())
        )
        msgs = msgs_res.scalars().all()

        msg_responses = [
            WhatsAppMessageResponse(
                id=m.id,
                direction=m.direction,
                sender_phone=m.sender_phone,
                recipient_phone=m.recipient_phone,
                raw_text=m.raw_text,
                command_type=m.command_type,
                is_authorized=m.is_authorized,
                is_redacted=m.is_redacted,
                status=m.status,
                created_at=m.created_at,
            )
            for m in msgs
        ]

        out.append(
            WhatsAppConversationResponse(
                id=c.id,
                developer_id=c.developer_id,
                developer_name=dev_name,
                phone_number=c.phone_number,
                active_project_id=c.active_project_id,
                state=c.state,
                updated_at=c.updated_at,
                messages=msg_responses,
            )
        )
    return out
