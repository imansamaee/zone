$(function () {
  const urlParams = new URLSearchParams(window.location.search);
  const file = urlParams.get('file');

  if (!file) {
    console.error("No filename provided.");
    return;
  }

  fetch(`/static/pairs_history/${file}`)
    .then(response => response.json())
    .then(data => {

      const authorizationTime = data.crypto.current_time;
      const sellOrderLimit = data.order.sell_order_limit_marker;
      const sellOrderStop = data.order.sell_order_stop_loss;
      const buyOrder = data.order.buy_order;

    
      const sellOrder = sellOrderLimit.info.status === "FILLED" ? sellOrderLimit :
        (sellOrderStop.info.status === "FILLED" ? sellOrderStop : null);
  
    
      // Parse and ensure all times are in milliseconds
      const buyTime = buyOrder.lastTradeTimestamp;
      const sellTime = sellOrder.lastTradeTimestamp;

      // Populate the chart-info div
      const chartInfo = document.getElementById('chart-info');
      chartInfo.innerHTML = ` 
        <div class="container-fluid"> 
        <div class="row"> 
        <div class="col-md-2"> 
        <ul style="list-style: none; padding: 0; margin: 0; "> 
        <li style="display: flex; justify-content: space-between; align-items: center; padding: 5px; border-bottom: 1px solid black;"> <span>Auth Time:</span> <span>${new Date(authorizationTime).toLocaleTimeString('en-GB', { timeZone: 'Europe/London' })}</span> </li> 
        <li style="display: flex; justify-content: space-between; align-items: center; padding: 5px; border-bottom: 1px solid black;"> <span>Buy Time:</span> <span>${new Date(buyTime).toLocaleTimeString('en-GB', { timeZone: 'Europe/London' })}</span> </li> 
        <li style="display: flex; justify-content: space-between; align-items: center; padding: 5px; border-bottom: 1px solid black;"> <span>Sell Time:</span> <span>${new Date(sellTime).toLocaleTimeString('en-GB', { timeZone: 'Europe/London' })}</span> </li> 
        </ul> 
        </div> 
        <div class="col-md-2"> 
        <ul style="list-style: none; padding: 0; margin: 0; "> 
        <li style="display: flex; justify-content: space-between; align-items: center; padding: 5px; border-bottom: 1px solid black;"> <span>Buy Waiting:</span> <span>${formatDuration(buyTime - authorizationTime)}</span> </li> 
        <li style="display: flex; justify-content: space-between; align-items: center; padding: 5px; border-bottom: 1px solid black;"> <span>Trade Duration:</span> <span>${formatDuration(sellTime - buyTime)}</span> </li> 
        <li style="display: flex; justify-content: space-between; align-items: center; padding: 5px; border-bottom: 1px solid black;"> <span>Whole Duration:</span> <span>${formatDuration(sellTime - authorizationTime)}</span> </li> 
        </ul> 
        </div> 
        <div class="col-md-2"> 
        <ul style="list-style: none; padding: 0; margin: 0; "> 
        <li style="display: flex; justify-content: space-between; align-items: center; padding: 5px; border-bottom: 1px solid black;"> <span>Buy Price:</span> <span>${data.order.buy_order.price}</span> </li> 
        <li style="display: flex; justify-content: space-between; align-items: center; padding: 5px; border-bottom: 1px solid black;"> <span>Stop Loss Price:</span> <span>${data.order.sell_order_stop_loss.stopPrice}</span> </li> 
        <li style="display: flex; justify-content: space-between; align-items: center; padding: 5px; border-bottom: 1px solid black;"> <span>Limit Price:</span> <span>${data.order.sell_order_limit_marker.price}</span> </li> 
        </ul> 
        </div> 
                <div class="col-md-2"> 
        <ul style="list-style: none; padding: 0; margin: 0; "> 
        <li style="display: flex; justify-content: space-between; align-items: center; padding: 5px; border-bottom: 1px solid black;"> <span>Symbol:</span> <span>${data.trade_time_crypto.symbol}</span> </li> 
        <li style="display: flex; justify-content: space-between; align-items: center; padding: 5px; border-bottom: 1px solid black;"> <span>PNL:</span> <span>${data.pnl}</span> </li> 
        </ul> 
        </div> 
                        <div class="col-md-2"> 
        <ul style="list-style: none; padding: 0; margin: 0; "> 
        <li style="display: flex; justify-content: space-between; align-items: center; padding: 5px; border-bottom: 1px solid black;"> <span>Symbol:</span> <span>${data.trade_time_crypto.symbol}</span> </li> 
        <li style="display: flex; justify-content: space-between; align-items: center; padding: 5px; border-bottom: 1px solid black;"> <span>PNL:</span> <span>${data.pnl}</span> </li> 
        </ul> 
        </div> 
                        <div class="col-md-2"> 
        <ul style="list-style: none; padding: 0; margin: 0; "> 
        <li style="display: flex; justify-content: space-between; align-items: center; padding: 5px; border-bottom: 1px solid black;"> <span>Symbol:</span> <span>${data.trade_time_crypto.symbol}</span> </li> 
        <li style="display: flex; justify-content: space-between; align-items: center; padding: 5px; border-bottom: 1px solid black;"> <span>PNL:</span> <span>${data.pnl}</span> </li> 
        </ul> 
        </div> 
        </div> 
        </div>
      `;

      const klines1m = data.trade_time_crypto.klines_1m;
      createChart('chart-container-1m', klines1m, data);

      const klinescover = data.trade_time_crypto.klines_cover;
      createChart('chart-container-cover', klinescover, data);
    });
});
