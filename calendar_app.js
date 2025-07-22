// --- 設定（ファイル名や初期月） ---
const PRICE_FILE = "vacancy_price_cache.json";
const EVENT_FILE = "event_data.json";
const HIST_FILE  = "historical_data.json";

// --- グローバル ---
let calendarMonth = getTodayMonth();
let priceData = {}, eventData = [], histData = {};
let holidayList = {}; // 祝日情報キャッシュ

// --- 初期ロード ---
document.addEventListener("DOMContentLoaded", async () => {
  [priceData, eventData, histData] = await Promise.all([
    fetchJson(PRICE_FILE),
    fetchJson(EVENT_FILE),
    fetchJson(HIST_FILE)
  ]);
  // ←この1行を追加
  if (!Array.isArray(eventData)) eventData = Object.values(eventData);

  holidayList = getJapanHolidays(calendarMonth.year);
  renderCalendar(calendarMonth.year, calendarMonth.month);
  setEventListeners();
  setLastUpdated();
});

// --- 月送り ---
function setEventListeners() {
  document.getElementById("prevMonthBtn").onclick = () => {
    calendarMonth = addMonth(calendarMonth, -1);
    holidayList = getJapanHolidays(calendarMonth.year);
    renderCalendar(calendarMonth.year, calendarMonth.month);
  };
  document.getElementById("nextMonthBtn").onclick = () => {
    calendarMonth = addMonth(calendarMonth, 1);
    holidayList = getJapanHolidays(calendarMonth.year);
    renderCalendar(calendarMonth.year, calendarMonth.month);
  };
}

// --- カレンダー描画 ---
function renderCalendar(year, month) {
  const calendarDiv = document.getElementById("calendar-app");
  const firstDay = new Date(year, month-1, 1);
  const firstWday = firstDay.getDay();
  const daysInMonth = new Date(year, month, 0).getDate();
  let html = `<table class="calendar-table"><tr>`;
  const weekDays = ["日", "月", "火", "水", "木", "金", "土"];
  for(let wd of weekDays) html += `<th>${wd}</th>`;
  html += `</tr><tr>`;

  let wday = firstWday, printed = 0;
  for(let i=0; i<firstWday; i++) { html += `<td class="disabled"></td>`; printed++; }
  for(let d=1; d<=daysInMonth; d++) {
    const dateStr = `${year}-${String(month).padStart(2,"0")}-${String(d).padStart(2,"0")}`;
    let cellClass = [], cellHtml = "";

    // 曜日判定
    if (wday == 0) cellClass.push("sun");
    if (wday == 6) cellClass.push("sat");
    if (isJapanHoliday(dateStr)) cellClass.push("holiday");

    // 祝日名（ツールチップ用）
    let hname = isJapanHoliday(dateStr) ? getHolidayName(dateStr) : "";
    // データ取得
    const dData = priceData[dateStr] || {};
    const events = eventData.filter(e => e.date === dateStr);

    cellHtml += `<span class="cell-date" title="${hname}">${d}</span>`;
    if (dData.vacancy !== undefined) {
      // 在庫数・前日比
      cellHtml += `<span class="cell-vacancy">${dData.vacancy || 0}`;
      if (dData.previous_vacancy !== undefined && dData.vacancy !== undefined) {
        const diff = dData.vacancy - dData.previous_vacancy;
        if (diff > 0) cellHtml += `<span class="diff-plus">＋${diff}</span>`;
        else if (diff < 0) cellHtml += `<span class="diff-minus">－${Math.abs(diff)}</span>`;
      }
      cellHtml += `</span>`;
      // 平均価格・変動アイコン
      if (dData.avg_price !== undefined) {
        let priceDiff = dData.avg_price - (dData.previous_avg_price || 0);
        let priceClass = priceDiff > 0 ? "price-up" : priceDiff < 0 ? "price-down" : "";
        let icon = priceDiff > 0 ? "↑" : priceDiff < 0 ? "↓" : "";
        cellHtml += `<span class="cell-price ${priceClass}">¥${(dData.avg_price||0).toLocaleString()} <span>${icon}</span></span>`;
      }
    }
    // イベント注記
    if (events.length > 0) {
      for (let e of events) {
        let icon = "★";
        if (e.venue && e.venue.includes("京セラ")) icon = "🔴";
        else if (e.venue && e.venue.includes("ヤンマー")) icon = "🔵";
        cellHtml += `<div class="cell-event">${icon} ${e.name || ""}</div>`;
      }
    }
    // 需要シンボル（炎マーク）
    if (dData.hot_level && dData.hot_level > 0) {
      cellHtml += `<span class="cell-hot">${"🔥".repeat(dData.hot_level)}</span>`;
    }

    // 日付クリックでグラフ表示
    html += `<td class="${cellClass.join(" ")}" data-date="${dateStr}" onclick="showChartModal('${dateStr}')">${cellHtml}</td>`;
    printed++;
    wday++;
    if (wday > 6 && d < daysInMonth) { html += "</tr><tr>"; wday=0; }
  }
  for(let i=printed%7; i<7 && i!=0; i++) html += `<td class="disabled"></td>`;
  html += "</tr></table>";

  // 月表示
  html = `<div style="text-align:center;margin-bottom:6px;font-size:1.07em;font-weight:bold;">${year}年${month}月</div>` + html;
  calendarDiv.innerHTML = html;
}

