const DATA_PATH = "./vacancy_price_cache.json";
const PREV_DATA_PATH = "./vacancy_price_cache_previous.json";
const EVENT_PATH = "./event_data.json";
const HISTORICAL_PATH = "./historical_data.json";
const SPIKE_PATH = "./demand_spike_history.json";

let calendarData = {};
let prevCalendarData = {};
let eventData = {};
let historicalData = {};
let spikeData = [];

let currentYearMonth = [];
let selectedDate = null;

// ----------- 初期化 -----------
window.onload = async function() {
  await loadAllData();
  renderSpikeBanner();
  initMonth();
  renderCalendars();
  updateLastUpdate();
  setupMonthButtons();
};

// ----------- データ読込 -----------
async function loadAllData() {
  calendarData = await fetchJson(DATA_PATH);
  prevCalendarData = await fetchJson(PREV_DATA_PATH);
  eventData = await fetchJson(EVENT_PATH);
  historicalData = await fetchJson(HISTORICAL_PATH);
  spikeData = await fetchJson(SPIKE_PATH);
}
async function fetchJson(path) {
  try {
    const res = await fetch(path + "?v=" + Date.now());
    if (!res.ok) return {};
    return await res.json();
  } catch(e) { return {}; }
}

// ----------- 需要急騰バナー -----------
function renderSpikeBanner() {
  const banner = document.getElementById("spike-banner");
  banner.innerHTML = "";
  if (!Array.isArray(spikeData) || spikeData.length === 0) {
    banner.style.display = "none";
    return;
  }
  banner.style.display = "flex";
  spikeData.slice(0, 10).forEach(s => {
    const chip = document.createElement("div");
    chip.className = "spike-chip";
    chip.innerHTML = `<span class="spike-date">🚀 ${s.date}</span>
    <span class="spike-main">${s.spike_date ? "該当日 " + s.spike_date : ""}</span>
    <span style="color:#d35400;">単価${s.price_diff > 0 ? "↑" : "↓"} ${Math.abs(s.price_diff).toLocaleString()}円</span>
    <span style="color:#2980b9;">客室${s.vacancy_diff < 0 ? "減" : "増"} ${Math.abs(s.vacancy_diff)}件</span>
    <span class="spike-comment">${s.comment ? s.comment : ""}</span>
    `;
    banner.appendChild(chip);
  });
}

// ----------- 月初期化 -----------
function initMonth() {
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth() + 1;
  currentYearMonth = [
    [year, month],
    month === 12 ? [year+1, 1] : [year, month+1]
  ];
}

// ----------- カレンダー描画 -----------
function renderCalendars() {
  const container = document.getElementById("calendar-container");
  container.innerHTML = "";
  for (let ym of currentYearMonth) {
    const calElem = renderMonthCalendar(ym[0], ym[1]);
    container.appendChild(calElem);
  }
}

