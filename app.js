// ========== データ & 祝日設定 ==========

// ========= モード（1名 / 2名） =========
const MODE_CONFIG = {
  "1p": {
    DATA_PATH: "./vacancy_price_cache.json",
    PREV_PATH: "./vacancy_price_cache_previous.json",
    HIST_PATH: "./historical_data.json",
  },
  "2p": {
    DATA_PATH: "./vacancy_price_cache_2p.json",
    PREV_PATH: "./vacancy_price_cache_2p_previous.json",
    HIST_PATH: "./historical_data_2p.json",
  }
};

// 共通（モード非依存）
const EVENT_PATH = "./event_data.json";
const SPIKE_PATH = "./demand_spike_history.json";   // ※当面は1名のまま運用（後回し）
const LASTUPDATED_PATH = "./last_updated.json";

// 現在モード（localStorageに保存）
(() => {
  const v = localStorage.getItem("avgMode");
  if (v !== "1p" && v !== "2p") localStorage.setItem("avgMode", "1p");
})();
let currentMode = localStorage.getItem("avgMode") || "1p";

function getModeConf() {
  return MODE_CONFIG[currentMode] || MODE_CONFIG["1p"];
}
function modeLabel() {
  return currentMode === "2p" ? "2名平均" : "1名平均";
}


// グローバル状態
let calendarData   = {},
    prevData       = {},
    eventData      = {},
    historicalData = {},
    spikeData      = {};   // ←追加
let currentYM = [], selectedDate = null;

// ========== 祝日判定（ローカルjs方式） ==========
function isHoliday(date) {
  if (!window.JapaneseHolidays) return null;
  return window.JapaneseHolidays.isHoliday(date);
}

// ========== ヘルパー ==========
const todayIso = () => new Date().toISOString().slice(0,10);

// --- 自社比較モード（localStorage初期化＆厳密判定） ---
(() => {
  const v = localStorage.getItem("compareMode");
  if (v !== "1" && v !== "0") localStorage.setItem("compareMode", "0"); // 既定OFF
})();
const isCompareModeOn = () => localStorage.getItem("compareMode") === "1";

// 汎用ロード
async function loadJson(path) {
  try {
    const res = await fetch(path + "?cb=" + Date.now()); // no-cache
    if (!res.ok) return {};
    return await res.json();
  } catch {
    return {};
  }
}
async function loadAll() {
  const conf = getModeConf();
  calendarData   = await loadJson(conf.DATA_PATH);
  prevData       = await loadJson(conf.PREV_PATH);
  eventData      = await loadJson(EVENT_PATH);
  historicalData = await loadJson(conf.HIST_PATH);
  spikeData      = await loadJson(SPIKE_PATH);   // 当面は1名（後回し）
}


// ========== 1名/2名 タブ（DOMへ自動挿入） ==========
function ensureAvgModeTabs() {
  // すでにあるなら何もしない
  if (document.getElementById("avg-mode-tabs")) return;

  // 既存の spike-banner の直前に差し込む（ページ上部に出せる）
  const bannerDiv = document.getElementById("spike-banner");
  if (!bannerDiv || !bannerDiv.parentNode) return;

  const wrap = document.createElement("div");
  wrap.id = "avg-mode-tabs";
  wrap.className = "avg-mode-tabs";
  wrap.innerHTML = `
    <button class="avg-tab" data-mode="1p">1名平均</button>
    <button class="avg-tab" data-mode="2p">2名平均</button>
  `;

  bannerDiv.parentNode.insertBefore(wrap, bannerDiv);

  // クリックイベント
  wrap.querySelectorAll(".avg-tab").forEach(btn => {
    btn.addEventListener("click", async () => {
      const m = btn.dataset.mode;
      if (m === currentMode) return;

      currentMode = m;
      localStorage.setItem("avgMode", currentMode);

      // データ再読み込み → 再描画
      await loadAll();
      renderPage();
      updateLastUpdate();
    });
  });

  // 初期のアクティブ反映
  updateAvgModeTabsActive();
}

