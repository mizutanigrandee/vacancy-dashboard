// ========== 設定 ==========
const DATA_PATH = "./vacancy_price_cache.json";
const PREV_DATA_PATH = "./vacancy_price_cache_previous.json";
const EVENT_PATH = "./event_data.json";
const HISTORICAL_PATH = "./historical_data.json";

// ========== グローバル状態 ==========
let calendarData = {};
let prevCalendarData = {};
let eventData = {};
let historicalData = {};

let currentYearMonth = [];
let selectedDate = null;

// ========== 初期化 ==========
window.onload = async function() {
  await loadAllData();
  initMonth();
  renderCalendars();
  updateLastUpdate();
  setupMonthButtons();
}

// ========== データ読込 ==========
async function loadAllData() {
  calendarData = await fetchJson(DATA_PATH);
  prevCalendarData = await fetchJson(PREV_DATA_PATH);
  eventData = await fetchJson(EVENT_PATH);
  historicalData = await fetchJson(HISTORICAL_PATH);
}

async function fetchJson(path) {
  try {
    const res = await fetch(path);
    if (!res.ok) return {};
    return await res.json();
  } catch(e) {
    return {};
  }
}

// ========== 月初期設定 ==========
function initMonth() {
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth() + 1;
  currentYearMonth = [
    [year, month],
    month === 12 ? [year+1, 1] : [year, month+1]
  ];
}

// ========== カレンダー描画 ==========
function renderCalendars() {
  const container = document.getElementById("calendar-container");
  container.innerHTML = "";
  for (let ym of currentYearMonth) {
    const calElem = renderMonthCalendar(ym[0], ym[1]);
    container.appendChild(calElem);
  }
}

// ========== 1か月分カレンダー描画 ==========
function renderMonthCalendar(year, month) {
  const wrapper = document.createElement("div");
  wrapper.className = "month-calendar";
  const header = document.createElement("div");
  header.className = "month-header";
  header.textContent = `${year}年${month}月`;
  wrapper.appendChild(header);

  // 曜日ヘッダー
  const daysOfWeek = ["日", "月", "火", "水", "木", "金", "土"];
  const grid = document.createElement("div");
  grid.className = "calendar-grid";
  for (let d of daysOfWeek) {
    const cell = document.createElement("div");
    cell.className = "calendar-cell";
    cell.style.fontWeight = "bold";
    cell.style.background = "#fff";
    cell.textContent = d;
    grid.appendChild(cell);
  }

  // 各日のセル
  const firstDay = new Date(year, month-1, 1).getDay();
  const lastDate = new Date(year, month, 0).getDate();
  let dayCount = 0;
  for (let i=0; i<firstDay; i++) {
    const emptyCell = document.createElement("div");
    emptyCell.className = "calendar-cell";
    grid.appendChild(emptyCell);
    dayCount++;
  }
  for (let date=1; date<=lastDate; date++) {
    const cellDate = `${year}-${String(month).padStart(2,"0")}-${String(date).padStart(2,"0")}`;
    const cell = document.createElement("div");
    cell.className = "calendar-cell";
    cell.dataset.date = cellDate;

    // 土日判定
    const dayOfWeek = (dayCount)%7;
    if (dayOfWeek === 0) cell.classList.add("sunday");
    if (dayOfWeek === 6) cell.classList.add("saturday");

    // データ取得
    const data = calendarData[cellDate] || {};
    const prevData = prevCalendarData[cellDate] || {};
    const event = eventData[cellDate] ? eventData[cellDate].event_name : "";
    const demand = data.demand ? "🔥" : "";

    if (event && event.includes("祝日")) {
      cell.classList.add("holiday");
    }
    if (event && !event.includes("祝日")) {
      cell.classList.add("event");
    }
    if (data.demand) {
      cell.classList.add("strong-demand");
    }

    let stock = data.stock || "-";
    let price = data.price ? `¥${data.price.toLocaleString()}` : "-";
    let diffHtml = "";
    if (data.price && prevData.price) {
      const diff = data.price - prevData.price;
      if (diff > 0) {
        diffHtml = `<span class="cell-diff up">↑ ${diff.toLocaleString()}</span>`;
      } else if (diff < 0) {
        diffHtml = `<span class="cell-diff down">↓ ${Math.abs(diff).toLocaleString()}</span>`;
      } else {
        diffHtml = `<span class="cell-diff">→ 0</span>`;
      }
    }

    let eventHtml = event ? `<span class="cell-event"><span>🎫</span> ${event}</span>` : "";
    let demandHtml = demand ? `<span class="cell-demand">${demand}</span>` : "";

    cell.innerHTML = `
      <div class="cell-main">${stock}件 (${date}日)</div>
      <div class="cell-price">${price}</div>
      <div>${diffHtml}</div>
      ${eventHtml}
      ${demandHtml}
    `;

    cell.onclick = function() {
      selectDate(cellDate);
    };

    grid.appendChild(cell);
    dayCount++;
  }
  wrapper.appendChild(grid);
  return wrapper;
}

