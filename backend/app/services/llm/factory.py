from app.core.config import settings
from app.services.llm.client import LLMClient
from app.services.llm.provider_nim import NIMProvider


def get_llm_client() -> LLMClient | None:
    """Returns None when no API key is configured, so callers can degrade
    gracefully (watching/diffing keeps working even without an LLM
    configured — only the reasoning layer on top is skipped).
    """

    if not settings.nvidia_api_key:
        return None

    return NIMProvider(
        api_key=settings.nvidia_api_key,
        base_url=settings.nvidia_base_url,
        chat_model=settings.nvidia_chat_model,
        embed_model=settings.nvidia_embed_model,
    )
