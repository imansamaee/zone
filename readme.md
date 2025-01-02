sudo systemctl stop tagtrade.service
sudo systemctl start tagtrade.service
tail -f /root/tagTrade/main.log
rm -rf ~/.vscode-server  # Delete the VS Code Server folder


'''
{
   "info":{
      "symbol":"BNBUSDT",
      "orderId":"4968178172",
      "orderListId":"-1",
      "clientOrderId":"ios_561f5e1046a3462dab2dded4b1955eb3",
      "price":"320.00000000",
      "origQty":"0.03200000",
      "executedQty":"0.03200000",
      "cummulativeQuoteQty":"10.26880000",
      "status":"FILLED",
      "timeInForce":"GTC",
      "type":"LIMIT",
      "side":"SELL",
      "stopPrice":"0.00000000",
      "icebergQty":"0.00000000",
      "time":"1704018105181",
      "updateTime":"1704018105181",
      "isWorking":true,
      "workingTime":"1704018105181",
      "origQuoteOrderQty":"0.00000000",
      "selfTradePreventionMode":"EXPIRE_MAKER"
   },
   "id":"4968178172",
   "clientOrderId":"ios_561f5e1046a3462dab2dded4b1955eb3",
   "timestamp":1704018105181,
   "datetime":"2023-12-31T10:21:45.181Z",
   "lastTradeTimestamp":1704018105181,
   "lastUpdateTimestamp":1704018105181,
   "symbol":"BNB/USDT",
   "type":"limit",
   "timeInForce":"GTC",
   "postOnly":false,
   "reduceOnly":"None",
   "side":"sell",
   "price":320.0,
   "triggerPrice":"None",
   "amount":0.032,
   "cost":10.2688,
   "average":320.9,
   "filled":0.032,
   "remaining":0.0,
   "status":"closed",
   "fee":{
      "currency":"None",
      "cost":"None",
      "rate":"None"
   },
   "trades":[
      
   ],
   "fees":[
      {
         "currency":"None",
         "cost":"None",
         "rate":"None"
      }
   ],
   "stopPrice":"None",
   "takeProfitPrice":"None",
   "stopLossPrice":"None"
}
'''


{
  "33522802246": {  // Order ID
    "info": {  // Raw order information from Binance
      "symbol": "BTCUSDT",  // Trading pair
      "orderId": "33522802246",  // Order ID
      "orderListId": "-1",  // ID of the order list (not applicable here)
      "clientOrderId": "x-R4BD3S829811d79e75a8da9a02e09f",  // Client-generated order ID
      "transactTime": "1733744128410",  // Timestamp of order transaction
      "price": "100000.00000000",  // Order price
      "origQty": "0.00010000",  // Original order quantity
      "executedQty": "0.00010000",  // Executed order quantity
      "cummulativeQuoteQty": "9.83127500",  // Cumulative quote asset quantity
      "status": "FILLED",  // Order status
      "timeInForce": "GTC",  // Time in force (Good Till Cancelled)
      "type": "LIMIT",  // Order type
      "side": "BUY",  // Order side
      "workingTime": "1733744128410",  // Timestamp when the order began processing
      "fills": [  // Array of fills (individual executions)
        {
          "price": "98312.75000000",  // Fill price
          "qty": "0.00010000",  // Fill quantity
          "commission": "0.00000010",  // Commission paid for this fill
          "commissionAsset": "BTC",  // Asset in which commission was paid
          "tradeId": "4230393379"  // ID of the trade associated with this fill
        }
      ],
      "selfTradePreventionMode": "EXPIRE_MAKER"  // Self-trade prevention mode
    },
    "id": "33522802246",  // Order ID
    "clientOrderId": "x-R4BD3S829811d79e75a8da9a02e09f",  // Client-generated order ID
    "timestamp": 1733744128410,  // Timestamp of order creation
    "datetime": "2024-12-09T11:35:28.410Z",  // Date and time of order creation
    "lastTradeTimestamp": 1733744128410,  // Timestamp of the last trade associated with this order
    "lastUpdateTimestamp": 1733744128410,  // Timestamp of the last order update
    "symbol": "BTC/USDT",  // Trading pair
    "type": "limit",  // Order type
    "timeInForce": "GTC",  // Time in force
    "postOnly": false,  // Whether the order is post-only
    "reduceOnly": null,  // Whether the order is reduce-only
    "side": "buy",  // Order side
    "price": 100000,  // Order price
    "triggerPrice": null,  // Trigger price (not applicable for limit orders)
    "amount": 0.0001,  // Order quantity
    "cost": 9.831275,  // Total cost of the order
    "average": 98312.75,  // Average fill price
    "filled": 0.0001,  // Filled quantity
    "remaining": 0,  // Remaining quantity
    "status": "closed",  // Order status
    "fee": {  // Information about the fee paid
      "currency": "BTC",  // Currency in which the fee was paid
      "cost": 1e-7  // Fee amount
    },
    "trades": [  // Array of trades associated with this order
      {
        "info": {  // Raw trade information from Binance
          // ... (same fields as in the "fills" array above) ...
        },
        "timestamp": null,  // Timestamp of the trade (might be null if not provided by Binance)
        "datetime": null,  // Date and time of the trade
        "symbol": "BTC/USDT",  // Trading pair
        "id": "4230393379",  // Trade ID
        "order": null,  // Order ID associated with this trade
        "type": null,  // Trade type (might be null if not provided by Binance)
        "side": null,  // Trade side (might be null if not provided by Binance)
        "takerOrMaker": null,  // Whether the trade was a taker or maker (might be null)
        "price": 98312.75,  // Trade price
        "amount": 0.0001,  // Trade quantity
        "cost": 9.831275,  // Total cost of the trade
        "fee": {  // Information about the fee paid for this trade
          "currency": "BTC",  // Currency in which the fee was paid
          "cost": 1e-7  // Fee amount
        },
        "fees": [  // Array of fees (in case multiple fees apply)
          {
            "currency": "BTC",  // Currency in which the fee was paid
            "cost": 1e-7  // Fee amount
          }
        ]
      }
    ],
    "fees": [  // Array of fees paid for the entire order
      {
        "currency": "BTC",  // Currency in which the fee was paid
        "cost": 1e-7  // Fee amount
      }
    ],
    "stopPrice": null,  // Stop price (not applicable for limit orders)
    "takeProfitPrice": null,  // Take profit price (not applicable here)
    "stopLossPrice": null  // Stop loss price (not applicable here)
  }
}