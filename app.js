// ---- 基本設定 ----
let current = new Date();
let offset = 0;

// 必要なファイルパスは、運用環境のルート or public配下に必ず配置してください
const VACANCY_JSON = "vacancy_price_cache.json";
const EVENT_JSON = "event_data.json";
const HISTORY_JSON = "historical_data.json";

let calendarData = {};
let eventData = {};
let historicalData = {};

let selectedDate = formatDate(current);

// --- データロード ---
function fetchAllAndRender() {
  Promise.all([
    fetch(VACANCY_JSON).then(res => res.json()),
    fetch(EVENT_JSON).then(res => res.json()).catch(()=>{return {}}),
    fetch(HISTORY_JSON).then(res => res.json()).catch(()=>{return {}})
  ]).then(([calData, evtData, histData]) => {
    calendarData = calData;
    eventData = evtData;
    historicalData = histData;
    redrawAll();
  }).catch(e => {
    alert("JSONファイルが見つからない、または壊れています。: " + e.message);
  });
}

function formatDate(dt) {
  return dt.toISOString().slice(0,10);
}

// --- カレンダー描画 ---
function getFirstMonth() {
  const now = new Date();
  now.setMonth(now.getMonth() + offset);
  now.setDate(1);
  return new Date(now);
}
function getSecondMonth() {
  const now = new Date();
  now.setMonth(now.getMonth() + offset + 1);
  now.setDate(1);
  return new Date(now);
}

function redrawAll() {
  renderCalendar(getFirstMonth(), "calendar1", "month1-title");
  renderCalendar(getSecondMonth(), "calendar2", "month2-title");
  renderChart(selectedDate || formatDate(current));
}

function renderCalendar(monthDate, tableId, titleId) {
  const yyyy = monthDate.getFullYear();
  const mm = monthDate.getMonth() + 1;
  document.getElementById(titleId).textContent = `${yyyy}年${mm}月`;
  const table = document.getElementById(tableId);
  let html = `<tr>${"日月火水木金土".split("").map((w) => `<th>${w}</th>`).join("")}</tr>`;
  const first = new Date(yyyy, mm-1, 1);
  let day = 1 - first.getDay();
  for (let w = 0; w < 6; w++) {
    html += "<tr>";
    for (let d = 0; d < 7; d++) {
      const date = new Date(yyyy, mm-1, day);
      const ds = formatDate(date);
      let cls = [];
      if (d === 0) cls.push("sunday");
      if (d === 6) cls.push("saturday");
      if (ds === selectedDate) cls.push("selected");
      const rec = (calendarData && calendarData[ds]) || {};
      const ev = (eventData && eventData[ds]) || [];
      html += `<td class="${cls.join(" ")}" data-date="${ds}">
        <div class="day-num">${date.getMonth() === mm-1 ? date.getDate() : ""}</div>
        ${rec.vacancy ? `<div class="vacancy">${rec.vacancy}件${rec.vacancy_diff !== undefined && rec.vacancy_diff !== 0 ? `<span class="${rec.vacancy_diff>0?'diff-up':'diff-down'}">(${rec.vacancy_diff>0?'+':''}${rec.vacancy_diff})</span>` : ""}</div>` : ""}
        ${rec.avg_price ? `<div class="avg-price">￥${Number(rec.avg_price).toLocaleString()}${rec.avg_price_diff !== undefined && rec.avg_price_diff !== 0 ? `<span class="${rec.avg_price_diff>0?'diff-up':'diff-down'}">${rec.avg_price_diff>0?'↑':'↓'}</span>` : ""}</div>` : ""}
        ${(rec.demand || rec.demand_symbol) ? `<div class="demand">🔥${rec.demand || rec.demand_symbol}</div>` : ""}
        ${ev.length ? `<div class="event">${ev.map(e=>`${e.icon?e.icon:""} ${e.name}`).join("<br>")}</div>` : ""}
      </td>`;
      day++;
    }
    html += "</tr>";
  }
  table.innerHTML = html;
  // 日付クリック
  Array.from(table.querySelectorAll("td[data-date]")).forEach(td => {
    td.onclick = () => {
      selectedDate = td.getAttribute("data-date");
      redrawAll();
    }
  });
}

// --- グラフ描画 ---
function renderChart(dateStr) {
  document.getElementById("graph-title").textContent = `${dateStr} の在庫・価格推移`;
  let dataObj = (historicalData && historicalData[dateStr]) || {};
  let labels = [], vacancy = [], price = [];
  if (dataObj && typeof dataObj === "object") {
    let rows = Object.entries(dataObj)
      .map(([dt, rec]) => ({date: dt, vacancy: rec.vacancy, price: rec.avg_price}))
      .sort((a,b) => a.date.localeCompare(b.date));
    labels = rows.map(r => r.date);
    vacancy = rows.map(r => r.vacancy);
    price = rows.map(r => r.price);
  }
  const ctx = document.getElementById('mainChart').getContext('2d');
  if (window._chart) window._chart.destroy();
  window._chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        { label: '在庫数', data: vacancy, borderColor: '#2d7bcb', backgroundColor: 'rgba(70,145,220,0.07)', yAxisID: 'y', tension: 0.15, pointRadius: 2, borderWidth: 2 },
        { label: '平均単価(円)', data: price, borderColor: '#e15759', backgroundColor: 'rgba(225,87,89,0.07)', yAxisID: 'y2', tension: 0.13, pointRadius: 2, borderWidth: 2 }
      ]
    },
    options: {
      responsive: false,
      plugins: { legend: { display: true, labels: {font: {size: 13}} } },
      scales: {
        y: { type: 'linear', position: 'left', beginAtZero:true, title: { display:true, text:"在庫数" }, min:0 },
        y2: { type: 'linear', position: 'right', beginAtZero:true, title: { display:true, text:"平均単価(円)" }, min:0, grid: { drawOnChartArea: false } }
      }
    }
  });
}

// --- ナビゲーション ---
document.getElementById("prevMonthBtn").onclick = ()=>{ offset--; redrawAll(); }
document.getElementById("nextMonthBtn").onclick = ()=>{ offset++; redrawAll(); }
document.getElementById("todayBtn").onclick = ()=>{ offset=0; redrawAll(); }

// ---- ページ初期化 ----
window.onload = fetchAllAndRender;