function updateAvgModeTabsActive() {
  const wrap = document.getElementById("avg-mode-tabs");
  if (!wrap) return;
  wrap.querySelectorAll(".avg-tab").forEach(b => {
    b.classList.toggle("is-active", b.dataset.mode === currentMode);
  });
}


// ▼ 追加：自社ラインの有無を保証（取りこぼし対策）
function ensureCompareLineFor(dateStr){
  if (!window.pc || !window.pc.data) return;

  const isOn = isCompareModeOn();
  const labels = window.pc.data.labels || [];
  const hasMine = (window.pc.data.datasets || []).some(d => String(d.label) === "自社");

  const myPrice = Number((calendarData[dateStr] || {}).my_price || 0);
  const shouldShow = isOn && myPrice > 0;

  // 追加が必要
  if (shouldShow && !hasMine){
    window.pc.data.datasets.push({
      label: "自社",
      data: Array(labels.length).fill(myPrice),
      fill: false,
      borderColor: "#ff9800",
      borderDash: [6,4],
      pointRadius: 0
    });
    if (window.pc.options?.plugins?.legend) {
      window.pc.options.plugins.legend.display = true;
    }
    try { window.pc.update(); } catch(e){}
    return;
  }

  // 削除が必要（ONでもmyPriceが0/未定義なら消す、OFFなら消す）
  if ((!shouldShow && hasMine) || (!isOn && hasMine)){
    window.pc.data.datasets = window.pc.data.datasets.filter(d => String(d.label) !== "自社");
    if (window.pc.options?.plugins?.legend) {
      window.pc.options.plugins.legend.display = window.pc.data.datasets.length > 1;
    }
    try { window.pc.update(); } catch(e){}
  }
}


// ========== 需要スパイク履歴バナー ==========
// サマリー：直近3日分×最大10件（※当日〜3日先は除外）
function renderSpikeBanner() {
  const bannerDiv = document.getElementById("spike-banner");
  if (!bannerDiv) return;

  if (!spikeData || Object.keys(spikeData).length === 0) {
    bannerDiv.innerHTML = "";
    return;
  }

  const EXCLUDE_NEAR_DAYS = 3; // 当日(0)〜3日先を除外
  const MS_PER_DAY = 24 * 60 * 60 * 1000;

  // JSTの「今日 00:00」
  const now = new Date();
  const jstNow = new Date(now.getTime() + (9 - now.getTimezoneOffset() / 60) * 60 * 60 * 1000);
  const jstToday = new Date(Date.UTC(
    jstNow.getUTCFullYear(),
    jstNow.getUTCMonth(),
    jstNow.getUTCDate(), 0, 0, 0
  ));

  const parseYMD = (ymd) => {
    const [y, m, d] = String(ymd).split("-").map(Number);
    return new Date(Date.UTC(y, m - 1, d, 0, 0, 0));
  };

  const sortedDates = Object.keys(spikeData)
    .sort((a, b) => b.localeCompare(a))
    .slice(0, 3);

  let chips = [];

  for (const up_date of sortedDates) {
    for (const spike of spikeData[up_date]) {
      const spikeDate = spike.spike_date || "";
      if (!spikeDate) continue;

      const target = parseYMD(spikeDate);
      const daysAhead = Math.floor((target - jstToday) / MS_PER_DAY);
      if (daysAhead <= EXCLUDE_NEAR_DAYS) continue;

      const priceDiff = spike.price_diff || 0;
      const priceRatio = spike.price_ratio ? (spike.price_ratio * 100).toFixed(1) : "0";
      const price = spike.price ? spike.price.toLocaleString() : "-";
      const vacancyDiff = spike.vacancy_diff || 0;
      const vacancyRatio = spike.vacancy_ratio ? (spike.vacancy_ratio * 100).toFixed(1) : "0";
      const vacancy = spike.vacancy ? spike.vacancy.toLocaleString() : "-";

      const priceTxt = `<span class='spike-price ${priceDiff > 0 ? "up" : "down"}'>単価${priceDiff > 0 ? "↑" : "↓"} ${Math.abs(priceDiff).toLocaleString()}円</span>（${priceRatio}%）`;
      const vacTxt   = `<span class='spike-vacancy ${vacancyDiff < 0 ? "dec" : "inc"}'>客室${vacancyDiff < 0 ? "減" : "増"} ${Math.abs(vacancyDiff)}</span>（${vacancyRatio}%）`;

      chips.push(
        `<div class="spike-chip">
          <span class="spike-date">[${up_date.replace(/^(\d{4})-(\d{2})-(\d{2})$/, "$2/$3 UP")}]</span>
          <span class="spike-main"><b>該当日 ${spikeDate}</b> ${priceTxt} ${vacTxt} <span class="spike-avg">平均￥${price}／残${vacancy}</span></span>
        </div>`
      );

      if (chips.length >= 10) break;
    }
    if (chips.length >= 10) break;
  }

  bannerDiv.innerHTML = chips.length
    ? `<div class="spike-banner-box">
         <span class="spike-banner-header">🚀 需要急騰検知日</span>
         <span class="spike-banner-meta">（直近3日・最大10件）</span>
         <div class="spike-chip-row">${chips.join("")}</div>
       </div>`
    : "";
}


