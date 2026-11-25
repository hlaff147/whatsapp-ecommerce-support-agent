"""Normalização e particionamento seguro de texto para WhatsApp."""

from pawdesk.shared.constants.limits import WHATSAPP_MAX_TEXT_CHARS
from pawdesk.shared.constants.regex import WHITESPACE_RE


def strip_control_chars(text: str) -> str:
    """Remove caracteres de controle mantendo quebras de linha e tabulações."""
    return "".join(ch for ch in text if ch in {"\n", "\t"} or ord(ch) >= 32)


def normalize_text(text: str) -> str:
    """Limpa caracteres de controle e normaliza espaços em branco."""
    cleaned = strip_control_chars(text).strip()
    return WHITESPACE_RE.sub(" ", cleaned)


def truncate_for_whatsapp(text: str, max_chars: int = WHATSAPP_MAX_TEXT_CHARS) -> str:
    """Trunca texto respeitando o limite do canal WhatsApp."""
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    return text[: max_chars - 3].rstrip() + "..."


def split_for_whatsapp(text: str, max_chars: int = WHATSAPP_MAX_TEXT_CHARS) -> list[str]:
    """Divide mensagens longas em blocos dentro do limite do WhatsApp."""
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break
        split_at = remaining.rfind("\n", 0, max_chars)
        if split_at <= 0:
            split_at = remaining.rfind(" ", 0, max_chars)
        if split_at <= 0:
            split_at = max_chars
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    return [c for c in chunks if c]
