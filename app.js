// app.js - 本番用（ダミーデータ完全排除）
// 必要に応じてファイル名やAPI URLなどを調整してください

let baseYear, baseMonth, monthOffset = 0;
let cacheData = {};    // vacancy_price_cache.json
let eventData = {};    // event_data.json もしくは event_data.xlsxを事前変換
let selectedDate = null;

// --- データ取得（ページ初期化時に実行） ---
async function loadAllData() {
    // 1. 空室・価格キャッシュ
    await fetch('vacancy_price_cache.json', { cache: "reload" })
      .then(res => res.json())
      .then(json => { cacheData = json; });

    // 2. イベントデータ（JSONに変換しておくことを推奨）
    await fetch('event_data.json', { cache: "reload" })
      .then(res => res.json())
      .then(json => { eventData = json; });

    // 3. 今日
    const today = new Date();
    baseYear = today.getFullYear();
    baseMonth = today.getMonth() + 1;
    monthOffset = 0;
    // 4. 初回描画
    drawCalendars();
    // 5. 初期グラフ
    const todayStr = today.toISOString().slice(0, 10);
    selectedDate = todayStr;
    drawGraph(todayStr);
    // 6. 更新日時
    document.getElementById("last-updated").textContent = `最終更新日時: ${todayStr}`;
}

// --- カレンダーデータ取得 ---
function getCalendarMatrix(year, month) {
    const matrix = [];
    const firstDay = new Date(year, month - 1, 1).getDay();
    const lastDate = new Date(year, month, 0).getDate();

    let week = Array(7).fill(null);
    let dayCount = 1 - firstDay;

    for (let row = 0; row < 6; row++) {
        week = [];
        for (let col = 0; col < 7; col++, dayCount++) {
            if (dayCount < 1 || dayCount > lastDate) {
                week.push(null);
            } else {
                const iso = `${year}-${String(month).padStart(2, '0')}-${String(dayCount).padStart(2, '0')}`;
                const rec = cacheData[iso] || {};
                const ev  = eventData[iso] || [];
                week.push({
                    day: dayCount,
                    iso,
                    ...rec,
                    events: ev,
                    weekday: col
                });
            }
        }
        matrix.push(week);
    }
    return matrix;
}

// --- カレンダー描画 ---
function drawCalendar(targetId, year, month, selIso) {
    const weekDays = ["日", "月", "火", "水", "木", "金", "土"];
    const matrix = getCalendarMatrix(year, month);
    let html = `<table class="calendar-table"><thead><tr>`;
    for (let wd = 0; wd < 7; wd++) {
        html += `<th>${weekDays[wd]}</th>`;
    }
    html += "</tr></thead><tbody>";

    for (const week of matrix) {
        html += "<tr>";
        for (const cell of week) {
            if (!cell) {
                html += `<td></td>`;
                continue;
            }
            let tdClass = "";
            if (cell.weekday === 0) tdClass += " sunday";
            else if (cell.weekday === 6) tdClass += " saturday";
            if (selIso && selIso === cell.iso) tdClass += " selected";
            html += `<td class="${tdClass.trim()}" data-date="${cell.iso}">`;
            html += `<span class="day-num">${cell.day}</span>`;
            // 在庫数・差分
            if (cell.vacancy !== undefined) {
                html += `<span class="vacancy">${cell.vacancy}件`;
                if (cell.vacancy_diff > 0) html += `<span class="diff-up">（+${cell.vacancy_diff}）</span>`;
                else if (cell.vacancy_diff < 0) html += `<span class="diff-down">（${cell.vacancy_diff}）</span>`;
                html += `</span>`;
            }
            // 平均価格・差分
            if (cell.avg_price !== undefined) {
                html += `<span class="avg-price">￥${Number(cell.avg_price).toLocaleString()}`;
                if (cell.avg_price_diff > 0) html += `<span class="diff-up"> ↑</span>`;
                else if (cell.avg_price_diff < 0) html += `<span class="diff-down"> ↓</span>`;
                html += `</span>`;
            }
            // 需要マーク
            if (cell.demand_symbol) {
                html += `<span class="demand">${cell.demand_symbol}</span>`;
            }
            // イベント
            if (cell.events.length > 0) {
                html += `<div class="event">`;
                for (const e of cell.events) html += `<span>${e.icon} ${e.name}</span><br>`;
                html += `</div>`;
            }
            html += `</td>`;
        }
        html += "</tr>";
    }
    html += "</tbody></table>";
    document.getElementById(targetId).innerHTML = html;

    // 日付クリック
    document.querySelectorAll(`#${targetId} td[data-date]`).forEach(td => {
        td.onclick = () => {
            const iso = td.getAttribute("data-date");
            selectedDate = iso;
            drawCalendars(iso);
            drawGraph(iso);
        };
    });
}

