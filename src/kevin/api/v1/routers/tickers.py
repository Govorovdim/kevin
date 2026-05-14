import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from kevin.api.v1.dependencies import get_current_user

router = APIRouter(
    prefix="/tickers",
    tags=["tickers"],
    dependencies=[Depends(get_current_user)],
)

_YF_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Persistent HTTP client with connection pooling
_http_client = httpx.AsyncClient(
    headers=_YF_HEADERS,
    timeout=10.0,
)


@router.get("/search")
async def search_tickers(q: str = Query(..., min_length=1)):
    """Search for ticker symbols by name or symbol using Yahoo Finance."""
    url = "https://query1.finance.yahoo.com/v1/finance/search"
    params = {
        "q": q,
        "quotesCount": 8,
        "newsCount": 0,
        "listsCount": 0,
        "enableFuzzyQuery": False,
    }
    try:
        resp = await _http_client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502, detail=f"Yahoo Finance error: {exc.response.status_code}"
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503, detail=f"Could not reach Yahoo Finance: {exc}"
        )

    quotes = data.get("quotes", [])
    return [
        {
            "symbol": item["symbol"],
            "name": item.get("shortname") or item.get("longname") or item["symbol"],
            "type": item.get("quoteType", ""),
            "exchange": item.get("exchange", ""),
        }
        for item in quotes
        if "symbol" in item
    ]


@router.get("/{symbol}/quote")
async def get_ticker_quote(symbol: str):
    """Return the current (or most recent close) price for a ticker symbol."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"interval": "1d", "range": "1d"}
    try:
        resp = await _http_client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502, detail=f"Yahoo Finance error: {exc.response.status_code}"
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503, detail=f"Could not reach Yahoo Finance: {exc}"
        )

    try:
        meta = data["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice") or meta.get("previousClose")
        currency = meta.get("currency", "USD")
        return {"symbol": symbol.upper(), "price": price, "currency": currency}
    except (KeyError, IndexError, TypeError):
        return {"symbol": symbol.upper(), "price": None, "currency": None}
