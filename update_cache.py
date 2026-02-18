#!/usr/bin/env python
"""
update_cache.py
– 未来日の在庫・平均(最低)料金を取得して
  vacancy_price_cache.json / historical_data.json / demand_spike_history.json を更新
  ＋ GitHub Actions 実行完了のJST時刻を last_updated.json に書き出す

※ 重要: 『平均価格』は “各ホテルの当日最安値(最低価格) の平均” に統一
"""

import os
import sys
import json
import calendar
import requests
import datetime as dt
from pathlib import Path
from dateutil.relativedelta import relativedelta


# ============================================================
# Rakuten API credentials (V1 / V2)
#  - 無事故方針：V2の環境変数が揃っている時だけV2を使い、
#               無ければ従来どおりV1で動かす
# ============================================================
APP_ID_V1 = os.environ.get("RAKUTEN_APP_ID", "").strip()

APP_ID_V2 = os.environ.get("RAKUTEN_APP_ID_V2", "").strip()
ACCESS_KEY_V2 = os.environ.get("RAKUTEN_ACCESS_KEY_V2", "").strip()

# 任意：強制モード（auto / v1 / v2） ※未設定なら auto
API_MODE = os.environ.get("RAKUTEN_API_MODE", "auto").strip().lower()

USE_V2 = (API_MODE == "v2") or (API_MODE == "auto" and APP_ID_V2 and ACCESS_KEY_V2)

if USE_V2:
    if not APP_ID_V2 or not ACCESS_KEY_V2:
        raise ValueError("❌ V2モードなのに RAKUTEN_APP_ID_V2 / RAKUTEN_ACCESS_KEY_V2 が未設定です。")
else:
    if not APP_ID_V1:
        raise ValueError("❌ RAKUTEN_APP_ID が設定されていません。GitHub Secrets に登録してください。")

# 既存コード互換用：APP_ID は「今使う方」を入れておく
APP_ID = APP_ID_V2 if USE_V2 else APP_ID_V1

# エンドポイント（V1 / V2）
RAKUTEN_API_URL_V1 = "https://app.rakuten.co.jp/services/api/Travel/VacantHotelSearch/20170426"
RAKUTEN_API_URL_V2 = "https://openapi.rakuten.co.jp/engine/api/Travel/VacantHotelSearch/20170426"
RAKUTEN_API_URL = RAKUTEN_API_URL_V2 if USE_V2 else RAKUTEN_API_URL_V1

# V2は Referer/Origin が必要になるケースがあるため、明示して付ける（SmokeTestで成功済み）
HTTP_REFERER = os.environ.get("RAKUTEN_HTTP_REFERER", "https://mizutanigrandee.github.io/").strip()
HTTP_ORIGIN  = os.environ.get("RAKUTEN_HTTP_ORIGIN",  "https://mizutanigrandee.github.io").strip()

RAKUTEN_HEADERS = {}
if USE_V2:
    # accessKey は query にも入れる（V2の要求に確実に合う） + Bearer も併用
    RAKUTEN_HEADERS = {
        "Authorization": f"Bearer {ACCESS_KEY_V2}",
        "Referer": HTTP_REFERER,
        "Origin": HTTP_ORIGIN,
        "User-Agent": "vacancy-dashboard/update_cache",
    }

print(f"🧩 Rakuten API mode: {'V2' if USE_V2 else 'V1'}", file=sys.stderr)


# ★ 自社の楽天施設番号は Secrets 必須（直書きしない）
MY_HOTEL_NO = os.environ.get("RAKUTEN_MY_HOTEL_NO", "")
if not MY_HOTEL_NO or not MY_HOTEL_NO.strip().isdigit():
    raise ValueError("❌ RAKUTEN_MY_HOTEL_NO が未設定 or 不正です。GitHub Secrets に数字のみで登録してください。")
MY_HOTEL_NO = MY_HOTEL_NO.strip()

CACHE_FILE          = "vacancy_price_cache.json"
PREV_CACHE_FILE     = "vacancy_price_cache_previous.json"
HISTORICAL_FILE     = "historical_data.json"
SPIKE_HISTORY_FILE  = "demand_spike_history.json"
LAST_UPDATED_FILE   = "last_updated.json"   # フロントが読む最終更新メタ

MAX_PAGES = 3  # 市場側のページ走査上限（パフォーマンス配慮）


# ------------------------------------------------------------
# 価格抽出ヘルパー：1ホテル塊の“当日最安値(最低価格)”を返す
# ------------------------------------------------------------
def _extract_hotel_min_price(hotel_obj):
    """
    Rakuten API の hotels[i] の塊から、そのホテルの当日最安値(total)を返す。
    見つからなければ None。
    """
    try:
        blocks = hotel_obj.get("hotel", [])
        if len(blocks) < 2:
            return None
        room_block = blocks[1]  # roomInfo 配列が入っている側
        min_price = None
        for ri in room_block.get("roomInfo", []):
            dc = ri.get("dailyCharge") or {}
            total = dc.get("total")
            if isinstance(total, (int, float)) and total > 0:
                if (min_price is None) or (total < min_price):
                    min_price = total
        return min_price
    except Exception:
        return None


