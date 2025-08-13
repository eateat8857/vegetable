import os
import requests
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from zhdate import ZhDate

# 從環境變數讀取（用 GitHub Secrets 提供）
CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
USER_IDS = [u.strip() for u in os.environ.get("LINE_USER_ID", "").split(",") if u.strip()]
TZ_NAME = os.environ.get("TZ", "Asia/Taipei")

def lunar_day(d: date) -> int:
    """回傳農曆日（1~30）。為相容 zhdate 舊版，使用 datetime 物件。"""
    z = ZhDate.from_datetime(datetime(d.year, d.month, d.day))
    return z.lunar_day

def is_chuyi_or_shiwu(d: date) -> bool:
    return lunar_day(d) in (1, 15)

def find_next_chuyi_or_shiwu(start_date: date, include_today: bool = False) -> date:
    """往後逐日尋找最近的農曆初一或十五。"""
    d = start_date if include_today else start_date + timedelta(days=1)
    for _ in range(120):  # 足夠跨一～兩個月
        if is_chuyi_or_shiwu(d):
            return d
        d += timedelta(days=1)
    raise RuntimeError("找不到下一次的農曆初一/十五，請檢查 zhdate。")

def send_line_push(user_id: str, text: str):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {"to": user_id, "messages": [{"type": "text", "text": text}]}
    r = requests.post(url, headers=headers, json=data, timeout=15)
    r.raise_for_status()

def main():
    if not CHANNEL_ACCESS_TOKEN or not USER_IDS:
        raise RuntimeError("缺少必要環境變數：LINE_CHANNEL_ACCESS_TOKEN 或 LINE_USER_ID")

    tz = ZoneInfo(TZ_NAME)
    now = datetime.now(tz)
    today = now.date()

    today_is_target = is_chuyi_or_shiwu(today)
    next_date = find_next_chuyi_or_shiwu(today, include_today=not today_is_target)

    solar_now = now.strftime("%Y-%m-%d %H:%M")
    next_solar = next_date.strftime("%Y-%m-%d")
    today_lday = lunar_day(today)  # 只顯示日，避免舊版差異
    today_lunar_str = f"農曆{today_lday}日"

    if today_is_target:
        msg = (
            "🌱 吃素提醒\n"
            f"今天是 {today_lunar_str}，記得吃素喔！\n"
            f"國曆：{solar_now}（{TZ_NAME}）\n"
            f"🔔 下一次提醒：{next_solar}"
        )
        for uid in USER_IDS:
            send_line_push(uid, msg)
        print("[OK] 已推播：", msg)
    else:
        # 不是 1/15 就不推播，只印 log（需要每天都通知可自行改成也推）
        print(f"[SKIP] 今天 {today_lunar_str}；現在 {solar_now}；下一次提醒：{next_solar}")

if __name__ == "__main__":
    main()
