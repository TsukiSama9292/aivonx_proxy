import httpx
from django.conf import settings
import logging

logger = logging.getLogger('proxy')


async def stream_post_bytes(url: str, headers: dict, content: bytes):
    """Async generator that streams bytes from an upstream POST request.

    Uses a configurable timeout to avoid unbounded upstream waits.
    """
    timeout = getattr(settings, 'PROXY_UPSTREAM_TIMEOUT', 30.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", url, headers=headers, content=content) as resp:
                async for chunk in resp.aiter_bytes():
                    if chunk:
                        yield chunk
    except Exception as e:
        logger.exception("stream_post_bytes: upstream streaming failed: %s", e)
        # propagate to caller; caller may decide how to handle
        raise