# ------------------------------------------------------------
# 楽天API：市場の在庫数と平均(最低)価格
# ------------------------------------------------------------
def fetch_market_avg(date: dt.date) -> dict:
    """
    指定日の 市場在庫数 と 『平均(最低)価格』
    = “各ホテルの当日最安値”を集めて平均した値 を返す
    """
    print(f"🔍 market {date}", file=sys.stderr)
    hotel_mins = []
    vacancy_total = 0

    for page in range(1, MAX_PAGES + 1):
        params = {
            "applicationId": APP_ID,
            "format": "json",
            "checkinDate":  date.strftime("%Y-%m-%d"),
            "checkoutDate": (date + dt.timedelta(days=1)).strftime("%Y-%m-%d"),
            "adultNum": 1,
            "largeClassCode":  "japan",
            "middleClassCode": "osaka",
            "smallClassCode":  "shi",
            "detailClassCode": "D",
            "page": page,
        }

        # V2の場合は accessKey を必ず付与（SmokeTestと同じ）
        if USE_V2:
            params["applicationId"] = APP_ID_V2
            params["accessKey"] = ACCESS_KEY_V2
        else:
            params["applicationId"] = APP_ID_V1

        try:
            r = requests.get(RAKUTEN_API_URL, params=params, headers=RAKUTEN_HEADERS, timeout=10)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"  ⚠️ market fetch error {date} p{page}: {e}", file=sys.stderr)
            continue

        if page == 1:
            vacancy_total = data.get("pagingInfo", {}).get("recordCount", 0)

        for h in data.get("hotels", []):
            mp = _extract_hotel_min_price(h)
            if isinstance(mp, (int, float)):
                hotel_mins.append(mp)

    avg_price = round(sum(hotel_mins) / len(hotel_mins), 0) if hotel_mins else 0.0
    print(f"   → market avg(min) = {avg_price}  (vacancy={vacancy_total}, hotels={len(hotel_mins)})", file=sys.stderr)
    return {"vacancy": vacancy_total, "avg_price": avg_price}


