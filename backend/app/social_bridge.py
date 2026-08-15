"""Social Bridge — helper do generowania deep-linków dla platform social media i B2B."""
from urllib.parse import urlencode, quote


# ---------------------------------------------------------------------------
# Konfiguracja platform
# ---------------------------------------------------------------------------

PLATFORM_CONFIGS: dict[str, dict] = {
    "facebook_messenger": {
        "label": "Facebook Messenger",
        "icon": "💬",
        "base_url": "https://m.me/",
        "description": "Otwórz czat w Messengerze",
    },
    "facebook_group": {
        "label": "Grupa Facebook",
        "icon": "👥",
        "base_url": "https://www.facebook.com/groups/",
        "description": "Dołącz do grupy na Facebooku",
    },
    "facebook_post": {
        "label": "Post Facebook",
        "icon": "📢",
        "base_url": "https://www.facebook.com/sharer/sharer.php",
        "description": "Udostępnij post na Facebooku",
    },
    "telegram_chat": {
        "label": "Telegram Chat",
        "icon": "✈️",
        "base_url": "https://t.me/",
        "description": "Otwórz czat na Telegramie",
    },
    "telegram_channel": {
        "label": "Kanał Telegram",
        "icon": "📡",
        "base_url": "https://t.me/",
        "description": "Subskrybuj kanał Telegram",
    },
    "whatsapp": {
        "label": "WhatsApp",
        "icon": "📱",
        "base_url": "https://wa.me/",
        "description": "Wyślij wiadomość przez WhatsApp",
    },
    "linkedin": {
        "label": "LinkedIn",
        "icon": "🔗",
        "base_url": "https://www.linkedin.com/company/",
        "description": "Odwiedź profil na LinkedIn",
    },
    "otomoto": {
        "label": "OtoMoto",
        "icon": "🚗",
        "base_url": "https://www.otomoto.pl/osobowe",
        "description": "Szukaj ogłoszeń na OtoMoto",
    },
    "olx": {
        "label": "OLX",
        "icon": "🛒",
        "base_url": "https://www.olx.pl/motoryzacja/",
        "description": "Przeglądaj oferty na OLX",
    },
    "allegro": {
        "label": "Allegro",
        "icon": "🛍️",
        "base_url": "https://allegro.pl/listing",
        "description": "Szukaj na Allegro",
    },
    "gratka": {
        "label": "Gratka",
        "icon": "📋",
        "base_url": "https://gratka.pl/motoryzacja/",
        "description": "Ogłoszenia motoryzacyjne Gratka",
    },
}


# ---------------------------------------------------------------------------
# Generatory deep-linków
# ---------------------------------------------------------------------------

def build_messenger_link(page_id: str, ref: str = "") -> str:
    """Deep-link do czatu Messenger dla konkretnej strony FB."""
    url = f"https://m.me/{quote(str(page_id), safe='')}"
    if ref:
        url += f"?ref={quote(ref, safe='')}"
    return url


def build_facebook_group_link(group_id_or_slug: str) -> str:
    """Link do grupy Facebook."""
    return f"https://www.facebook.com/groups/{quote(str(group_id_or_slug), safe='')}"


def build_facebook_share_link(url_to_share: str, quote_text: str = "") -> str:
    """Przycisk 'Udostępnij' dla dowolnego URL-a."""
    params: dict[str, str] = {"u": url_to_share}
    if quote_text:
        params["quote"] = quote_text
    return f"https://www.facebook.com/sharer/sharer.php?{urlencode(params)}"


def build_telegram_chat_link(username_or_id: str, message: str = "") -> str:
    """Deep-link do czatu Telegram (username lub numer telefonu)."""
    base = f"https://t.me/{quote(str(username_or_id), safe='')}"
    if message:
        base += f"?text={quote(message, safe='')}"
    return base


def build_telegram_channel_link(channel_username: str) -> str:
    """Link do kanału Telegram."""
    return f"https://t.me/{quote(str(channel_username), safe='')}"


def build_whatsapp_link(phone_number: str, message: str = "") -> str:
    """Deep-link WhatsApp z opcjonalną treścią wiadomości.

    phone_number powinien być w formacie międzynarodowym bez '+', np. '48123456789'.
    """
    clean_phone = "".join(c for c in phone_number if c.isdigit())
    base = f"https://wa.me/{clean_phone}"
    if message:
        base += f"?text={quote(message, safe='')}"
    return base


def build_linkedin_company_link(company_slug: str) -> str:
    """Link do strony firmy na LinkedIn."""
    return f"https://www.linkedin.com/company/{quote(str(company_slug), safe='')}"


def build_otomoto_search_link(query: str = "", make: str = "", model: str = "") -> str:
    """Link do wyszukiwania na OtoMoto z gotowymi filtrami."""
    params: dict[str, str] = {}
    if query:
        params["search[filter_float_price:from]"] = ""
        params["search[order]"] = "created_at:desc"
        params["search[advanced_search_expanded]"] = "true"
        params["search[filter_enum_make][]"] = query
    if make:
        params["search[filter_enum_make][]"] = make
    if model:
        params["search[filter_enum_model][]"] = model
    base = "https://www.otomoto.pl/osobowe"
    if params:
        base += f"?{urlencode(params)}"
    return base


def build_olx_search_link(query: str = "") -> str:
    """Link do OLX z wyszukiwaną frazą."""
    base = "https://www.olx.pl/motoryzacja/"
    if query:
        base += f"?q={quote(query, safe='')}"
    return base


def build_allegro_search_link(query: str = "") -> str:
    """Link do Allegro z wyszukiwaną frazą."""
    params: dict[str, str] = {"string": query} if query else {}
    base = "https://allegro.pl/listing"
    if params:
        base += f"?{urlencode(params)}"
    return base


# ---------------------------------------------------------------------------
# Główna funkcja rozdzielająca
# ---------------------------------------------------------------------------

def generate_deep_link(platform: str, params: dict) -> str:
    """Generuje deep-link dla podanej platformy i parametrów.

    Args:
        platform: klucz platformy (np. 'telegram_chat', 'facebook_messenger')
        params: słownik parametrów specyficznych dla platformy

    Returns:
        Gotowy URL (str).

    Raises:
        ValueError: gdy platforma jest nieznana.
    """
    p = platform.lower()

    if p == "facebook_messenger":
        return build_messenger_link(
            page_id=params.get("page_id", ""),
            ref=params.get("ref", ""),
        )
    if p == "facebook_group":
        return build_facebook_group_link(params.get("group_id", ""))
    if p == "facebook_post":
        return build_facebook_share_link(
            url_to_share=params.get("url", ""),
            quote_text=params.get("text", ""),
        )
    if p == "telegram_chat":
        return build_telegram_chat_link(
            username_or_id=params.get("username", ""),
            message=params.get("message", ""),
        )
    if p == "telegram_channel":
        return build_telegram_channel_link(params.get("channel", ""))
    if p == "whatsapp":
        return build_whatsapp_link(
            phone_number=params.get("phone", ""),
            message=params.get("message", ""),
        )
    if p == "linkedin":
        return build_linkedin_company_link(params.get("company", ""))
    if p == "otomoto":
        return build_otomoto_search_link(
            query=params.get("query", ""),
            make=params.get("make", ""),
            model=params.get("model", ""),
        )
    if p == "olx":
        return build_olx_search_link(params.get("query", ""))
    if p == "allegro":
        return build_allegro_search_link(params.get("query", ""))

    raise ValueError(f"Nieznana platforma: '{platform}'")
