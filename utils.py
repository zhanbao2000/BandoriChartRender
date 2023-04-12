from typing import Optional

import httpx


def get_client(proxies: Optional[str] = None, timeout: float = 15, retries: int = 0, **kwargs) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        proxies=proxies,
        timeout=timeout,
        transport=httpx.AsyncHTTPTransport(retries=retries) if retries else None,
        **kwargs
    )


def second_to_sexagesimal(t: float) -> str:
    """Convert seconds to sexagesimal notation. e.g. 0:00.0"""
    return f'{int(t // 60)}:{int(t % 60):02d}.{int(t * 10 % 10):0d}'
