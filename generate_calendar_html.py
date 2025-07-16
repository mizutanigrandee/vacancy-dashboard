# ファイル名: generate_calendar_html.py

import json
import datetime

# データファイルを読み込む（vacancy_price_cache.json）
with open("vacancy_price_cache.json", encoding="utf-8") as f:
    data = json.load(f)

today = datetime.date.today().strftime("%Y-%m-%d")
# ここからHTML組み立て。サンプルとして1日分だけ出力
calendar_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <title>空室＆平均価格カレンダー</title>
</head>
<body>
<h2>空室＆平均価格カレンダー</h2>
<p>最終巡回時刻：{today}</p>
<table border="1">
  <tr>
    <th>日付</th>
    <th>在庫数</th>
    <th>平均価格</th>
  </tr>
"""

# ここでデータから日付順に出力する（サンプルは10日分だけ）
for i, (d, v) in enumerate(sorted(data.items())):
    if i >= 10:
        break
    calendar_html += f"<tr><td>{d}</td><td>{v['vacancy']}</td><td>{v['avg_price']}</td></tr>\n"

calendar_html += """
</table>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(calendar_html)
print("index.html を生成しました！")
