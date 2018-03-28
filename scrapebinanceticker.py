from binance.client import Client
import threading
import datetime
import json

client = Client('CyyxfQcp7XGGIU7s5GN48TI8ViGRmUFfOB98pNQUyk1aM3XlxBaTNc87UXgo3TQZ', 'GFkq21d5RECuM3iYR6OY5Jm7fdUPueoz2SWYoGhaYLNQIPIU4PX4SPOL9cXct2OP')


def printit():
  threading.Timer(1, printit).start()
  with open("C:/Users/rishi\Documents\Scripts\Arb\BinanceScraping/1 Second Pitch (2)\Binance_Ticker_{}.json".format(str(datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S"))), 'w') as f: 
        f.write(json.dumps(client.get_orderbook_tickers()))
        print('-----')
        print('Writing to ', f)
printit()