// ========== 月送りボタン設定 ==========
function setupMonthButtons() {
  const prevBtn = document.getElementById("prevMonthBtn");
  const curBtn  = document.getElementById("currentMonthBtn");
  const nextBtn = document.getElementById("nextMonthBtn");
  if (prevBtn) prevBtn.onclick = () => { shiftMonth(-1); renderPage(); };
  if (curBtn)  curBtn.onclick  = () => { initMonth();   renderPage(); };
  if (nextBtn) nextBtn.onclick = () => { shiftMonth(1);  renderPage(); };
}
function initMonth() {
  const t = new Date(),
        y = t.getFullYear(),
        m = t.getMonth() + 1;
  currentYM = [[y, m], m === 12 ? [y+1,1] : [y, m+1]];
}
function shiftMonth(diff) {
  let [y,m] = currentYM[0];
  m += diff;
  if (m < 1)      { y--; m = 12; }
  else if (m > 12){ y++; m = 1;  }
  currentYM = [[y,m], m === 12 ? [y+1,1] : [y, m+1]];
}

// ========== ページ全体再描画 ==========
function renderPage() {
  const main = document.querySelector(".calendar-main");
  if (!main) return;

  const isMobile = window.innerWidth <= 700;
  if (isMobile) {
    main.innerHTML =
      '<div class="main-flexbox">' +
        '<div class="calendar-container" id="calendar-container"></div>' +
        '<div class="graph-side" id="graph-container"></div>' +
      '</div>';
  } else {
    main.innerHTML =
      '<div class="main-flexbox">' +
        '<div class="graph-side" id="graph-container"></div>' +
        '<div class="calendar-container" id="calendar-container"></div>' +
      '</div>';
  }

  // ★ 1名/2名タブを常に表示（index.html改修なし）
  ensureAvgModeTabs();
  updateAvgModeTabsActive();

    
  // ① バナー
  renderSpikeBanner();

  // ② カレンダー（ここで #calendar-container を作り直す＝中身が空になる）
  renderCalendars();

  // ③ ★ここで毎回トグルを差し直す
  if (typeof window.ensureCompareToggle === "function") {
    window.ensureCompareToggle();
  }

  // ③.5 ★カレンダーへ「自社：¥…」行を差し込む（月送り後に必ず実行）
  if (typeof window.renderMyLines === "function") {
    window.renderMyLines();
  }

  // ④ グラフ
  renderGraph(selectedDate);

  // ▼ 追加：グラフ作成直後に自社ラインを保証（非同期ズレ対策で二度呼ぶ）
  ensureCompareLineFor(selectedDate);
  setTimeout(() => ensureCompareLineFor(selectedDate), 0);
}


