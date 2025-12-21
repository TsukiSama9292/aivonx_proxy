import httpx


async def stream_post_bytes(url: str, headers: dict, content: bytes):
    """Async generator that streams bytes from an upstream POST request."""
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", url, headers=headers, content=content) as resp:
            async for chunk in resp.aiter_bytes():
                if chunk:
                    yield chunk
