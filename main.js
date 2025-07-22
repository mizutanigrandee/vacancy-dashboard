const calendarEl = document.getElementById('calendar');
let vacancyData = {};
let eventData = [];
let historicalData = [];
let currentMonth = moment();

async function loadData() {
  try {
    const vacancyResponse = await fetch('vacancy_price_cache.json');
    vacancyData = await vacancyResponse.json();

    const historicalResponse = await fetch('historical_data.json');
    historicalData = await historicalResponse.json();

    const eventResponse = await fetch('event_data.xlsx');
    const arrayBuffer = await eventResponse.arrayBuffer();
    const workbook = XLSX.read(new Uint8Array(arrayBuffer), { type: 'array' });
    eventData = XLSX.utils.sheet_to_json(workbook.Sheets[workbook.SheetNames[0]]);
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
  html.push(`<button onclick="changeMonth(-1)" class="px-2 py-1 bg-blue-500 text-white rounded"><</button>`);
  html.push(`<h2 class="text-xl">${currentMonth.format('YYYY年MM月')}</h2>`);
  html.push(`<button onclick="changeMonth(1)" class="px-2 py-1 bg-blue-500 text-white rounded">></button>`);
  html.push('</div>');

  const days = ['日', '月', '火', '水', '木', '金', '土'];
  days.forEach((day, i) => {
    html.push(`<div class="font-bold ${i === 6 ? 'text-red-500' : 'text-black'}">${day}</div>`);
  });

  const startOfMonth = currentMonth.clone().startOf('month');
  const endOfMonth = currentMonth.clone().endOf('month');
  const startWeek = startOfMonth.day();
  const daysInMonth = endOfMonth.date();

  for (let i = 0; i < startWeek; i++) html.push('<div></div>');
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
        <div>価格: ${data.avg_price !== '-' ? `¥${data.avg_price.toLocaleString()}` : '-'}</div>
        ${priceDiff !== null ? `<div class="${priceDiff >= 0 ? 'text-red-500' : 'text-green-500'}">
          ${priceDiff >= 0 ? '+' : ''}¥${Math.abs(priceDiff).toLocaleString()}</div>` : ''}
        ${events.map(e => `<div class="text-red-500 text-xs">${e.name}</div>`).join('')}
      </div>`);
  }
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
          yAxisID: 'y1',
          fill: false
        },
        {
          label: '空室数',
          data: graphData.map(d => d.vacancy),
          borderColor: 'green',
          yAxisID: 'y2',
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      scales: {
        x: { title: { display: true, text: '日付' } },
        y1: { type: 'linear', position: 'left', title: { display: true, text: '価格 (¥)' }, ticks: { callback: value => `¥${value.toLocaleString()}` } },
        y2: { type: 'linear', position: 'right', title: { display: true, text: '空室数' }, grid: { drawOnChartArea: false } }
      },
      plugins: { legend: { position: 'top' } }
    }
  });
}

document.addEventListener('DOMContentLoaded', loadData);
