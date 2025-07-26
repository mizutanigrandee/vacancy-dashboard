// app.js

// 必要なモックデータ例（本番はfetchで差し替え）
const mockVacancyData = window.mockVacancyData || {}; // { 'YYYY-MM-DD': { vacancy, price, ... } }
const mockEventData = window.mockEventData || {};     // { 'YYYY-MM-DD': [ { icon, name }, ... ] }
const mockHistoryData = window.mockHistoryData || {}; // { 'YYYY-MM-DD': { 'YYYY-MM-DD': { vacancy, price } } }

const WEEKDAYS = ['日', '月', '火', '水', '木', '金', '土'];
const CALENDAR_CELL_SIZE = 70; // px, 正方形を維持

// 祝日判定（例：jpholiday互換API/テーブルなど本番で差し替え）
function isHoliday(date) {
  // 簡易版：日曜だけ祝日。必要に応じて拡張
  return date.getDay() === 0;
}
function isSaturday(date) {
  return date.getDay() === 6;
}

// 月のカレンダー行列（weeks: [[Date, ...], ...]）
function getMonthMatrix(year, month) {
  const first = new Date(year, month, 1);
  const last = new Date(year, month + 1, 0);
  const start = new Date(first);
  start.setDate(start.getDate() - start.getDay());
  const end = new Date(last);
  end.setDate(end.getDate() + (6 - end.getDay()));
  const weeks = [];
  let cur = new Date(start);
  while (cur <= end) {
    let week = [];
    for (let d = 0; d < 7; ++d) {
      week.push(new Date(cur));
      cur.setDate(cur.getDate() + 1);
    }
    weeks.push(week);
  }
  return weeks;
}

// 需要シンボル
function getDemandIcon(vac, price) {
  if (vac <= 70 || price >= 50000) return "🔥5";
  if (vac <= 100 || price >= 40000) return "🔥4";
  if (vac <= 150 || price >= 35000) return "🔥3";
  if (vac <= 200 || price >= 30000) return "🔥2";
  if (vac <= 250 || price >= 25000) return "🔥1";
  return "";
}

// 祝日 or 土日判定
function getCellClass(date, month) {
  if (date.getMonth() !== month) return "calendar-cell out-month";
  if (isHoliday(date)) return "calendar-cell holiday";
  if (isSaturday(date)) return "calendar-cell saturday";
  if (date.getDay() === 0) return "calendar-cell sunday";
  return "calendar-cell";
}

// カレンダー1枚HTML生成
function renderCalendar(year, month, selectedDate) {
  const today = new Date();
  const weeks = getMonthMatrix(year, month);
  let html = `<div class="month-header">${year}年${month + 1}月</div>`;
  html += `<div class="calendar-grid calendar-header-row">`;
  for (let i = 0; i < 7; ++i) html += `<div>${WEEKDAYS[i]}</div>`;
  html += `</div>`;

  html += `<div class="calendar-grid">`;
  for (const week of weeks) {
    for (const date of week) {
      const ymd = date.toISOString().slice(0, 10);
      const inMonth = date.getMonth() === month;
      const cellClass =
        getCellClass(date, month) +
        (ymd === selectedDate ? " selected" : "");
      let rec = mockVacancyData[ymd] || {};
      let vac = rec.vacancy ?? "";
      let price = rec.price ?? "";
      let diffV = rec.vacancy_diff ?? "";
      let diffP = rec.price_diff ?? "";
      let demand = (vac && price) ? getDemandIcon(vac, price) : "";
      let eventHtml = "";
      if (mockEventData[ymd]) {
        eventHtml = `<div class="event-line">${mockEventData[ymd]
          .map(ev => `<span>${ev.icon} ${ev.name}</span>`)
          .join("<br>")}</div>`;
      }
      html += `
      <div class="${cellClass}" style="height:${CALENDAR_CELL_SIZE}px;"
        data-date="${ymd}" ${inMonth ? '' : 'tabindex="-1"'}>
        <div class="cell-date" style="font-weight:bold;font-size:15px;">
          ${date.getDate()}
        </div>
        <div class="cell-vac">
          ${vac !== "" ? `${vac}件` : ""}
          ${diffV > 0 ? `<span style="color:blue;font-size:12px;">（+${diffV}）</span>` : ""}
          ${diffV < 0 ? `<span style="color:red;font-size:12px;">（${diffV}）</span>` : ""}
        </div>
        <div class="cell-price">
          ${price !== "" ? `¥${Number(price).toLocaleString()}` : ""}
          ${diffP > 0 ? `<span style="color:red;"> ↑</span>` : ""}
          ${diffP < 0 ? `<span style="color:blue;"> ↓</span>` : ""}
        </div>
        <div class="cell-demand">${demand}</div>
        ${eventHtml}
      </div>
      `;
    }
  }
  html += `</div>`;
  return html;
}

