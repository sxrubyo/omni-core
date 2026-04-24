#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List


BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


def brave_search(query: str, api_key: str, *, count: int = 5, timeout: int = 20) -> Dict[str, Any]:
    encoded_query = urllib.parse.quote(str(query or "").strip(), safe="")
    url = f"{BRAVE_SEARCH_URL}?q={encoded_query}&count={count}&text_decorations=false&spellcheck=true"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": str(api_key or "").strip(),
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return {"status": response.status, "payload": payload}
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {err.code}: {body}") from err
    except urllib.error.URLError as err:
        raise RuntimeError(f"Network error: {err}") from err


def summarize_brave_results(payload: Dict[str, Any], *, limit: int = 5) -> List[str]:
    web = payload.get("web") or {}
    results = web.get("results") or []
    lines: List[str] = []
    for item in results[:limit]:
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", "")).strip()
        description = str(item.get("description", "")).strip()
        if title:
            lines.append(title)
        if url:
            lines.append(url)
        if description:
            lines.append(description)
        if title or url or description:
            lines.append("")
    return [line for line in lines if line is not None][: limit * 4]
