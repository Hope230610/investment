from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timedelta, timezone
from html import unescape
from typing import Any, Optional

import httpx
import structlog

from src.core.config import get_settings
from src.schemas.stock import (
    StockCompanyProfile,
    StockDetail,
    StockEvent,
    StockHistoryPoint,
    StockQuoteSnapshot,
    StockSearchItem,
)


CN_TZ = timezone(timedelta(hours=8))


class _TTLCache:
    def __init__(self):
        self._lock = threading.Lock()
        self._store: dict[str, tuple[datetime, Any]] = {}

    def get(self, key: str) -> Any:
        with self._lock:
            cached = self._store.get(key)
            if not cached:
                return None
            expires_at, value = cached
            if expires_at <= datetime.now(CN_TZ):
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: int):
        with self._lock:
            self._store[key] = (
                datetime.now(CN_TZ) + timedelta(seconds=ttl_seconds),
                value,
            )


class MarketDataService:
    """Fetch and normalize external market data for A-share analysis."""

    SEARCH_URL = "https://searchadapter.eastmoney.com/api/suggest/get"
    NOTICE_URL = "https://np-anotice-stock.eastmoney.com/api/security/ann"
    QUOTE_URL = "https://qt.gtimg.cn/q={symbol}"
    HISTORY_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    QUOTE_PAGE_URL = "https://quote.eastmoney.com/concept/{symbol}.html"

    def __init__(self):
        settings = get_settings()
        self.settings = settings
        self.logger = structlog.get_logger().bind(service="market_data")
        self.cache = _TTLCache()
        self.client = httpx.Client(
            timeout=settings.STOCK_DATA_TIMEOUT,
            follow_redirects=True,
            trust_env=False,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/123.0.0.0 Safari/537.36"
                ),
                "Referer": "https://quote.eastmoney.com/",
            },
        )

    def search_stocks(self, query: str, limit: int = 10) -> list[StockSearchItem]:
        normalized_query = query.strip()
        if not normalized_query:
            return []

        cache_key = f"search:{normalized_query}:{limit}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        payload = self._request_json(
            self.SEARCH_URL,
            params={
                "input": normalized_query,
                "type": "14",
                "token": "D43BF722C8E33BDC906FB84D85E326E8",
            },
        )
        rows = ((payload or {}).get("QuotationCodeTable") or {}).get("Data") or []

        items: list[StockSearchItem] = []
        seen: set[str] = set()
        for row in rows:
            if row.get("Classify") != "AStock":
                continue
            market = self._market_from_search_row(row)
            if not market:
                continue
            stock_code = str(row.get("Code") or "").strip()
            if not re.fullmatch(r"\d{6}", stock_code):
                continue
            stock_id = f"{market}{stock_code}"
            if stock_id in seen:
                continue

            seen.add(stock_id)
            items.append(
                StockSearchItem(
                    stock_id=stock_id,
                    stock_code=stock_code,
                    stock_name=str(row.get("Name") or stock_code),
                    market=market,
                    industry=None,
                    security_type=row.get("SecurityTypeName"),
                    pinyin=row.get("PinYin"),
                    quote_id=row.get("QuoteID"),
                    matched_by=self._infer_match_type(normalized_query, stock_code, row),
                )
            )
            if len(items) >= limit:
                break

        self.cache.set(cache_key, items, self.settings.STOCK_DATA_CACHE_SECONDS)
        return items

    def get_stock_detail(self, stock_id: str) -> StockDetail:
        market, stock_code = self.normalize_stock_id(stock_id)
        search_match = self._resolve_stock_search_item(stock_id)
        quote_snapshot = self._fetch_quote_snapshot(market, stock_code)
        recent_history = self._fetch_recent_history(market, stock_code)
        company_profile = self._fetch_company_profile(market, stock_code)
        stock_name = (
            (search_match.stock_name if search_match else None)
            or self._extract_name_from_profile(company_profile)
            or f"{market}{stock_code}"
        )
        recent_events = self._fetch_recent_events(stock_code, stock_name)
        industry = (
            (search_match.industry if search_match else None)
            or company_profile.board_name
            or self._infer_industry_from_profile(company_profile)
        )
        detail = StockDetail(
            stock_id=f"{market}{stock_code}",
            stock_code=stock_code,
            stock_name=stock_name,
            market=market,
            industry=industry,
            security_type=search_match.security_type if search_match else None,
            pinyin=search_match.pinyin if search_match else None,
            quote_id=search_match.quote_id if search_match else None,
            quote_snapshot=quote_snapshot,
            company_profile=company_profile,
            recent_events=recent_events,
            recent_history=recent_history,
            data_sources=[
                "腾讯行情",
                "腾讯历史K线",
                "东方财富搜索",
                "东方财富个股页",
                "东方财富公告",
            ],
        )
        return detail

    def normalize_stock_id(self, value: str) -> tuple[str, str]:
        raw = value.strip().upper()
        if re.fullmatch(r"(SH|SZ|BJ)\d{6}", raw):
            return raw[:2], raw[2:]
        if re.fullmatch(r"\d{6}\.(SH|SZ|BJ)", raw):
            return raw[-2:], raw[:6]
        if re.fullmatch(r"\d{6}", raw):
            return self._guess_market(raw), raw
        raise ValueError(f"Unsupported stock identifier: {value}")

    def close(self):
        self.client.close()

    def _resolve_stock_search_item(self, stock_id: str) -> Optional[StockSearchItem]:
        market, stock_code = self.normalize_stock_id(stock_id)
        matches = self.search_stocks(stock_code, limit=5)
        exact = next((item for item in matches if item.stock_id == f"{market}{stock_code}"), None)
        return exact or (matches[0] if matches else None)

    def _fetch_quote_snapshot(self, market: str, stock_code: str) -> Optional[StockQuoteSnapshot]:
        cache_key = f"quote:{market}:{stock_code}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        symbol = f"{market.lower()}{stock_code}"
        text = self.client.get(self.QUOTE_URL.format(symbol=symbol)).text
        parts = self._parse_tencent_quote(text)
        if not parts:
            return None

        snapshot = StockQuoteSnapshot(
            latest_price=self._to_float(parts, 3),
            previous_close=self._to_float(parts, 4),
            open_price=self._to_float(parts, 5),
            change_amount=self._to_float(parts, 31),
            change_percent=self._to_float(parts, 32),
            high_price=self._to_float(parts, 33),
            low_price=self._to_float(parts, 34),
            volume=self._to_float(parts, 36),
            amount=self._to_float(parts, 37, multiplier=10000),
            turnover_rate=self._to_float(parts, 38),
            pe_ratio=self._to_float(parts, 39),
            amplitude=self._to_float(parts, 43),
            total_market_cap=self._to_float(parts, 44, multiplier=100000000),
            circulating_market_cap=self._to_float(parts, 45, multiplier=100000000),
            pb_ratio=self._to_float(parts, 46),
            data_as_of=self._parse_tencent_datetime(parts[30] if len(parts) > 30 else None),
        )
        self.cache.set(cache_key, snapshot, self.settings.STOCK_DATA_CACHE_SECONDS)
        return snapshot

    def _fetch_recent_history(
        self, market: str, stock_code: str, limit: int = 30
    ) -> list[StockHistoryPoint]:
        cache_key = f"history:{market}:{stock_code}:{limit}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        symbol = f"{market.lower()}{stock_code}"
        response = self._request_json(
            self.HISTORY_URL,
            params={"param": f"{symbol},day,,,90,qfq"},
        )
        raw_points = (((response or {}).get("data") or {}).get(symbol) or {}).get("qfqday") or []
        points: list[StockHistoryPoint] = []
        for row in raw_points[-limit:]:
            try:
                points.append(
                    StockHistoryPoint(
                        date=datetime.strptime(row[0], "%Y-%m-%d").replace(tzinfo=CN_TZ),
                        open_price=float(row[1]),
                        close_price=float(row[2]),
                        high_price=float(row[3]),
                        low_price=float(row[4]),
                        volume=float(row[5]),
                    )
                )
            except (TypeError, ValueError, IndexError):
                continue

        self.cache.set(cache_key, points, self.settings.STOCK_DATA_CACHE_SECONDS)
        return points

    def _fetch_company_profile(self, market: str, stock_code: str) -> StockCompanyProfile:
        cache_key = f"profile:{market}:{stock_code}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        symbol = f"{market.lower()}{stock_code}"
        url = self.QUOTE_PAGE_URL.format(symbol=symbol)
        html = self.client.get(url).text

        description_match = re.search(
            r'<meta name="description" content="([^"]+)"', html, flags=re.IGNORECASE
        )
        description = unescape(description_match.group(1)).strip() if description_match else None

        board_name = None
        json_match = re.search(
            rf'(\{{"name":"[^"]+","code":"{stock_code}".*?"bk_name":"[^"]*".*?\}})',
            html,
        )
        if json_match:
            try:
                meta = json.loads(json_match.group(1))
                board_name = meta.get("bk_name")
            except json.JSONDecodeError:
                board_name = None

        profile = StockCompanyProfile(
            description=description,
            business_scope=self._extract_business_scope(description),
            board_name=board_name,
            listing_date=None,
            source_url=url,
        )
        self.cache.set(cache_key, profile, self.settings.STOCK_DATA_CACHE_SECONDS)
        return profile

    def _fetch_recent_events(
        self, stock_code: str, stock_name: str, limit: int = 5
    ) -> list[StockEvent]:
        cache_key = f"events:{stock_code}:{limit}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        end_time = datetime.now(CN_TZ)
        begin_time = end_time - timedelta(days=self.settings.STOCK_NOTICE_LOOKBACK_DAYS)
        events: list[StockEvent] = []

        for page_index in range(1, 6):
            payload = self._request_json(
                self.NOTICE_URL,
                params={
                    "sr": "-1",
                    "page_size": "100",
                    "page_index": str(page_index),
                    "ann_type": "A",
                    "client_source": "web",
                    "f_node": "0",
                    "s_node": "0",
                    "begin_time": begin_time.strftime("%Y-%m-%d"),
                    "end_time": end_time.strftime("%Y-%m-%d"),
                },
            )
            rows = ((payload or {}).get("data") or {}).get("list") or []
            if not rows:
                break

            for row in rows:
                codes = row.get("codes") or []
                matched = any((code_item or {}).get("stock_code") == stock_code for code_item in codes)
                if not matched:
                    continue
                columns = row.get("columns") or []
                event_type = columns[0].get("column_name") if columns else None
                url = f"https://data.eastmoney.com/notices/detail/{stock_code}/{row.get('art_code')}.html"
                events.append(
                    StockEvent(
                        title=str(row.get("title") or stock_name),
                        event_type=event_type,
                        published_at=self._parse_notice_datetime(row.get("notice_date")),
                        url=url,
                        source="eastmoney_notice",
                    )
                )
                if len(events) >= limit:
                    self.cache.set(cache_key, events, self.settings.STOCK_DATA_CACHE_SECONDS)
                    return events

        self.cache.set(cache_key, events, self.settings.STOCK_DATA_CACHE_SECONDS)
        return events

    def _request_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        response = self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def _parse_tencent_quote(self, payload: str) -> list[str]:
        match = re.search(r'"([^"]+)"', payload)
        if not match:
            return []
        return match.group(1).split("~")

    def _parse_tencent_datetime(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=CN_TZ)
        except ValueError:
            return None

    def _parse_notice_datetime(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        cleaned = value.replace(" 00:00:00", "")
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(cleaned, fmt).replace(tzinfo=CN_TZ)
            except ValueError:
                continue
        return None

    def _to_float(
        self, parts: list[str], index: int, multiplier: float = 1.0
    ) -> Optional[float]:
        if index >= len(parts):
            return None
        raw = parts[index]
        if raw in {"", "-", "--"}:
            return None
        try:
            return float(raw) * multiplier
        except ValueError:
            return None

    def _market_from_search_row(self, row: dict[str, Any]) -> Optional[str]:
        security_type = str(row.get("SecurityTypeName") or "")
        market_type = str(row.get("MarketType") or "")
        stock_code = str(row.get("Code") or "")

        if "沪A" in security_type or market_type == "1":
            return "SH"
        if "深A" in security_type or market_type == "2":
            return "SZ"
        if "京A" in security_type or stock_code.startswith(("4", "8")):
            return "BJ"
        return None

    def _guess_market(self, stock_code: str) -> str:
        if stock_code.startswith(("600", "601", "603", "605", "688", "689")):
            return "SH"
        if stock_code.startswith(("000", "001", "002", "003", "300", "301")):
            return "SZ"
        if stock_code.startswith(("430", "831", "832", "833", "834", "835", "836", "837", "838", "839", "870", "871", "872", "873", "874", "875", "876", "877", "878", "879", "880", "881", "882", "883", "884", "885", "886", "887", "888", "889")):
            return "BJ"
        return "SZ"

    def _infer_match_type(
        self, query: str, stock_code: str, row: dict[str, Any]
    ) -> str:
        upper_query = query.upper()
        if upper_query == stock_code:
            return "code"
        if upper_query == str(row.get("PinYin") or "").upper():
            return "pinyin"
        return "name"

    def _extract_business_scope(self, description: Optional[str]) -> Optional[str]:
        if not description:
            return None
        return description[:140]

    def _extract_name_from_profile(
        self, profile: Optional[StockCompanyProfile]
    ) -> Optional[str]:
        if not profile or not profile.description:
            return None
        match = re.search(r"提供([^()（）]+)\(", profile.description)
        if match:
            return match.group(1).strip()
        return None

    def _infer_industry_from_profile(
        self, profile: Optional[StockCompanyProfile]
    ) -> Optional[str]:
        if not profile:
            return None
        return profile.board_name