// ========== 日付選択 ==========
function selectDate(dateStr) {
  selectedDate = dateStr;
  document.querySelectorAll('.calendar-cell').forEach(cell => {
    if (cell.dataset.date === dateStr) {
      cell.classList.add('selected');
    } else {
      cell.classList.remove('selected');
    }
  });
  renderGraph(dateStr);
}

// ========== グラフ描画（Chart.js版） ==========
function renderGraph(dateStr) {
  const graphContainer = document.getElementById("graph-container");
  graphContainer.style.display = "block";

  // 履歴データ取得
  const history = historicalData[dateStr];
  const stockHistory = history?.stock_history || [];
  const priceHistory = history?.price_history || [];
  const labels = history?.date_list || [];

  graphContainer.innerHTML = `
    <button onclick="closeGraph()" style="float:right;">グラフを閉じる</button>
    <h3>${dateStr} の在庫・価格推移</h3>
    <div style="margin-bottom:18px;">
      <canvas id="stockChart" width="420" height="180"></canvas>
    </div>
    <div>
      <canvas id="priceChart" width="420" height="180"></canvas>
    </div>
  `;

  // 既存グラフの破棄（同じcanvasIDで再描画する場合のChart.jsメモリリーク防止）
  if(window.stockChartInstance) {
    window.stockChartInstance.destroy();
  }
  if(window.priceChartInstance) {
    window.priceChartInstance.destroy();
  }

  // 在庫推移グラフ
  if (labels.length && stockHistory.length) {
    window.stockChartInstance = new Chart(document.getElementById('stockChart').getContext('2d'), {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: '在庫数',
          data: stockHistory,
          fill: false,
          borderColor: '#2196f3',
          backgroundColor: '#90caf9',
          tension: 0.2,
          pointRadius: 2,
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, title: { display: true, text: "在庫数" } },
          x: { title: { display: true, text: "日付" } }
        }
      }
    });
  }

  // 価格推移グラフ
  if (labels.length && priceHistory.length) {
    window.priceChartInstance = new Chart(document.getElementById('priceChart').getContext('2d'), {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: '平均価格',
          data: priceHistory,
          fill: false,
          borderColor: '#e91e63',
          backgroundColor: '#f8bbd0',
          tension: 0.2,
          pointRadius: 2,
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          y: {
            beginAtZero: false,
            title: { display: true, text: "平均価格（円）" }
          },
          x: { title: { display: true, text: "日付" } }
        }
      }
    });
  }
}

// ========== グラフを閉じる ==========
function closeGraph() {
  document.getElementById("graph-container").style.display = "none";
  document.querySelectorAll('.calendar-cell.selected').forEach(cell => {
    cell.classList.remove('selected');
  });
  selectedDate = null;

  // メモリリーク防止のためChart.jsインスタンスを破棄
  if(window.stockChartInstance) {
    window.stockChartInstance.destroy();
    window.stockChartInstance = null;
  }
  if(window.priceChartInstance) {
    window.priceChartInstance.destroy();
    window.priceChartInstance = null;
  }
}

// ========== 月切替ボタン ==========
function setupMonthButtons() {
  document.getElementById("prevMonthBtn").onclick = function() {
    shiftMonth(-1);
  };
  document.getElementById("currentMonthBtn").onclick = function() {
    initMonth();
    renderCalendars();
  };
  document.getElementById("nextMonthBtn").onclick = function() {
    shiftMonth(1);
  };
}

function shiftMonth(diff) {
  let [y,m] = currentYearMonth[0];
  m += diff;
  if (m < 1) { y--; m = 12; }
  if (m > 12) { y++; m = 1; }
  currentYearMonth = [
    [y,m],
    m === 12 ? [y+1,1] : [y,m+1]
  ];
  renderCalendars();
}

// ========== 最終更新日時 ==========
function updateLastUpdate() {
  document.getElementById("last-update").textContent = formatDate(new Date());
}

function formatDate(dt) {
  return `${dt.getFullYear()}-${String(dt.getMonth()+1).padStart(2,"0")}-${String(dt.getDate()).padStart(2,"0")} ${String(dt.getHours()).padStart(2,"0")}:${String(dt.getMinutes()).padStart(2,"0")}:${String(dt.getSeconds()).padStart(2,"0")}`;
}