// --- グラフ（トレンド2本線） ---
function showChartModal(dateStr) {
  const modal = document.getElementById("chart-modal");
  modal.style.display = "block";
  drawTrendChart(dateStr);

  // ナビボタン
  document.getElementById("prevDayBtn").onclick = () => moveChartDate(dateStr, -1);
  document.getElementById("nextDayBtn").onclick = () => moveChartDate(dateStr, 1);
  document.getElementById("closeChartBtn").onclick = () => { modal.style.display = "none"; };
}

// グラフ移動
function moveChartDate(curDateStr, diff) {
  const d = new Date(curDateStr);
  d.setDate(d.getDate() + diff);
  const ymd = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
  drawTrendChart(ymd);
}

// グラフ描画
function drawTrendChart(dateStr) {
  const labels = [];
  const vacancy = [];
  const price = [];
  // 過去30日 or 7日前～7日後を対象
  const days = Object.keys(histData).sort();
  let idx = days.indexOf(dateStr);
  let range = days.slice(Math.max(0, idx-7), Math.min(days.length, idx+8));
  for (let d of range) {
    labels.push(d.slice(5)); // "MM-DD"
    vacancy.push(histData[d]?.vacancy || 0);
    price.push(histData[d]?.avg_price || 0);
  }
  const ctx = document.getElementById("trendChart").getContext("2d");
  if(window.trendChartObj) window.trendChartObj.destroy();
  window.trendChartObj = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {label: "在庫数", data: vacancy, yAxisID: "y1", borderWidth: 2, fill: false, tension: 0.3},
        {label: "平均価格", data: price, yAxisID: "y2", borderWidth: 2, borderDash: [5,5], fill: false, tension: 0.3}
      ]
    },
    options: {
      responsive: false,
      scales: {
        y1: {type: "linear", position: "left", title:{display:true,text:"在庫数"}},
        y2: {type: "linear", position: "right", title:{display:true,text:"平均価格"}, grid:{drawOnChartArea:false}}
      }
    }
  });
}

// --- ユーティリティ ---
function fetchJson(path) { return fetch(path).then(r=>r.json()); }
function getTodayMonth() {
  const now = new Date();
  return {year: now.getFullYear(), month: now.getMonth()+1};
}
function addMonth({year, month}, diff) {
  let m = month + diff, y = year;
  while(m > 12) { y++; m-=12; }
  while(m < 1)  { y--; m+=12; }
  return {year:y, month:m};
}
function setLastUpdated() {
  const days = Object.keys(priceData||{});
  if(!days.length) return;
  days.sort();
  document.getElementById("last-updated").innerText = "最終更新: " + days[days.length-1];
}

// --- 祝日判定用 ---
function getJapanHolidays(year) {
  // 必要に応じて外部APIや既存jsonからも拡張可
  // ここではサンプルとして一部固定データ
  let holis = {};
  // 例: holis["2025-01-01"] = "元日";
  return holis;
}
function isJapanHoliday(dateStr) {
  return holidayList[dateStr] !== undefined;
}
function getHolidayName(dateStr) {
  return holidayList[dateStr] || "";
}