// --- 2枚カレンダー描画 ---
function drawCalendars(selectedIso = null) {
    // 左：今月 右：来月
    let base = new Date(baseYear, baseMonth - 1 + monthOffset);
    let y1 = base.getFullYear();
    let m1 = base.getMonth() + 1;
    let y2 = y1, m2 = m1 + 1;
    if (m2 > 12) { m2 = 1; y2 += 1; }

    let sel1 = null, sel2 = null;
    if (selectedIso) {
        const [yy, mm] = selectedIso.split("-").map(Number);
        if (yy === y1 && mm === m1) sel1 = selectedIso;
        if (yy === y2 && mm === m2) sel2 = selectedIso;
    }
    drawCalendar("calendar1", y1, m1, sel1);
    drawCalendar("calendar2", y2, m2, sel2);
}

// --- グラフ描画（本番用。データは historical_data.json などと連携想定）---
function drawGraph(iso) {
    const box = document.getElementById("graph-container");
    box.innerHTML = ""; // 初期化
    if (!iso) {
        box.innerHTML = `<div style="width:95%;height:230px;background:#f9fafb;display:flex;align-items:center;justify-content:center;border-radius:8px;color:#aaa;font-size:20px;">データなし</div>`;
        return;
    }
    // 本番は historical_data.json からAPI等で該当日データ取得
    fetch('historical_data.json', { cache: "reload" })
      .then(res => res.json())
      .then(hist => {
        const dayObj = hist[iso];
        if (!dayObj) {
          box.innerHTML = `<div style="width:95%;height:230px;background:#f9fafb;display:flex;align-items:center;justify-content:center;border-radius:8px;color:#aaa;font-size:20px;">この日付の履歴データがありません</div>`;
          return;
        }
        // vacancy, avg_priceの推移データ（取得日ベース）でグラフ化
        const labels = Object.keys(dayObj).sort();
        const vacancy = labels.map(k => dayObj[k].vacancy);
        const price   = labels.map(k => dayObj[k].avg_price);
        // Chart.jsなどに差し替えてください。ここではSVG簡易例
        let svg = `<svg width="400" height="180" style="background:#fff;">`;
        // vacancy(青)
        svg += `<polyline fill="none" stroke="#2171b8" stroke-width="2" points="`;
        vacancy.forEach((v, i) => svg += `${30 + i * 11},${140 - (v - 100) * 0.3} `);
        svg += `"/>`;
        // price(赤)
        svg += `<polyline fill="none" stroke="#e15759" stroke-width="2" points="`;
        price.forEach((p, i) => svg += `${30 + i * 11},${170 - (p - 8000) * 0.0045} `);
        svg += `"/>`;
        svg += `<text x="30" y="22" font-size="16" fill="#444">${iso} の在庫・価格推移</text>`;
        svg += `</svg>`;
        box.innerHTML = svg;
      });
}

// --- ナビゲーション ---
document.getElementById("prev-month").onclick = () => {
    monthOffset -= 1;
    drawCalendars(selectedDate);
};
document.getElementById("current-month").onclick = () => {
    monthOffset = 0;
    drawCalendars(selectedDate);
};
document.getElementById("next-month").onclick = () => {
    monthOffset += 1;
    drawCalendars(selectedDate);
};

// --- ページロード ---
window.onload = loadAllData;
