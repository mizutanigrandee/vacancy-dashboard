import pandas as pd
import json

# Excelファイル読み込み
df = pd.read_excel("event_data.xlsx")

# 必要カラム名: 日付, イベント名, 種別
# 例: 2025-07-14, SEVENTEEN, 京セラ
events = []
for _, row in df.iterrows():
    events.append({
        "date": str(row["日付"]),
        "name": str(row["イベント名"]),
        "type": str(row["種別"])
    })

# 日付ごとにリスト化
event_dict = {}
for e in events:
    d = e["date"][:10]  # 日付部分だけ抜き出し
    if d not in event_dict:
        event_dict[d] = []
    event_dict[d].append({"name": e["name"], "type": e["type"]})

with open("event_data.json", "w", encoding="utf-8") as f:
    json.dump(event_dict, f, ensure_ascii=False, indent=2)

print("event_data.json を出力しました")