// ▼ 追加：カレンダーに「自社価格」と「自社 vs エリア差分％」を描画
window.renderMyLines = function () {
  // まず既存の表示を全クリア（再描画のたびにリセット）
  const cells = document.querySelectorAll(".calendar-cell[data-date]");
  cells.forEach(cell => {
    cell.querySelectorAll(".cell-myprice, .cell-myprice-diff").forEach(el => el.remove());
  });

  // 自社比較モードがOFFなら、ここで終了（クリアのみ）
  if (!isCompareModeOn()) return;

  cells.forEach(cell => {
    const dateStr = cell.dataset.date;
    if (!dateStr) return;

    const cur = calendarData[dateStr] || {};
    const myPrice   = Number(cur.my_price   || 0);  // 自社価格
    const areaPrice = Number(cur.avg_price || 0);   // エリア平均

    // 自社価格がなければ何も出さない
    if (!myPrice || !isFinite(myPrice)) return;

    // ---------- 1行目：自社価格 ----------
    const myLine = document.createElement("div");
    myLine.className = "cell-myprice";
    myLine.textContent = "自社: ￥" + myPrice.toLocaleString();
    // 基本価格行(.cell-price)の直後あたりに入れるイメージ
    const priceRow = cell.querySelector(".cell-price");
    if (priceRow && priceRow.nextSibling) {
      cell.insertBefore(myLine, priceRow.nextSibling);
    } else {
      cell.appendChild(myLine);
    }

    // エリア平均がなければ、差分％は出さずに終了
    if (!areaPrice || !isFinite(areaPrice)) return;

    // ---------- 2行目：差分％サイン ----------
    const diffPct   = ((myPrice - areaPrice) / areaPrice) * 100;
    const absDiff   = Math.abs(diffPct);

    // しきい値：±20％未満ならサインなし
    if (absDiff < 20) return;

    const arrow     = diffPct > 0 ? "⬆" : "⬇";
    const sign      = diffPct > 0 ? "+" : "-";
    const pctRounded = Math.round(absDiff);   // 18.3 → 18

    const diffDiv = document.createElement("div");
    diffDiv.className = "cell-myprice-diff " + (diffPct > 0 ? "higher" : "lower");
    diffDiv.textContent = `${arrow} ${sign}${pctRounded}%`;

    cell.appendChild(diffDiv);
  });
};




// ========== カレンダー描画 ==========
function renderCalendars() {
  const container = document.getElementById("calendar-container");
  if (!container) return;
  container.innerHTML = "";
  for (const [y,m] of currentYM) {
    container.appendChild(renderMonth(y,m));
  }
}