// グラフ描画（簡易・モック版、実際はChart.js等で実装推奨）
function renderGraph(dateStr) {
  // データ取得
  const hist = mockHistoryData[dateStr];
  if (!hist) return `<div style="color:#777;margin:14px;">データなし</div>`;
  // 仮：canvasタグ生成。グラフjsは別途
  // 実際はplotlyやChart.jsなど推奨
  return `
    <div style="font-weight:bold;margin-bottom:2px;">${dateStr} の在庫・価格推移</div>
    <canvas id="vacancyGraph" width="340" height="120"></canvas>
    <canvas id="priceGraph" width="340" height="120"></canvas>
  `;
}

// 選択日付のグラフ描画
function updateGraph(dateStr) {
  const graphContainer = document.getElementById("graph-container");
  graphContainer.innerHTML = renderGraph(dateStr);
  // ここでCanvas描画（Chart.js等で）を追加
  // 仮のランダムグラフでOKなら…
  if (mockHistoryData[dateStr]) {
    drawMockLineChart("vacancyGraph", Object.values(mockHistoryData[dateStr]).map(d => d.vacancy), "在庫数");
    drawMockLineChart("priceGraph", Object.values(mockHistoryData[dateStr]).map(d => d.price), "平均単価(円)");
  }
}

// 仮：ランダム線グラフ（Canvasで簡易）
function drawMockLineChart(canvasId, dataArr, label) {
  const c = document.getElementById(canvasId);
  if (!c || !dataArr.length) return;
  const ctx = c.getContext("2d");
  ctx.clearRect(0,0, c.width, c.height);
  ctx.beginPath();
  ctx.moveTo(10, 100 - dataArr[0]/(Math.max(...dataArr)+1) * 100);
  for (let i=1; i<dataArr.length; i++) {
    ctx.lineTo(10+i*20, 100 - dataArr[i]/(Math.max(...dataArr)+1) * 100);
  }
  ctx.strokeStyle = canvasId === "vacancyGraph" ? "#2980b9" : "#e74c3c";
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.font = "10px sans-serif";
  ctx.fillText(label, 10, 10);
}

// 月カレンダーのリフレッシュ
function updateCalendars(baseDate, selectedDate) {
  const y1 = baseDate.getFullYear(), m1 = baseDate.getMonth();
  const y2 = (new Date(baseDate.getTime() + 32*24*60*60*1000)).getFullYear();
  const m2 = (new Date(baseDate.getTime() + 32*24*60*60*1000)).getMonth();

  document.getElementById("calendar-container-1").innerHTML = renderCalendar(y1, m1, selectedDate);
  document.getElementById("calendar-container-2").innerHTML = renderCalendar(y2, m2, selectedDate);

  // カレンダークリックで日付選択
  Array.from(document.querySelectorAll('.calendar-cell')).forEach(cell => {
    cell.onclick = e => {
      const ymd = cell.dataset.date;
      if (ymd) {
        updateGraph(ymd);
        updateCalendars(baseDate, ymd);
      }
    };
  });
}

// ナビゲーション
function bindCalendarNav(baseDateSetter) {
  document.getElementById('prevMonthBtn').onclick = () => baseDateSetter(-1);
  document.getElementById('currentMonthBtn').onclick = () => baseDateSetter(0);
  document.getElementById('nextMonthBtn').onclick = () => baseDateSetter(1);
}

// 初期化
window.onload = function() {
  let baseMonth = new Date();
  baseMonth.setDate(1);
  let selected = null;

  function rerender(navi=0) {
    if (navi !== 0) {
      baseMonth.setMonth(baseMonth.getMonth() + navi);
    } else if (navi === 0) {
      baseMonth = new Date();
      baseMonth.setDate(1);
    }
    updateCalendars(baseMonth, selected);
  }

  // ナビゲーション
  bindCalendarNav((navi) => rerender(navi));

  // 初期表示（当日グラフ付き）
  selected = new Date().toISOString().slice(0, 10);
  updateCalendars(baseMonth, selected);
  updateGraph(selected);

  // 巡回日時
  document.getElementById("last-update").textContent =
    `最終更新日時: ${(new Date()).toLocaleString()}`;
};
