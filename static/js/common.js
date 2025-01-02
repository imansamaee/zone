function showAlert(type, message) {
  const alertContainer = document.getElementById('alert-container');
  const alert = `
    <div class="alert alert-${type} alert-dismissible fade show" role="alert">
      ${message}
      <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>
  `;
  alertContainer.innerHTML = alert;

  setTimeout(() => {
    const alertElement = alertContainer.querySelector('.alert');
    if (alertElement) {
      bootstrap.Alert.getOrCreateInstance(alertElement).close();
    }
  }, 3000);
}

async function runBackend(endpoint, method, successMessage) {
  try {
    const response = await fetch(endpoint, { method: method }); 
    if (response.ok) {
      const data = await response.json();
      showAlert('success', data.message || successMessage);
    } else {
      showAlert('danger', `Error ${method} ${endpoint}`); 
    }
  } catch (error) {
    console.error(`Error ${method} ${endpoint}:`, error);
    showAlert('danger', `Error ${method} ${endpoint}`); 
  }
}



function createChart(containerId, klines, data) {

  const authorizationTime = data.crypto.current_time;
  const symbol = data.trade_time_crypto.symbol;
  const buyPrice = data.order.buy_order.price;
  const sellOrderLimit = data.order.sell_order_limit_marker;
  const sellOrderStop = data.order.sell_order_stop_loss;
  const buyOrder = data.order.buy_order;
  const supports = data.crypto.support_resistance_1m[0];
  const resistances = data.crypto.support_resistance_1m[1];

  const stopLossPrice = sellOrderStop.stopPrice
  const limitPrice = sellOrderLimit.price

  const sellOrder = sellOrderLimit.info.status === "FILLED" ? sellOrderLimit :
    (sellOrderStop.info.status === "FILLED" ? sellOrderStop : null);

  const isOrderProfitable = sellOrder === sellOrderLimit;
  const isOrderLoss = sellOrder === sellOrderStop;

  // Parse and ensure all times are in milliseconds
  const buyTime = buyOrder.lastTradeTimestamp;
  const sellTime = sellOrder.lastTradeTimestamp;



  const ohlc = klines.map((kline, index) => {
    let color = 'white'; // Default bearish color
    let upColor = 'black'; // Default bullish color
    let lineColor = 'grey';
    let lineWidth = 1;
    // Check if the buy time falls within the candle range
    if (index < klines.length - 1 && kline[0] <= buyTime && klines[index + 1][0] > buyTime) {
      color = 'blue';
      upColor = 'blue';
      lineColor = 'indigo';
      lineWidth = 4;
    }

    // Check if the sell time falls within the candle range
    if (index < klines.length - 1 && kline[0] <= sellTime && klines[index + 1][0] > sellTime) {
      color = 'green';
      upColor = 'green';
      lineColor = 'green';
      lineWidth = 4;
    }

    // Check if the sell time falls within the candle range
    if (index < klines.length - 1 && kline[0] <= authorizationTime && klines[index + 1][0] > authorizationTime) {
      color = 'orange';
      upColor = 'orange';
      lineColor = 'red';
      lineWidth = 4;
    }
    return {
      x: kline[0],
      open: parseFloat(kline[1]),
      high: parseFloat(kline[2]),
      low: parseFloat(kline[3]),
      close: parseFloat(kline[4]),
      color: color,
      upColor: upColor,
      lineColor: lineColor,
      lineWidth: lineWidth,
    };
  });

  const seriesData = [{
    type: 'candlestick',
    name: symbol,
    data: ohlc,
    color: 'white',
    upColor: 'black',
    dataGrouping: {enabled: false}
  }];

  const priceLines = [
    {name: "Buy Price", price: buyPrice, color: "blue", dashArray: "5, 5", lineWidth: 2},
    {name: "Stop Loss", price: stopLossPrice, color: "red", dashArray: "5, 5", lineWidth: 2},
    {name: "Limit", price: limitPrice, color: "green", dashArray: "5, 5", lineWidth: 2},
  ];

  priceLines.forEach(line => {
    seriesData.push({
      type: 'line',
      name: line.name,
      data: [
        [klines[0][0], parseFloat(line.price)],
        [klines[klines.length - 1][0], parseFloat(line.price)]
      ],
      color: line.color,
      dashStyle: 'Dash', // Add dashStyle property
      lineWidth: 2
    });
  });

  supports.forEach(support => {
    seriesData.push({
      type: 'line',
      name: 'S - ' + support[1],
      data: [
        [klines[0][0], parseFloat(support[0])],
        [klines[klines.length - 1][0], parseFloat(support[0])]
      ],
      color: 'green',
      lineWidth: 2
    });
  });

  resistances.forEach(resistance => {
    console.log(resistance);
    seriesData.push({
      type: 'line',
      name: 'R - ' + resistance[1],
      data: [
        [klines[0][0], parseFloat(resistance[0])],
        [klines[klines.length - 1][0], parseFloat(resistance[0])]
      ],
      color: 'red',
      lineWidth: 2
    });
  });


  Highcharts.stockChart(containerId, {
    chart: {
      height: '100%',
      events: {
        load: function () {
          const chart = this;
          setTimeout(() => {
            chart.xAxis[0].setExtremes(
              Math.min(authorizationTime, sellTime) - (2 * 60 * 1000),
              Math.max(authorizationTime, sellTime) + (1 * 60 * 1000)
            );
          }, 1000);
        }
      }
    },
    rangeSelector: {enabled: false},
    title: {
      text: `${symbol}`,
      useHTML: true,
      align: 'left'
    },
    yAxis: [{
      labels: {align: 'right', x: -3},
      title: {text: 'OHLC'},
      height: '100%',
      lineWidth: 2,
      resize: {enabled: true}
    }],
    xAxis: {type: 'datetime'},
    series: seriesData,
    plotOptions: {
      series: {turboThreshold: 0},
      candlestick: {
        dataLabels: {enabled: false}
      }
    }
  });

  function formatDuration(milliseconds) {
    const totalSeconds = Math.floor(milliseconds / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  }
}

function formatDuration(milliseconds) {
  const totalSeconds = Math.floor(milliseconds / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}
