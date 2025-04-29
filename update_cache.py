import json
from datetime import datetime
from fetch_rakuten_data import fetch_all_vacancy_and_price  # 楽天API取得用関数

# --- 設定 ---
CACHE_PATH = "vacancy_price_cache.json"

# --- 1. 既存キャッシュを読み込み ---
try:
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        cache = json.load(f)
except FileNotFoundError:
    cache = {}

# --- 2. 最新データを取得 ---
latest_data = fetch_all_vacancy_and_price()

# --- 3. データ更新処理 ---
for date_str, new_info in latest_data.items():
    new_vacancy = new_info["vacancy"]
    new_price = new_info["avg_price"]

    # 以前の情報を取得（なければ0）
    old_entry = cache.get(date_str, {})
    prev_vacancy = old_entry.get("vacancy", 0)

    # 差分を計算
    vacancy_diff = new_vacancy - prev_vacancy

    # 保存形式
    cache[date_str] = {
        "vacancy": new_vacancy,
        "avg_price": new_price,
        "previous_vacancy": prev_vacancy,
        "previous_avg_price": old_entry.get("avg_price", 0.0),
        "vacancy_diff": vacancy_diff
    }

# --- 4. 保存 ---
with open(CACHE_PATH, "w", encoding="utf-8") as f:
    json.dump(cache, f, ensure_ascii=False, indent=2)

print(f"✅ 更新完了：{datetime.now().isoformat()}")
