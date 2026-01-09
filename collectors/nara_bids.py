"""나라장터 입찰공고 수집기"""
from __future__ import annotations
import datetime as dt
import json
import requests
from typing import Any, Dict, List
from collectors.base import BaseCollector, CollectResult
from core.db import BidNotice


class NaraBidsCollector(BaseCollector):
    source_name = "nara_bids"

    def collect(self, days_back: int = 7, **kwargs) -> CollectResult:
        if not self.env.has_data_go_kr:
            return CollectResult(self.source_name, 0, 0, 0, 1, "API 키 없음")

        api_cfg = self.settings.get_api("nara")
        base_url = api_cfg.get("base_url", "https://apis.data.go.kr/1230000/ad/BidPublicInfoService")
        endpoints = api_cfg.get("endpoints", [
            {"name": "construction", "path": "/getBidPblancListInfoCnstwk"},
            {"name": "service", "path": "/getBidPblancListInfoServc"},
            {"name": "goods", "path": "/getBidPblancListInfoThng"},
        ])

        end_dt = dt.datetime.now()
        start_dt = end_dt - dt.timedelta(days=days_back)

        all_bids = []
        errors = 0

        for ep in endpoints:
            try:
                bids = self._fetch_endpoint(base_url, ep, start_dt, end_dt)
                all_bids.extend(bids)
                print(f"  {ep['name']}: {len(bids)}개")
            except Exception as e:
                print(f"  {ep['name']} 오류: {e}")
                errors += 1

        matched = self._score_and_save(all_bids)

        result = CollectResult(self.source_name, len(all_bids), matched, 0, errors)
        self.update_sync_log(result)
        return result

    def _fetch_endpoint(self, base_url: str, ep: Dict, start_dt: dt.datetime, end_dt: dt.datetime) -> List[Dict]:
        url = base_url + ep["path"]
        bids = []
        page = 1

        while page <= 10:
            params = {
                "serviceKey": self.env.data_go_kr_key,
                "type": "json",
                "pageNo": str(page),
                "numOfRows": "100",
                "inqryDiv": "1",
                "inqryBgnDt": start_dt.strftime("%Y%m%d") + "0000",
                "inqryEndDt": end_dt.strftime("%Y%m%d") + "2359",
            }

            try:
                resp = requests.get(url, params=params, timeout=30)
                data = resp.json()
            except Exception as e:
                break

            items = self._parse_response(data)
            if not items:
                break

            for item in items:
                item["endpoint"] = ep["name"]
                bids.append(item)

            if len(items) < 100:
                break
            page += 1

        return bids

    def _parse_response(self, data: Dict) -> List[Dict]:
        if "response" not in data:
            return []
        body = data["response"].get("body", {})
        items = body.get("items", [])
        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):
            items = [items]
        return items if isinstance(items, list) else []

    def _score_and_save(self, bids: List[Dict]) -> int:
        keywords_high = set(kw.lower() for kw in self.settings.keywords_high_intent)
        keywords_fac = set(kw.lower() for kw in self.settings.keywords_facilities)
        
        # 제외 키워드 로드
        exclude_keywords = set()
        if hasattr(self.settings, 'keywords_exclude'):
            exclude_keywords = set(kw.lower() for kw in self.settings.keywords_exclude)
        
        regions = set(self.settings.regions)
        scoring = self.settings.scoring

        saved_count = 0

        with self.db.SessionLocal() as session:
            for bid in bids:
                title = str(bid.get("bidNtceNm", "") or "")
                org = str(bid.get("ntceInsttNm", "") or "")
                demand = str(bid.get("dminsttNm", "") or "")
                text = (title + " " + org + " " + demand).lower()

                # 제외 키워드 체크 - 있으면 스킵
                if any(ex in text for ex in exclude_keywords):
                    continue

                score = 0
                matched = []

                for kw in keywords_high:
                    if kw in text:
                        score += scoring.get("keyword_high_intent", 15)
                        matched.append(kw)

                for kw in keywords_fac:
                    if kw in text:
                        score += scoring.get("keyword_facility", 8)
                        matched.append(kw)

                is_capital = any(r in text for r in regions)
                if is_capital:
                    score += scoring.get("region_match", 10)

                if not is_capital:
                    continue
                 # high_intent 키워드가 최소 1개 이상 있어야 알림
                has_high_intent = any(kw in matched for kw in keywords_high)
                if not has_high_intent:
                    continue
                bid_no = bid.get("bidNtceNo", "")
                bid_ord = str(bid.get("bidNtceOrd", "00"))
                endpoint = bid.get("endpoint", "")

                if not bid_no:
                    continue

                existing = session.query(BidNotice).filter(
                    BidNotice.endpoint == endpoint,
                    BidNotice.bid_ntce_no == bid_no,
                    BidNotice.bid_ntce_ord == bid_ord
                ).first()

                if not existing:
                    notice = BidNotice(
                        endpoint=endpoint,
                        bid_ntce_no=bid_no,
                        bid_ntce_ord=bid_ord,
                        title=title,
                        org=org,
                        demand_org=demand,
                        budget=self.safe_float(bid.get("presmptPrce")),
                        bid_begin_dt=str(bid.get("bidBeginDt", "")),
                        bid_close_dt=str(bid.get("bidClseDt", "")),
                        url=str(bid.get("bidNtceDtlUrl", "")),
                        score=min(score, 100),
                        matched_keywords=json.dumps(matched, ensure_ascii=False),
                        raw_data=json.dumps(bid, ensure_ascii=False, default=str),
                        contact_name=str(bid.get("ntceInsttOfclNm", "") or ""),
                        contact_phone=str(bid.get("ntceInsttOfclTelNo", "") or ""),
                        contact_email=str(bid.get("ntceInsttOfclEmailAdrs", "") or ""),
                    )
                    session.add(notice)
                    saved_count += 1

            session.commit()

        return saved_count
