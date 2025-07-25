// ========== 設定 ==========
const DATA_PATH = "./vacancy_price_cache.json";
const PREV_DATA_PATH = "./vacancy_price_cache_previous.json";
const EVENT_PATH = "./event_data.json";
const HISTORICAL_PATH = "./historical_data.json";

// ========== グローバル状態 ==========
let calendarData = {};       // 当日分データ
let prevCalendarData = {};   // 前日分データ
let eventData = {};          // イベントデータ
let historicalData = {};     // 推移グラフ用データ

let currentYearMonth = [];   // [year, month] の配列。2か月分
let selectedDate = null;     // カレンダーで選択された日付

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
  // 枠作成
  const wrapper = document.createElement("div");
  wrapper.className = "month-calendar";
  // ヘッダー
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
    // 土日・祝日判定
    const dayOfWeek = (dayCount)%7;
    if (dayOfWeek === 0) cell.classList.add("sunday");
    if (dayOfWeek === 6) cell.classList.add("saturday");

    // データ反映（仮。後ほど詳細化）
    cell.innerHTML = `<div class="cell-main">${date}日</div>
                      <div class="cell-price"></div>
                      <div class="cell-diff"></div>
                      <div class="cell-event"></div>
                      <div class="cell-demand"></div>`;

    // クリックイベント
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
  // 選択セルのハイライト
  document.querySelectorAll('.calendar-cell').forEach(cell => {
    if (cell.dataset.date === dateStr) {
      cell.classList.add('selected');
    } else {
      cell.classList.remove('selected');
    }
  });
  // グラフ表示
  renderGraph(dateStr);
}

// ========== グラフ描画（仮） ==========
function renderGraph(dateStr) {
  const graphContainer = document.getElementById("graph-container");
  graphContainer.style.display = "block";
  graphContainer.innerHTML = `
    <button onclick="closeGraph()" style="float:right;">グラフを閉じる</button>
    <h3>${dateStr} の在庫・価格推移</h3>
    <div>（ここにJSグラフを描画します）</div>
  `;
}

// ========== グラフを閉じる ==========
function closeGraph() {
  document.getElementById("graph-container").style.display = "none";
  document.querySelectorAll('.calendar-cell.selected').forEach(cell => {
    cell.classList.remove('selected');
  });
  selectedDate = null;
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
  // 先頭月をずらす
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
  // 仮：vacancy_price_cache.jsonの更新日を取得
  document.getElementById("last-update").textContent = formatDate(new Date());
}

function formatDate(dt) {
  // yyyy-mm-dd hh:mm:ss
  return `${dt.getFullYear()}-${String(dt.getMonth()+1).padStart(2,"0")}-${String(dt.getDate()).padStart(2,"0")} ${String(dt.getHours()).padStart(2,"0")}:${String(dt.getMinutes()).padStart(2,"0")}:${String(dt.getSeconds()).padStart(2,"0")}`;
}

// ========== ここから先、カレンダーセルへの詳細データ反映・グラフ描画を拡充します ==========
