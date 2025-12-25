"""입찰공고 알림 - GitHub Actions용"""
import requests
from datetime import datetime
from core.config import load_env, load_settings
from core.db import open_db, BidNotice
from collectors.nara_bids import NaraBidsCollector


def send_telegram(token: str, chat_id: str, message: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"텔레그램 발송 실패: {e}")
        return False


def format_bid_message(bid: BidNotice) -> str:
    budget_str = f"{bid.budget:,.0f}원" if bid.budget else "미정"
    close_str = str(bid.bid_close_dt)[:16] if bid.bid_close_dt else "미정"

    return f"""📢 <b>새 입찰공고</b>

📌 <b>{bid.title[:50]}{'...' if len(bid.title) > 50 else ''}</b>

🏛 발주기관: {bid.org or '-'}
💰 추정가: {budget_str}
⏰ 마감: {close_str}
🎯 매칭키워드: {bid.matched_keywords or '-'}

🔗 <a href="{bid.url or '#'}">공고 바로가기</a>
"""


def check_and_notify(days_back: int = 1) -> dict:
    env = load_env()
    settings = load_settings()
    db = open_db(env.db_path)

    token = env.telegram_token
    chat_id = env.telegram_chat_id

    if not token or not chat_id:
        print("오류: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID 없음")
        return {"error": "텔레그램 설정 없음"}

    if not env.has_data_go_kr:
        print("오류: DATA_GO_KR_SERVICE_KEY 없음")
        return {"error": "API 키 없음"}

    # 기존 공고 ID
    with db.SessionLocal() as session:
        existing_ids = set(b.id for b in session.query(BidNotice).all())

    # 공고 수집
    print(f"[입찰공고 수집] 최근 {days_back}일")
    result = NaraBidsCollector(db, settings, env).collect(days_back=days_back)

    # 새로 추가된 공고
    new_bids = []
    with db.SessionLocal() as session:
        for bid in session.query(BidNotice).all():
            if bid.id not in existing_ids:
                new_bids.append(bid)

    print(f"신규 공고: {len(new_bids)}개")

    # 알림 발송 (점수 20 이상만)
    sent = 0
    for bid in new_bids:
        if bid.score >= 20:
            msg = format_bid_message(bid)
            if send_telegram(token, chat_id, msg):
                sent += 1
                print(f"  📢 알림: {bid.title[:20]}...")

    # 요약 메시지
    if new_bids:
        summary = f"""📊 <b>입찰공고 수집 완료</b>

🆕 신규: {len(new_bids)}개
📢 알림: {sent}개 (점수 20+)
🕐 수집시간: {datetime.now().strftime('%m/%d %H:%M')}
"""
        send_telegram(token, chat_id, summary)

    return {
        "collected": result.inserted,
        "new_bids": len(new_bids),
        "notified": sent
    }


if __name__ == "__main__":
    result = check_and_notify(days_back=3)
    print(f"\n완료: {result}")
