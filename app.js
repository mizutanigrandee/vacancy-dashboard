const API_URL = './vacancy_price_cache.json'; // 本番データをここに指定
const EVENT_URL = './event_data.json'; // イベント情報

let currentOffset = 0;
let rawData = {};
let eventData = {};

document.addEventListener('DOMContentLoaded', async () => {
  await fetchData();
  renderCalendar(currentOffset);
  setupButtons();
});

async function fetchData() {
  const [res1, res2] = await Promise.all([
    fetch(API_URL).then(r => r.json()),
    fetch(EVENT_URL).then(r => r.json())
  ]);
  rawData = res1;
  eventData = res2;
  document.getElementById("last-updated").textContent = `最終更新：${new Date().toLocaleDateString()}`;
}

function setupButtons() {
  document.getElementById('prev-month').onclick = () => {
    currentOffset--;
    renderCalendar(currentOffset);
  };
  document.getElementById('current-month').onclick = () => {
    currentOffset = 0;
    renderCalendar(currentOffset);
  };
  document.getElementById('next-month').onclick = () => {
    currentOffset++;
    renderCalendar(currentOffset);
  };
}

function renderCalendar(offset) {
  const container = document.getElementById('calendar-container');
  container.innerHTML = '';
  const baseDate = new Date();
  baseDate.setMonth(baseDate.getMonth() + offset);
  for (let i = 0; i < 2; i++) {
    const date = new Date(baseDate);
    date.setMonth(baseDate.getMonth() + i);
    container.appendChild(createCalendar(date));
  }
}

function createCalendar(date) {
  const year = date.getFullYear();
  const month = date.getMonth();
  const first = new Date(year, month, 1);
  const last = new Date(year, month + 1, 0);
  const startDay = first.getDay();

  const table = document.createElement('table');
  const header = document.createElement('caption');
  header.textContent = `${year}年${month + 1}月`;
  table.appendChild(header);

  const weekdays = ['日', '月', '火', '水', '木', '金', '土'];
  const tr = document.createElement('tr');
  weekdays.forEach(day => {
    const th = document.createElement('th');
    th.textContent = day;
    tr.appendChild(th);
  });
  table.appendChild(tr);

  let trBody = document.createElement('tr');
  for (let i = 0; i < startDay; i++) {
    const td = document.createElement('td');
    td.className = 'empty';
    trBody.appendChild(td);
  }

  for (let d = 1; d <= last.getDate(); d++) {
    if ((startDay + d - 1) % 7 === 0 && d > 1) {
      table.appendChild(trBody);
      trBody = document.createElement('tr');
    }

    const td = document.createElement('td');
    const cellDate = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    const info = rawData[cellDate];

    td.className = ['日', '土'].includes(weekdays[(startDay + d - 1) % 7])
      ? weekdays[(startDay + d - 1) % 7] === '日' ? 'sunday' : 'saturday'
      : '';

    const dayNum = document.createElement('div');
    dayNum.className = 'date-number';
    dayNum.textContent = d;
    td.appendChild(dayNum);

    if (info) {
      const v = document.createElement('span');
      v.className = 'vacancy';
      v.innerHTML = `${info.vacancy}件 ${info.previous_vacancy !== undefined ? `(${formatDiff(info.vacancy - info.previous_vacancy)})` : ''}`;
      td.appendChild(v);

      const p = document.createElement('span');
      p.className = 'price';
      p.innerHTML = `¥${info.avg_price.toLocaleString()} ${priceArrow(info.avg_price, info.previous_avg_price)}`;
      td.appendChild(p);
    }

    if (eventData[cellDate]) {
      const ev = document.createElement('div');
      ev.className = 'event';
      ev.innerHTML = eventData[cellDate];
      td.appendChild(ev);
    }

    trBody.appendChild(td);
  }

  while (trBody.children.length < 7) {
    const td = document.createElement('td');
    td.className = 'empty';
    trBody.appendChild(td);
  }
  table.appendChild(trBody);

  const wrapper = document.createElement('div');
  wrapper.className = 'calendar';
  wrapper.appendChild(table);
  return wrapper;
}

function formatDiff(num) {
  if (num > 0) return `<span class="up">+${num}</span>`;
  if (num < 0) return `<span class="down">${num}</span>`;
  return '±0';
}

function priceArrow(curr, prev) {
  if (curr > prev) return `<span class="up">↑</span>`;
  if (curr < prev) return `<span class="down">↓</span>`;
  return '';
}
