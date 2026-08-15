"""Social Bridge router — deep-linking i automatyczne mostki z social mediami."""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.models import SocialChannelEvent
from app.social_bridge import PLATFORM_CONFIGS, generate_deep_link
from database import get_db

router = APIRouter(prefix="/api/social", tags=["social"])


# ---------------------------------------------------------------------------
# Schematy Pydantic
# ---------------------------------------------------------------------------

class DeepLinkRequest(BaseModel):
    """Parametry do wygenerowania deep-linka."""
    params: dict = {}


class DeepLinkResponse(BaseModel):
    platform: str
    label: str
    icon: str
    target_url: str
    description: str


# ---------------------------------------------------------------------------
# Endpointy
# ---------------------------------------------------------------------------

@router.get("/platforms", summary="Lista dostępnych platform")
def list_platforms():
    """Zwraca listę obsługiwanych platform wraz z metadanymi."""
    return [
        {
            "platform": key,
            "label": cfg["label"],
            "icon": cfg["icon"],
            "description": cfg["description"],
        }
        for key, cfg in PLATFORM_CONFIGS.items()
    ]


@router.post(
    "/connect/{platform}",
    response_model=DeepLinkResponse,
    summary="Zarejestruj kliknięcie i wygeneruj deep-link",
)
def connect_platform(
    platform: str,
    body: DeepLinkRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Rejestruje aktywację kanału w bazie danych i zwraca gotowy ``target_url``.

    Front-end powinien otworzyć ``target_url`` w nowej karcie
    (``window.open(target_url, '_blank')``).
    """
    try:
        target_url = generate_deep_link(platform, body.params)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Extract client IP — take only the first value from x-forwarded-for to
    # avoid trusting a user-supplied proxy chain verbatim.
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        ip = forwarded_for.split(",")[0].strip()
    elif request.client:
        ip = request.client.host
    else:
        ip = ""
    user_agent = request.headers.get("user-agent", "")
    event = SocialChannelEvent(
        platform=platform,
        target_url=target_url,
        params_json=json.dumps(body.params, ensure_ascii=False),
        ip=ip,
        user_agent=user_agent,
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    db.commit()

    cfg = PLATFORM_CONFIGS.get(platform.lower(), {})
    return DeepLinkResponse(
        platform=platform,
        label=cfg.get("label", platform),
        icon=cfg.get("icon", "🔗"),
        target_url=target_url,
        description=cfg.get("description", ""),
    )


@router.get("/links", summary="Gotowe linki dla popularnych platform")
def get_default_links():
    """Zwraca zestaw gotowych linków domyślnych (bez parametrów).

    Użyteczne przy pierwszym renderze panelu – front-end może od razu
    wyświetlić przyciski nawet bez znajomości konkretnych identyfikatorów.
    """
    defaults = [
        ("facebook_group",   {"group_id": "polska-auto-leads"}),
        ("telegram_channel", {"channel": "polska_auto_leads"}),
        ("otomoto",          {}),
        ("olx",              {}),
        ("allegro",          {}),
    ]
    result = []
    for platform, params in defaults:
        try:
            url = generate_deep_link(platform, params)
        except ValueError:
            continue
        cfg = PLATFORM_CONFIGS.get(platform, {})
        result.append({
            "platform": platform,
            "label": cfg.get("label", platform),
            "icon": cfg.get("icon", "🔗"),
            "target_url": url,
            "description": cfg.get("description", ""),
        })
    return result


@router.get("/events", summary="Historia kliknięć / aktywacji kanałów")
def list_events(limit: int = 50, db: Session = Depends(get_db)):
    """Zwraca ostatnie zdarzenia zarejestrowane w bazie."""
    events = (
        db.query(SocialChannelEvent)
        .order_by(SocialChannelEvent.created_at.desc())
        .limit(max(1, min(limit, 200)))
        .all()
    )
    return [
        {
            "id": e.id,
            "platform": e.platform,
            "target_url": e.target_url,
            "params": json.loads(e.params_json or "{}"),
            "ip": e.ip,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]