# ------------------------------------------------------------
# 楽天API：自社ホテルの当日最安値（最低価格）
# ------------------------------------------------------------
def fetch_my_min_price(date: dt.date, hotel_no: str) -> float:
    """
    自社hotelNoの当日最安値。取得できなければ 0.0 を返す。
    """
    if not hotel_no:
        return 0.0

    params = {
        "applicationId": APP_ID,
        "format": "json",
        "checkinDate":  date.strftime("%Y-%m-%d"),
        "checkoutDate": (date + dt.timedelta(days=1)).strftime("%Y-%m-%d"),
        "adultNum": 1,
        "hotelNo": hotel_no,
        "detailClassCode": "D",
        "page": 1,
    }

    # V2の場合は accessKey を必ず付与（SmokeTestと同じ）
    if USE_V2:
        params["applicationId"] = APP_ID_V2
        params["accessKey"] = ACCESS_KEY_V2
    else:
        params["applicationId"] = APP_ID_V1

    try:
        r = requests.get(RAKUTEN_API_URL, params=params, headers=RAKUTEN_HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  ⚠️ my fetch error {date}: {e}", file=sys.stderr)
        return 0.0

    mins = []
    for h in data.get("hotels", []):
        mp = _extract_hotel_min_price(h)
        if isinstance(mp, (int, float)):
            mins.append(mp)

    my_min = float(min(mins)) if mins else 0.0
    print(f"   → my min = {my_min}", file=sys.stderr)
    return my_min


# ------------------------------------------------------------
# 当日以降の未来日を更新
# ------------------------------------------------------------
def update_cache(start_date: dt.date, months: int = 9) -> dict:
    today             = dt.date.today()
    three_months_ago  = today - relativedelta(months=3)
    cal               = calendar.Calendar(firstweekday=calendar.SUNDAY)

    cache = {}
    if Path(CACHE_FILE).exists():
        cache = json.loads(Path(CACHE_FILE).read_text(encoding="utf-8"))

    old_cache = {}
    if Path(PREV_CACHE_FILE).exists():
        old_cache = json.loads(Path(PREV_CACHE_FILE).read_text(encoding="utf-8"))

    # 過去3か月より前は削除
    cache = {k: v for k, v in cache.items() if dt.date.fromisoformat(k) >= three_months_ago}

    for m in range(months):
        month_start = (start_date + relativedelta(months=m)).replace(day=1)
        for week in cal.monthdatescalendar(month_start.year, month_start.month):
            for day in week:
                # 現在以降の未来日だけ取得
                if day.month != month_start.month or day <= today:
                    continue

                iso = day.isoformat()

                # 市場平均(最低) & 自社最安 を取得
                market = fetch_market_avg(day)
                my_p   = 0.0
                try:
                    my_p = fetch_my_min_price(day, MY_HOTEL_NO)
                except Exception as e:
                    print(f"  ⚠️ my price error {iso}: {e}", file=sys.stderr)

                # API失敗日はスキップし既存値保持（0/0は更新しない）
                if market["vacancy"] == 0 and market["avg_price"] == 0.0:
                    print(f"⏩ skip {iso} (empty)", file=sys.stderr)
                    continue

                prev          = old_cache.get(iso, {})
                last_vac      = prev.get("vacancy",   market["vacancy"])
                last_price    = prev.get("avg_price", market["avg_price"])
                vac_diff      = market["vacancy"] - last_vac
                price_diff    = market["avg_price"] - last_price

                # 自社 vs 市場（％）：(自社 - 市場) / 市場 * 100
                my_vs_avg_pct = (
                    round((my_p - market["avg_price"]) / market["avg_price"] * 100, 1)
                    if (my_p and market["avg_price"]) else None
                )

                cache[iso] = {
                    "vacancy":        market["vacancy"],
                    "avg_price":      market["avg_price"],
                    "last_vacancy":   last_vac,
                    "last_avg_price": last_price,
                    "vacancy_diff":   vac_diff,
                    "avg_price_diff": price_diff,
                    # ★ 自社情報を保存
                    "my_price":       my_p if my_p else 0.0,
                    "my_vs_avg_pct":  my_vs_avg_pct,
                }

    Path(CACHE_FILE).write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(PREV_CACHE_FILE).write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    print("✅ cache updated", file=sys.stderr)
    return cache


def _is_date_string(s: str) -> bool:
    try:
        dt.date.fromisoformat(s)
        return True
    except ValueError:
        return False


# ------------------------------------------------------------
# 過去3か月のスナップショット履歴
# ------------------------------------------------------------
def update_history(cache: dict):
    today       = dt.date.today()
    today_str   = today.isoformat()
    hist_data = {}

    if Path(HISTORICAL_FILE).exists():
        try:
            with open(HISTORICAL_FILE, encoding="utf-8") as f:
                hist_data = json.load(f)
        except Exception as e:
            print(f"⚠️ error loading historical_data.json: {e}", file=sys.stderr)

    # 未来日の今日時点スナップショットを追記
    for iso, v in cache.items():
        if dt.date.fromisoformat(iso) >= today:
            hist_data.setdefault(iso, {})
            hist_data[iso][today_str] = {
                "vacancy":    v["vacancy"],
                "avg_price":  v["avg_price"],
            }

    # 各対象日の履歴を3か月に圧縮
    for date_key in list(hist_data.keys()):
        if not _is_date_string(date_key):
            print(f"⚠️ skip legacy key {date_key}", file=sys.stderr)
            continue

        date_dt = dt.date.fromisoformat(date_key)
        limit   = date_dt - relativedelta(months=3)

        for hist_key in list(hist_data[date_key].keys()):
            if not _is_date_string(hist_key):
                print(f"⚠️ skip legacy hist_key {hist_key}", file=sys.stderr)
                del hist_data[date_key][hist_key]
                continue

            hist_dt = dt.date.fromisoformat(hist_key)
            if hist_dt < limit:
                del hist_data[date_key][hist_key]

        if not hist_data[date_key]:
            del hist_data[date_key]

    Path(HISTORICAL_FILE).write_text(json.dumps(hist_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("📁 historical_data.json updated", file=sys.stderr)


# ------------------------------------------------------------
# 急騰検知（方向固定：客室↓ × 単価↑）
# ------------------------------------------------------------
def detect_demand_spikes(cache_data, n_recent=3, price_up_pct=0.05, vac_down_pct=0.05):
    """
    仕様：
      - 対象は“今日以降の宿泊日”のみ
      - 方向固定：『客室が -vac_down_pct 以下（= 減少）』かつ
                  『平均単価が +price_up_pct 以上（= 上昇）』の時だけ検知
      - 前回値(last_*)が無い/0 の項目は自動スキップ
      - 近い宿泊日の除外はフロント(app.js)側で実施済み
    """
    sorted_dates = sorted(cache_data.keys())
    today = dt.date.today()

    results = []
    for d in sorted_dates:
        # 宿泊日が過去なら除外
        try:
            stay_dt = dt.date.fromisoformat(d)
        except Exception:
            continue
        if stay_dt < today:
            continue

        rec = cache_data[d]
        last_price = rec.get("last_avg_price", 0)
        last_vac   = rec.get("last_vacancy", 0)
        cur_price  = rec.get("avg_price", 0)
        cur_vac    = rec.get("vacancy", 0)

        # 前回値が欠損 or 0 は判定不可
        if not (last_price and last_vac):
            continue

        # 差分（符号付き）と比率（符号付き）
        price_diff = cur_price - last_price      # + なら単価↑
        vac_diff   = cur_vac   - last_vac        # - なら客室↓
        price_ratio = (price_diff / last_price) if last_price else 0.0
        vac_ratio   = (vac_diff   / last_vac)   if last_vac   else 0.0

        # 方向＆閾値：客室↓ AND 単価↑
        if (vac_ratio <= -vac_down_pct) and (price_ratio >= price_up_pct):
            results.append({
                "spike_date": d,
                "price": cur_price,
                "last_price": last_price,
                "price_diff": price_diff,
                "price_ratio": round(float(price_ratio), 4),
                "vacancy": cur_vac,
                "last_vac": last_vac,
                "vacancy_diff": vac_diff,
                "vacancy_ratio": round(float(vac_ratio), 4),
            })

    print(f"📊 Demand Spikes Detected (dir-fixed: price↑ & vac↓): {len(results)} 件", file=sys.stderr)
    return results


# ------------------------------------------------------------
# 履歴の保存（過去宿泊日・方向逆を一括クレンジング）
# ------------------------------------------------------------
def save_demand_spike_history(demand_spikes, history_file=SPIKE_HISTORY_FILE):
    """履歴を更新しつつ、
       1) 90日より前のキーを削除
       2) 全キー横断で『過去日のspike』を削除
       3) 方向が逆（単価↓ or 客室↑）のspikeを削除
    """
    today_dt = dt.date.today()
    today_iso = today_dt.isoformat()

    # 既存履歴ロード
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception as e:
            print(f"⚠️ error loading {history_file}: {e}", file=sys.stderr)
            history = {}
    else:
        history = {}

    # 今日分を差し替え
    history[today_iso] = demand_spikes or []

    # 90日より前のキーを削除
    limit = (today_dt - dt.timedelta(days=90)).isoformat()
    history = {d: v for d, v in history.items() if d >= limit}

    # 全キーに対してクレンジング
    cleaned = {}
    for up_date, items in history.items():
        new_items = []
        for it in items or []:
            sd = it.get("spike_date")
            try:
                if sd and dt.date.fromisoformat(sd) < today_dt:
                    continue  # 過去宿泊日のスパイクは捨てる
            except Exception:
                pass

            p_diff = it.get("price_diff", 0)
            v_diff = it.get("vacancy_diff", 0)
            if not (isinstance(p_diff, (int, float)) and isinstance(v_diff, (int, float))):
                continue
            if not (p_diff > 0 and v_diff < 0):
                continue  # 方向が逆は捨てる

            new_items.append(it)
        cleaned[up_date] = new_items

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
    print(f"📁 {history_file} cleaned & updated", file=sys.stderr)


# ------------------------------------------------------------
# 最終更新メタの書き出し（JST）
# ------------------------------------------------------------
def write_last_updated():
    """Actions 実行完了時点のJST時刻などを last_updated.json に保存"""
    JST = dt.timezone(dt.timedelta(hours=9))
    now = dt.datetime.now(JST)
    payload = {
        "last_updated_iso": now.isoformat(timespec="seconds"),
        "last_updated_jst": now.strftime("%Y-%m-%d %H:%M:%S JST"),
        "source": "github-actions",
        "git_sha": os.environ.get("GITHUB_SHA", "")[:7],
        "note": "vacancy/price crawl finished",
    }
    try:
        with open(LAST_UPDATED_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"🕒 {LAST_UPDATED_FILE} written: {payload['last_updated_jst']}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️ failed to write {LAST_UPDATED_FILE}: {e}", file=sys.stderr)


# ------------------------------------------------------------
# エントリポイント
# ------------------------------------------------------------
if __name__ == "__main__":
    print("📡 update_cache.py start", file=sys.stderr)

    cache_now = update_cache(start_date=dt.date.today(), months=9)
    update_history(cache_now)

    demand_spikes = detect_demand_spikes(
        cache_data=cache_now,
        n_recent=3,
        price_up_pct=0.05,   # 単価↑5%以上
        vac_down_pct=0.05    # 客室↓5%以上
    )
    print(f"Demand spikes for today: {demand_spikes}", file=sys.stderr)
    save_demand_spike_history(demand_spikes)

    # すべての更新が完了した“最後”に書き出し
    write_last_updated()
    print("✨ all done", file=sys.stderr)