function renderMonth(y,m) {
  const wrap = document.createElement("div");
  wrap.className = "month-calendar";
  wrap.innerHTML = `<div class="month-header">${y}年${m}月</div>`;

  const grid = document.createElement("div");
  grid.className = "calendar-grid";

  // 曜日ヘッダー
  ["日","月","火","水","木","金","土"].forEach(d => {
    const c = document.createElement("div");
    c.className = "calendar-dow";
    c.textContent = d;
    grid.appendChild(c);
  });

  // 空セル
  const firstDay = new Date(y,m-1,1).getDay(),
        lastDate = new Date(y,m,0).getDate();
  for (let i=0; i<firstDay; i++){
    const e = document.createElement("div");
    e.className = "calendar-cell";
    grid.appendChild(e);
  }

  // 各日セル
  for (let d=1; d<=lastDate; d++){
    const iso = y + '-' + String(m).padStart(2,"0") + '-' + String(d).padStart(2,"0");
    const cell = document.createElement("div");
    cell.className = "calendar-cell";
    cell.dataset.date = iso;

    // 祝日判定
    let holidayName = isHoliday(iso);

    // 土日祝色分け
    const idx = (grid.children.length) % 7;
    if      (holidayName) cell.classList.add("holiday-bg");
    else if (idx === 0)   cell.classList.add("sunday-bg");
    else if (idx === 6)   cell.classList.add("saturday-bg");

    // 過去日付グレーアウト
    if (iso < todayIso()) cell.classList.add("past-date");

    // データ取得＆差分
    const cur = calendarData[iso] || {},
          prv = prevData[iso]      || {};
    const dv  = typeof cur.vacancy_diff === "number"
                ? cur.vacancy_diff
                : (cur.vacancy||0) - (prv.vacancy||0);
    const dp  = typeof cur.avg_price_diff === "number"
                ? cur.avg_price_diff
                : Math.round((cur.avg_price||0) - (prv.avg_price||0));
    const stock = cur.vacancy != null ? `${cur.vacancy}件` : "-";
    const price = cur.avg_price != null ? cur.avg_price.toLocaleString() : "-";

    // 括弧付き差分テキスト
    const dvText = dv > 0 ? `(+${dv})` : dv < 0 ? `(${dv})` : `(±0)`;

    // 需要シンボル
    let lvl = 0;
    if (cur.vacancy!=null && cur.avg_price!=null){
      if (cur.vacancy<=70  || cur.avg_price>=50000) lvl=5;
      else if (cur.vacancy<=100 || cur.avg_price>=40000) lvl=4;
      else if (cur.vacancy<=150 || cur.avg_price>=35000) lvl=3;
      else if (cur.vacancy<=200 || cur.avg_price>=30000) lvl=2;
      else if (cur.vacancy<=250 || cur.avg_price>=25000) lvl=1;
    }
    const badge = lvl ? `<div class="cell-demand-badge lv${lvl}">🔥${lvl}</div>` : "";

    // イベント
    const evs = (eventData[iso] || [])
      .map(ev => `<a href="https://www.google.com/search?q=${encodeURIComponent(ev.name)}" target="_blank" title="「${ev.name}」について調べる" class="event-link">
                    ${ev.icon} ${ev.name}
                  </a>`)
      .join("<br>");

    cell.innerHTML =
      `<div class="cell-date">${d}</div>` +
      `<div class="cell-main">
        <span class="cell-vacancy">${stock}</span>
        <span class="cell-vacancy-diff ${(dv>0?'plus':dv<0?'minus':'flat')}">${dvText}</span>
      </div>` +
      `<div class="cell-price">
        ￥${price}
        <span class="cell-price-diff ${(dp>0?'up':dp<0?'down':'flat')}">${dp>0?'↑':dp<0?'↓':'→'}</span>
      </div>` +
      badge +
      `<div class="cell-event-list">${evs}</div>`;

    cell.onclick = () => { selectedDate = iso; renderPage(); };
    grid.appendChild(cell);
  }

  wrap.appendChild(grid);
  return wrap;
}

