from __future__ import annotations

import json
import os
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
        self.mock_enabled = self._mock_market_enabled()
        self.client: httpx.Client | None = None
        if not self.mock_enabled:
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
        if self.mock_enabled:
            return self._mock_search_stocks(normalized_query, limit)

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

    def _get_stock_detail_legacy_unused(self, stock_id: str) -> StockDetail:
        if self.mock_enabled:
            return self._mock_stock_detail(stock_id)

        market, stock_code = self.normalize_stock_id(stock_id)
        search_match = self._safe_call(
            "stock_search_match_failed",
            lambda: self._resolve_stock_search_item(stock_id),
            stock_code=stock_code,
            default=None,
        )
        quote_snapshot = self._safe_call(
            "quote_snapshot_failed",
            lambda: self._fetch_quote_snapshot(market, stock_code),
            stock_code=stock_code,
            default=None,
        )
        recent_history = self._safe_call(
            "recent_history_failed",
            lambda: self._fetch_recent_history(market, stock_code),
            stock_code=stock_code,
            default=[],
        )
        company_profile = self._safe_call(
            "company_profile_failed",
            lambda: self._fetch_company_profile(market, stock_code),
            stock_code=stock_code,
            default=StockCompanyProfile(
                description=None,
                business_scope=None,
                board_name=None,
                listing_date=None,
                source_url=self.QUOTE_PAGE_URL.format(symbol=f"{market.lower()}{stock_code}"),
            ),
        )
        stock_name = (
            (search_match.stock_name if search_match else None)
            or self._extract_name_from_profile(company_profile)
            or f"{market}{stock_code}"
        )
        recent_events = self._safe_call(
            "recent_events_failed",
            lambda: self._fetch_recent_events(stock_code, stock_name),
            stock_code=stock_code,
            default=[],
        )
        industry = (
            (search_match.industry if search_match else None)
            or company_profile.board_name
            or self._infer_industry_from_profile(company_profile)
        )
        data_sources: list[str] = []
        if quote_snapshot:
            data_sources.append("tencent_quote")
        if recent_history:
            data_sources.append("tencent_history")
        if search_match:
            data_sources.append("eastmoney_search")
        if company_profile and (company_profile.description or company_profile.board_name):
            data_sources.append("eastmoney_profile")
        if recent_events:
            data_sources.append("cninfo_announcements")
        if not data_sources:
            data_sources.append("external_market_data_degraded")

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
                "巨潮资讯公告",
            ],
        )
        return detail

    def get_stock_detail(self, stock_id: str) -> StockDetail:
        if self.mock_enabled:
            return self._mock_stock_detail(stock_id)

        market, stock_code = self.normalize_stock_id(stock_id)
        symbol = f"{market.lower()}{stock_code}"
        profile_default = StockCompanyProfile(
            description=None,
            business_scope=None,
            board_name=None,
            listing_date=None,
            source_url=self.QUOTE_PAGE_URL.format(symbol=symbol),
        )

        search_match = self._safe_call(
            "stock_search_match_failed",
            lambda: self._resolve_stock_search_item(stock_id),
            default=None,
            stock_code=stock_code,
        )
        quote_snapshot = self._safe_call(
            "quote_snapshot_failed",
            lambda: self._fetch_quote_snapshot(market, stock_code),
            default=None,
            stock_code=stock_code,
        )
        recent_history = self._safe_call(
            "recent_history_failed",
            lambda: self._fetch_recent_history(market, stock_code),
            default=[],
            stock_code=stock_code,
        )
        company_profile = self._safe_call(
            "company_profile_failed",
            lambda: self._fetch_company_profile(market, stock_code),
            default=profile_default,
            stock_code=stock_code,
        )
        stock_name = (
            (search_match.stock_name if search_match else None)
            or self._extract_name_from_profile(company_profile)
            or f"{market}{stock_code}"
        )
        recent_events = self._safe_call(
            "recent_events_failed",
            lambda: self._fetch_recent_events(stock_code, stock_name),
            default=[],
            stock_code=stock_code,
        )
        industry = (
            (search_match.industry if search_match else None)
            or company_profile.board_name
            or self._infer_industry_from_profile(company_profile)
        )

        data_sources: list[str] = []
        if quote_snapshot:
            data_sources.append("tencent_quote")
        if recent_history:
            data_sources.append("tencent_history")
        if search_match:
            data_sources.append("eastmoney_search")
        if company_profile and (company_profile.description or company_profile.board_name):
            data_sources.append("eastmoney_profile")
        if recent_events:
            data_sources.append("cninfo_announcements")
        if not data_sources:
            data_sources.append("external_market_data_degraded")

        return StockDetail(
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
            data_sources=data_sources,
        )

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
        if self.client is not None:
            self.client.close()

    def _mock_market_enabled(self) -> bool:
        value = (
            os.getenv("E2E_MOCK_MARKET")
            or os.getenv("MOCK_MARKET_DATA")
            or ""
        )
        return value.strip().lower() in {"1", "true", "yes", "on"}

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

        events: list[StockEvent] = []

        # Step 1: 通过 cninfo 搜索 API 查找该股票的 orgId
        orgid = self._lookup_cninfo_orgid(stock_code)
        if not orgid:
            self.logger.warning("cninfo_orgid_not_found", stock_code=stock_code)
            self.cache.set(cache_key, events, self.settings.STOCK_DATA_CACHE_SECONDS)
            return events

        # Step 2: 向 cninfo 公告 API 发 POST 请求（cninfo 不支持 GET）
        end_time = datetime.now(CN_TZ)
        begin_time = end_time - timedelta(days=self.settings.STOCK_NOTICE_LOOKBACK_DAYS)

        # cninfo 需要自己的请求头（Referer 必须指向 cninfo.com.cn）
        cninfo_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.cninfo.com.cn/",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        cninfo_client = httpx.Client(timeout=self.settings.STOCK_DATA_TIMEOUT)

        try:
            form_data = {
                "pageNum": "1",
                "pageSize": str(limit),
                "tabName": "fulltext",
                "stock": f"{stock_code},{orgid}",
                "searchkey": "",
                "secid": "",
                "category": "",
                "trade": "",
                "column": "sse",
                "dbclick": "2",
                "isHLtitle": "true",
                "beginTime": begin_time.strftime("%Y-%m-%d"),
                "endTime": end_time.strftime("%Y-%m-%d"),
            }
            response = cninfo_client.post(
                "https://www.cninfo.com.cn/new/hisAnnouncement/query",
                headers=cninfo_headers,
                data=form_data,
            )
            response.raise_for_status()
            payload = response.json()

        except httpx.HTTPError as exc:
            self.logger.warning("cninfo_request_failed", stock_code=stock_code, error=str(exc))
            self.cache.set(cache_key, events, self.settings.STOCK_DATA_CACHE_SECONDS)
            return events
        finally:
            cninfo_client.close()

        # Step 3: 解析 announcements 列表（cninfo 将其放在响应顶层，非 result 字段）
        announcements = payload.get("announcements") or []
        for ann in announcements:
            ts_ms = ann.get("announcementTime")
            if ts_ms:
                published_at = datetime.fromtimestamp(int(ts_ms) / 1000, CN_TZ)
            else:
                published_at = None

            ann_id = ann.get("announcementId")
            # 新版巨潮以 announcementId 构造披露页 URL，不再依赖 adjunctUrl（旧版路径已下线）
            full_url = (
                f"https://www.cninfo.com.cn/new/disclosure/announcement/{ann_id}"
                if ann_id
                else ""
            )

            events.append(
                StockEvent(
                    title=str(ann.get("announcementTitle") or stock_name),
                    event_type=None,  # columnId 需额外映射，暂不填
                    published_at=published_at,
                    url=full_url,
                    source="cninfo",
                )
            )

        self.cache.set(cache_key, events, self.settings.STOCK_DATA_CACHE_SECONDS)
        return events

    def _lookup_cninfo_orgid(self, stock_code: str) -> Optional[str]:
        """通过 cninfo 搜索 API 查找股票对应的 orgId。

        cninfo 公告接口需要 stock={code},{orgId} 格式的精确参数，
        无法像 East Money np-anotice-stock 那样做全量流式扫描，
        因此必须先通过本方法获取 orgId。

        注意：cninfo API 要求 Referer 指向 cninfo.com.cn，
        与 MarketDataService 主 client 的 East Money Referer 冲突，
        所以这里创建独立 client。
        """
        cninfo_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.cninfo.com.cn/",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        cninfo_client = httpx.Client(timeout=self.settings.STOCK_DATA_TIMEOUT)
        try:
            response = cninfo_client.post(
                "https://www.cninfo.com.cn/new/information/topSearch/query",
                headers=cninfo_headers,
                data={
                    "pageNum": "1",
                    "pageSize": "5",
                    "keyWord": stock_code,
                    "tradeName": "",
                    "subType": "",
                },
            )
            response.raise_for_status()
            # cninfo 搜索返回的是列表，非 JSON object
            results = response.json()
            if not isinstance(results, list):
                return None
            # 精确匹配 code
            code_normalized = stock_code.lstrip("0") or "0"
            for item in results:
                item_code = str(item.get("code") or "").lstrip("0") or "0"
                if item_code == code_normalized:
                    return item.get("orgId")
            return None
        except httpx.HTTPError:
            return None
        finally:
            cninfo_client.close()

    def _request_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        if self.client is None:
            raise RuntimeError("real market data client is not initialized")
        response = self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def _safe_call(self, event: str, func, default: Any, **log_context: Any) -> Any:
        try:
            return func()
        except (httpx.HTTPError, json.JSONDecodeError, ValueError, TypeError, KeyError) as exc:
            self.logger.warning(event, error=str(exc), **log_context)
            return default

    def _mock_search_stocks(self, query: str, limit: int) -> list[StockSearchItem]:
        normalized = query.strip().upper()
        matches = [
            item for item in self._mock_stock_universe()
            if normalized in item["stock_id"].upper()
            or normalized in item["stock_code"]
            or normalized in item["stock_name"]
        ]
        return [
            StockSearchItem(
                stock_id=item["stock_id"],
                stock_code=item["stock_code"],
                stock_name=item["stock_name"],
                market=item["market"],
                industry=item["industry"],
                security_type="AStock",
                pinyin=item["pinyin"],
                quote_id=item["stock_id"],
                matched_by="mock",
            )
            for item in matches[:limit]
        ]

    def _mock_stock_detail(self, stock_id: str) -> StockDetail:
        market, stock_code = self.normalize_stock_id(stock_id)
        normalized_id = f"{market}{stock_code}"
        item = next(
            (row for row in self._mock_stock_universe() if row["stock_id"] == normalized_id),
            None,
        )
        if item is None:
            raise ValueError(f"Unsupported stock identifier: {stock_id}")

        data_as_of = datetime(2026, 4, 30, 15, 0, tzinfo=CN_TZ)
        base_price = float(item["base_price"])
        change_percent = float(item["change_percent"])
        previous_close = round(base_price / (1 + change_percent / 100), 2)
        history = self._mock_history(base_price)
        events = [
            StockEvent(
                title=f"{item['stock_name']}2026年第一季度主要经营数据公告",
                event_type="公司公告",
                published_at=datetime(2026, 4, 29, 9, 0, tzinfo=CN_TZ),
                url=f"https://mock.local/announcements/{normalized_id}/q1",
                source="mock",
            ),
            StockEvent(
                title=f"{item['stock_name']}关于召开业绩说明会的公告",
                event_type="公司公告",
                published_at=datetime(2026, 4, 28, 9, 0, tzinfo=CN_TZ),
                url=f"https://mock.local/announcements/{normalized_id}/briefing",
                source="mock",
            ),
        ]

        return StockDetail(
            stock_id=normalized_id,
            stock_code=stock_code,
            stock_name=item["stock_name"],
            market=market,
            industry=item["industry"],
            security_type="AStock",
            pinyin=item["pinyin"],
            quote_id=normalized_id,
            quote_snapshot=StockQuoteSnapshot(
                latest_price=base_price,
                change_amount=round(base_price - previous_close, 2),
                change_percent=change_percent,
                open_price=round(previous_close * 1.002, 2),
                high_price=round(base_price * 1.015, 2),
                low_price=round(base_price * 0.985, 2),
                previous_close=previous_close,
                volume=52800,
                amount=base_price * 52800,
                turnover_rate=0.42,
                pe_ratio=float(item["pe_ratio"]),
                pb_ratio=float(item["pb_ratio"]),
                total_market_cap=base_price * 1_000_000_000,
                circulating_market_cap=base_price * 800_000_000,
                amplitude=3.0,
                data_as_of=data_as_of,
            ),
            company_profile=StockCompanyProfile(
                description=f"{item['stock_name']} 是 E2E mock 行情模式下的稳定测试标的，用于验证分析、证据卡、复盘与提醒链路。",
                business_scope="E2E mock data",
                board_name=item["industry"],
                listing_date="2001-08-27",
                source_url=f"https://mock.local/stocks/{normalized_id}",
            ),
            recent_events=events,
            recent_history=history,
            data_sources=["E2E Mock Quote", "E2E Mock History", "E2E Mock Announcements"],
        )

    def _mock_history(self, latest_price: float) -> list[StockHistoryPoint]:
        points: list[StockHistoryPoint] = []
        start = datetime(2026, 3, 20, tzinfo=CN_TZ)
        for index in range(30):
            close = round(latest_price * (0.94 + index * 0.002), 2)
            open_price = round(close * 0.997, 2)
            points.append(
                StockHistoryPoint(
                    date=start + timedelta(days=index),
                    open_price=open_price,
                    close_price=close,
                    high_price=round(close * 1.012, 2),
                    low_price=round(close * 0.988, 2),
                    volume=50_000 + index * 100,
                )
            )
        points[-1].close_price = latest_price
        return points

    def _mock_stock_universe(self) -> list[dict[str, Any]]:
        return [
            {
                "stock_id": "SH600519",
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "market": "SH",
                "industry": "白酒",
                "pinyin": "GZMT",
                "base_price": 1384.79,
                "change_percent": -1.17,
                "pe_ratio": 20.97,
                "pb_ratio": 6.40,
            },
            {
                "stock_id": "SZ002594",
                "stock_code": "002594",
                "stock_name": "比亚迪",
                "market": "SZ",
                "industry": "汽车",
                "pinyin": "BYD",
                "base_price": 218.60,
                "change_percent": 2.36,
                "pe_ratio": 28.30,
                "pb_ratio": 5.10,
            },
            {
                "stock_id": "SZ300750",
                "stock_code": "300750",
                "stock_name": "宁德时代",
                "market": "SZ",
                "industry": "电池",
                "pinyin": "NDSD",
                "base_price": 192.40,
                "change_percent": 3.20,
                "pe_ratio": 24.80,
                "pb_ratio": 4.20,
            },
            {
                "stock_id": "SH600036",
                "stock_code": "600036",
                "stock_name": "招商银行",
                "market": "SH",
                "industry": "银行",
                "pinyin": "ZSYH",
                "base_price": 38.12,
                "change_percent": -0.65,
                "pe_ratio": 6.50,
                "pb_ratio": 0.95,
            },
            {
                "stock_id": "SZ000001",
                "stock_code": "000001",
                "stock_name": "平安银行",
                "market": "SZ",
                "industry": "银行",
                "pinyin": "PAYH",
                "base_price": 11.20,
                "change_percent": 1.12,
                "pe_ratio": 5.80,
                "pb_ratio": 0.72,
            },
            {
                "stock_id": "SH601012",
                "stock_code": "601012",
                "stock_name": "隆基绿能",
                "market": "SH",
                "industry": "光伏",
                "pinyin": "LJLN",
                "base_price": 18.42,
                "change_percent": -2.10,
                "pe_ratio": 18.60,
                "pb_ratio": 1.45,
            },
            {
                "stock_id": "SH600900",
                "stock_code": "600900",
                "stock_name": "长江电力",
                "market": "SH",
                "industry": "电力",
                "pinyin": "CJDL",
                "base_price": 26.80,
                "change_percent": 0.88,
                "pe_ratio": 22.10,
                "pb_ratio": 3.10,
            },
        ]

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