// ----------- 1か月分カレンダー -----------
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

  // 各日セル
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
    // 土日祝
    const dayOfWeek = (dayCount)%7;
    if (dayOfWeek === 0) cell.classList.add("sunday");
    if (dayOfWeek === 6) cell.classList.add("saturday");
    // 祝日・イベント色分け
    let isHoliday = false;
    let events = eventData[cellDate] || [];
    if (Array.isArray(events)) {
      if (events.some(ev => ev.icon === "🎌")) isHoliday = true;
    }
    if (isHoliday) cell.classList.add("holiday");
    if (events.length > 0 && !isHoliday) cell.classList.add("event");

    // データ
    const data = calendarData[cellDate] || {};
    const prevData = prevCalendarData[cellDate] || {};
    const diffVac = typeof data.vacancy === "number" && typeof prevData.vacancy === "number"
        ? data.vacancy - prevData.vacancy : 0;
    const diffPrice = typeof data.avg_price === "number" && typeof prevData.avg_price === "number"
        ? Math.round(data.avg_price) - Math.round(prevData.avg_price) : 0;
    // 需要Lv
    let demandLv = 0;
    if (typeof data.vacancy === "number" && typeof data.avg_price === "number") {
      if (data.vacancy <= 70 || data.avg_price >= 50000) demandLv = 5;
      else if (data.vacancy <= 100 || data.avg_price >= 40000) demandLv = 4;
      else if (data.vacancy <= 150 || data.avg_price >= 35000) demandLv = 3;
      else if (data.vacancy <= 200 || data.avg_price >= 30000) demandLv = 2;
      else if (data.vacancy <= 250 || data.avg_price >= 25000) demandLv = 1;
    }
    // セルHTML
    const stock = typeof data.vacancy === "number" ? `${data.vacancy}件` : "-";
    const avgPrice = typeof data.avg_price === "number" ? data.avg_price.toLocaleString() : "-";
    const eventsHtml = events.map(ev => `<div class="cell-event">${ev.icon} ${ev.name}</div>`).join("");
    cell.innerHTML = `
      <div class="cell-date">${date}</div>
      <div class="cell-main">
        <span class="cell-vacancy">${stock}</span>
        <span class="cell-vacancy-diff ${diffVac > 0 ? "plus" : diffVac < 0 ? "minus" : "flat"}">
          ${diffVac > 0 ? "+" + diffVac : diffVac < 0 ? diffVac : "±0"}
        </span>
      </div>
      <div class="cell-price">
        ￥${avgPrice}
        <span class="cell-price-diff ${diffPrice > 0 ? "up" : diffPrice < 0 ? "down" : "flat"}">
          ${diffPrice > 0 ? "↑" : diffPrice < 0 ? "↓" : "→"}
        </span>
      </div>
      ${demandLv > 0 ? `<div class="cell-demand-badge lv${demandLv}">🔥${demandLv}</div>` : ""}
      <div class="cell-event-list">${eventsHtml}</div>
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

// ----------- 日付選択・グラフ -----------
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
function renderGraph(dateStr) {
  const graphContainer = document.getElementById("graph-container");
  graphContainer.style.display = "block";
  // 履歴データ
  const history = historicalData[dateStr];
  let stockHistory = [], priceHistory = [], labels = [];
  if (history && typeof history === "object") {
    // history: {"2025-07-24":{"vacancy":271,"avg_price":12860}, ...}
    Object.entries(history).forEach(([d, v]) => {
      labels.push(d);
      stockHistory.push(v.vacancy);
      priceHistory.push(v.avg_price);
    });
  }
  // 前後日操作
  let allDates = Object.keys(historicalData).sort();
  let idx = allDates.indexOf(dateStr);
  window.goGraphDay = function(diff) {
    let nextIdx = idx + diff;
    if (nextIdx >= 0 && nextIdx < allDates.length) {
      selectDate(allDates[nextIdx]);
    }
  };
  // グラフ
  graphContainer.innerHTML = `
    <div class="graph-btns">
      <button onclick="closeGraph()">✗ グラフを閉じる</button>
      <button onclick="goGraphDay(-1)">＜前日</button>
      <button onclick="goGraphDay(1)">翌日＞</button>
    </div>
    <h3>${dateStr} の在庫・価格推移</h3>
    <div style="margin-bottom:18px;">
      <canvas id="stockChart" width="420" height="180"></canvas>
    </div>
    <div>
      <canvas id="priceChart" width="420" height="180"></canvas>
    </div>
  `;
  if(window.stockChartInstance) window.stockChartInstance.destroy();
  if(window.priceChartInstance) window.priceChartInstance.destroy();
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
          y: { beginAtZero: false, title: { display: true, text: "平均価格（円）" } },
          x: { title: { display: true, text: "日付" } }
        }
      }
    });
  }
}
function closeGraph() {
  document.getElementById("graph-container").style.display = "none";
  document.querySelectorAll('.calendar-cell.selected').forEach(cell => {
    cell.classList.remove('selected');
  });
  selectedDate = null;
  if(window.stockChartInstance) { window.stockChartInstance.destroy(); window.stockChartInstance = null; }
  if(window.priceChartInstance) { window.priceChartInstance.destroy(); window.priceChartInstance = null; }
}

// ----------- 月切替ボタン -----------
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

// ----------- 最終更新日時 -----------
function updateLastUpdate() {
  document.getElementById("last-update").textContent = "最終更新日時：" + formatDate(new Date());
}
function formatDate(dt) {
  return `${dt.getFullYear()}-${String(dt.getMonth()+1).padStart(2,"0")}-${String(dt.getDate()).padStart(2,"0")} ${String(dt.getHours()).padStart(2,"0")}:${String(dt.getMinutes()).padStart(2,"0")}:${String(dt.getSeconds()).padStart(2,"0")}`;
}
