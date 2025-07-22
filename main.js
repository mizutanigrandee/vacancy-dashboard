const calendarEl = document.getElementById('calendar');
let vacancyData = {};
let eventData = [];
let historicalData = [];
let currentMonth = moment();

async function loadData() {
  try {
    // JSONデータの読み込み
    const vacancyResponse = await fetch('vacancy_price_cache.json');
    vacancyData = await vacancyResponse.json();

    const historicalResponse = await fetch('historical_data.json');
    historicalData = await historicalResponse.json();

    // Excelデータの読み込み
    const eventResponse = await fetch('event_data.xlsx');
    const arrayBuffer = await eventResponse.arrayBuffer();
    const workbook = XLSX.read(new Uint8Array(arrayBuffer), { type: 'array' });
    eventData = XLSX.utils.sheet_to_json(workbook.Sheets[workbook.SheetNames[0]]);
    // Excelシリアル値を日付に変換
    eventData = eventData.map(event => ({
      ...event,
      date: moment('1899-12-30').add(event.date, 'days').format('YYYY-MM-DD')
    }));
  } catch (error) {
    console.error('データ読み込みエラー:', error);
  }
  renderCalendar();
  renderGraph();
}

function renderCalendar() {
  const html = [];
  html.push('<div class="grid grid-cols-7 gap-1 text-center">');
  html.push('<div class="col-span-7 flex justify-between mb-2">');
  html.push(`<button onclick="changeMonth(-1)" class="px-4 py-2 bg-blue-500 text-white rounded">&lt;</button>`);
  html.push(`<h2 class="text-xl">${currentMonth.format('YYYY年MM月')}</h2>`);
  html.push(`<button onclick="changeMonth(1)" class="px-4 py-2 bg-blue-500 text-white rounded">&gt;</button>`);
  html.push('</div>');

  // 曜日ヘッダ
  const days = ['日', '月', '火', '水', '木', '金', '土'];
  days.forEach(day => {
    html.push(`<div class="font-bold">${day}</div>`);
  });

  // カレンダー生成
  const startOfMonth = currentMonth.clone().startOf('month');
  const endOfMonth = currentMonth.clone().endOf('month');
  const startWeek = startOfMonth.day();
  const daysInMonth = endOfMonth.date();

  // 空白セル
  for (let i = 0; i < startWeek; i++) {
    html.push('<div></div>');
  }

  // 日付セル
  for (let day = 1; day <= daysInMonth; day++) {
    const date = currentMonth.clone().date(day).format('YYYY-MM-DD');
    const data = vacancyData[date] || { vacancy: '-', avg_price: '-', previous_avg_price: '-' };
    const priceDiff = data.avg_price !== '-' && data.previous_avg_price !== '-' ? 
      Math.round(data.avg_price - data.previous_avg_price) : null;
    const events = eventData.filter(e => e.date === date);
    
    html.push(`
      <div class="p-2 border rounded relative hover:bg-gray-100">
        <div class="text-right">${day}</div>
        <div>空室: ${data.vacancy}</div>
        <div>価格: ${data.avg_price}円</div>
        ${priceDiff !== null ? `<div class="${priceDiff >= 0 ? 'text-red-500' : 'text-green-500'}">
          ${priceDiff >= 0 ? '+' : ''}${priceDiff}円</div>` : ''}
        ${events.map(e => `<div class="text-xs">${e.icon} ${e.name}</div>`).join('')}
      </div>`);
  }
  html.push('</div>');
  calendarEl.innerHTML = html.join('');
}

function changeMonth(offset) {
  currentMonth.add(offset, 'months');
  renderCalendar();
}

function renderGraph() {
  const ctx = document.getElementById('priceChart').getContext('2d');
  const dates = Object.keys(historicalData).sort();
  const graphData = dates.map(date => ({
    date,
    vacancy: historicalData[date][date]?.vacancy || 0,
    avg_price: historicalData[date][date]?.avg_price || 0
  }));

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: graphData.map(d => d.date),
      datasets: [
        {
          label: '平均価格',
          data: graphData.map(d => d.avg_price),
          borderColor: 'blue',
          fill: false
        },
        {
          label: '空室数',
          data: graphData.map(d => d.vacancy),
          borderColor: 'green',
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      scales: {
        x: { title: { display: true, text: '日付' } },
        y: { title: { display: true, text: '値' } }
      }
    }
  });
}

document.addEventListener('DOMContentLoaded', loadData);