// ========== グラフ描画 ==========
function renderGraph(dateStr){
  const gc = document.getElementById("graph-container");
  if (!gc) return;

  // まず既存チャートを必ず破棄（残像防止）
  if (window.sc) { try { window.sc.destroy(); } catch(e){} window.sc = null; }
  if (window.pc) { try { window.pc.destroy(); } catch(e){} window.pc = null; }

  if (!dateStr) { gc.innerHTML=""; return; }

  const allDates = Object.keys(historicalData).sort(),
        idx = allDates.indexOf(dateStr);

  gc.innerHTML =
    '<div class="graph-btns">' +
      '<button onclick="closeGraph()"> 当日へ戻る</button>' +
      '<button onclick="nav(-1)">< 前日</button>' +
      '<button onclick="nav(1)">翌日 ></button>' +
    '</div>' +
    `<h3>${dateStr} の在庫・価格推移</h3>` +
    '<canvas id="stockChart" width="600" height="250"></canvas>' +
    '<canvas id="priceChart" width="600" height="250"></canvas>';

  window.nav = diff => {
    const ni = idx + diff;
    if (ni >= 0 && ni < allDates.length) {
      selectedDate = allDates[ni];
      renderPage();
    }
  };
  window.closeGraph = () => {
    selectedDate = todayIso();
    renderPage();
  };

  // 市場の履歴データ
  const hist = historicalData[dateStr] || {}, labels = [], sv = [], pv = [];
  Object.keys(hist).sort().forEach(d => {
    labels.push(d);
    sv.push(hist[d].vacancy);
    pv.push(hist[d].avg_price);
  });

  if (!labels.length) return;

  // 在庫グラフ
  window.sc = new Chart(
    document.getElementById("stockChart").getContext("2d"),
    {
      type: "line",
      data: { labels, datasets: [{ data: sv, fill: false, borderColor: "#2196f3", pointRadius: 2 }] },
      options: {
        plugins: { legend: { display: false } },
        responsive: false,
        animation: false,
        scales: {
          y: { beginAtZero: true, min: 50, max: 350, title: { display: true, text: "在庫数" } },
          x: { title: { display: true, text: "日付" } }
        }
      }
    }
  );

  // 価格グラフ：自社ライン（水平）を条件追加
  const myPrice = Number((calendarData[dateStr] || {}).my_price || 0);
  const showMine = isCompareModeOn() && myPrice > 0;
  const mySeries = showMine ? Array(labels.length).fill(myPrice) : [];

  // Y軸レンジ：市場＋自社を含めて自動調整（最低レンジ5,000円）
  const yVals = pv.concat(showMine ? [myPrice] : []);
  let ymin = 10000, ymax = 40000;
  if (yVals.length) {
    const nums = yVals.filter(v => typeof v === "number" && isFinite(v));
    if (nums.length) {
      const minv = Math.min(...nums), maxv = Math.max(...nums);
      ymin = Math.min(10000, Math.floor(minv / 1000) * 1000);
      ymax = Math.max(40000, Math.ceil(maxv / 1000) * 1000);
      if (ymax - ymin < 5000) ymax = ymin + 5000;
    }
  }

  const priceDatasets = [
    { label: "市場平均", data: pv, fill: false, borderColor: "#e91e63", pointRadius: 2 }
  ];
  if (showMine) {
    priceDatasets.push({
      label: "自社",
      data: mySeries,
      fill: false,
      borderColor: "#ff9800",
      borderDash: [6,4],
      pointRadius: 0
    });
  }

  window.pc = new Chart(
    document.getElementById("priceChart").getContext("2d"),
    {
      type: "line",
      data: { labels, datasets: priceDatasets },
      options: {
        plugins: { legend: { display: priceDatasets.length > 1 } }, // 自社表示時だけ凡例ON
        responsive: false,
        animation: false,
        spanGaps: true,
        scales: {
          y: { beginAtZero: false, min: ymin, max: ymax, title: { display: true, text: "平均価格（円）" } },
          x: { title: { display: true, text: "日付" } }
        }
      }
    }
  );
}

// ========== 最終更新日時（Actions完了時刻を表示） ==========
function updateLastUpdate(){
  const el = document.getElementById("last-update");
  if (!el) return;

  fetch(LASTUPDATED_PATH + "?cb=" + Date.now())
    .then(r => r.ok ? r.json() : Promise.reject("fetch failed"))
    .then(meta => {
      const jst = meta.last_updated_jst || meta.last_updated_iso || "—";
      el.textContent = `最終更新日時：${jst}`;
      const tips = [];
      if (meta.last_updated_iso) tips.push(`ISO: ${meta.last_updated_iso}`);
      if (meta.git_sha)          tips.push(`SHA: ${meta.git_sha}`);
      if (meta.source)           tips.push(`src: ${meta.source}`);
      el.title = tips.join("\n");
    })
    .catch(() => {
      el.textContent = "最終更新日時：—";
      el.title = "last_updated.json の取得に失敗しました";
    });
}

// ========== 起動時初期化 ==========
window.onload = async () => {
  await loadAll();
  initMonth();
  if (!selectedDate) selectedDate = todayIso();
  renderPage();
  updateLastUpdate();        // ← 閲覧時刻ではなく Actions 完了時刻を表示
  setupMonthButtons();
  window.addEventListener('resize', () => { renderPage(); });
};
