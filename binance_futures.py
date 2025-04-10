from keys import api, secret
import trading_setup
from binance.um_futures import UMFutures
import pandas as pd
import time
from binance.error import ClientError
import logger_bot
from datetime import datetime, timedelta

client = UMFutures(key=api, secret=secret)

logger = logger_bot.get_logger()


intervals = {'1m': 1,
             '3m': 3,
             '5m': 5,
             '15m': 15,
             '30m': 30,
             '1h': 60,
             '2h': 120,
             '4h': 240,
             '6h': 360,
             '8h': 480,
             '12h': 720,
             '1d': 1440,
             '3d': 4320,
             '1w': 10080,
             }


# Fetch klines data from Binance
def klines(symbol, timeframe=trading_setup.TRADE_TIME, limit=1500, start=None, end=None):
    try:
        resp = pd.DataFrame(client.klines(symbol, timeframe, limit=limit, startTime=start, endTime=end))
        
        if resp.empty or len(resp.columns) < 6:
            return None

        resp = resp.iloc[:, :6]
        resp.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
        resp = resp.set_index('Time')
        resp.index = pd.to_datetime(resp.index, unit='ms')
        resp = resp.astype(float)
        return resp
    
    except ClientError as error:
        print(f"Found error. status: {error.status_code}, error code: {error.error_code}, error message: {error.error_message}")
        
    return None


# Fetch klines data from Binance (datetime interval)
def klines_datetime(symbol, timeframe=trading_setup.TRADE_TIME, interval_days=30, dt_end=None):
    ms_interval = interval_days * 24 * 3600 * 1000
    limit = ms_interval / (intervals[timeframe] * 60 * 1000)
    steps = limit / 1500
    first_limit = int(steps)
    last_step = steps - int(steps)
    last_limit = round(1500 * last_step)
    if dt_end:
        current_time = int(dt_end.timestamp() * 1000)
    else:
        current_time = int(time.time() * 1000)
    p = pd.DataFrame()
    for i in range(first_limit):
        start = int(current_time - (ms_interval - i * 1500 * intervals[timeframe] * 60 * 1000))
        end = start + 1500 * intervals[timeframe] * 60 * 1000
        res = klines(symbol, timeframe = timeframe, limit=1500, start=start, end=end)
        if res is not None:
            p = pd.concat([p, res])

    p = pd.concat([p, klines(symbol, timeframe = timeframe, limit=last_limit, end=current_time)])
    p = p.loc[~p.index.duplicated(keep='first')]
    return p


# Get tickers list (pair with USDT)
def get_tickers_usdt():
    try:
        tickers = []
        resp = client.ticker_price()
        for elem in resp:
            if 'USDT' in elem['symbol']:
                tickers.append(elem['symbol'])
        return tickers
    except ClientError as error:
        print(f"Found error. status: {error.status_code}, error code: {error.error_code}, error message: {error.error_message}")


# Set leverage for the needed symbol
def set_leverage(symbol, level):
    try:
        response = client.change_leverage(symbol=symbol, leverage=level, recvWindow=6000)
        print(response)

    except ClientError as error:
        logger.error("[{}] Found error. status: {}, error code: {}, error message: {}".format(symbol, error.status_code, error.error_code, error.error_message))


# Set margin type for the needed symbol
def set_mode(symbol, type):
    try:
        response = client.change_margin_type(symbol=symbol, marginType=type, recvWindow=6000)
        print(response)

    except ClientError as error:
        if error.error_code != -4046: # error code: -4046, error message: No need to change margin type
            logger.error("[{}] Found error. status: {}, error code: {}, error message: {}".format(symbol, error.status_code, error.error_code, error.error_message))


# Startup trade config
def startup_trade(symbol, type, leverage):
    set_mode(symbol, type)
    time.sleep(1)
    set_leverage(symbol, leverage)
    time.sleep(1)


# Price precision
def get_price_precision(symbol):
    try:
        resp = client.exchange_info()['symbols']
        for elem in resp:
            if elem['symbol'] == symbol:
                return elem['pricePrecision']

    except ClientError as error:
        logger.error("[{}] Found error. status: {}, error code: {}, error message: {}".format(symbol, error.status_code, error.error_code, error.error_message))


# Amount precision
def get_qty_precision(symbol):
    try:
        resp = client.exchange_info()['symbols']
        for elem in resp:
            if elem['symbol'] == symbol:
                return elem['quantityPrecision']

    except ClientError as error:
        logger.error("[{}] Found error. status: {}, error code: {}, error message: {}".format(symbol, error.status_code, error.error_code, error.error_message))


# Current positions (returns the symbols list)
def get_pos():
    try:
        resp = client.get_position_risk()
        pos = []
        for elem in resp:
            if float(elem['positionAmt']) != 0:
                pos.append(elem['symbol'])
        return pos
    
    except ClientError as error:
        logger.error("Found error. status: {}, error code: {}, error message: {}".format(error.status_code, error.error_code, error.error_message))


# Current position size (<0: short, >0: long)
def get_pos_size(symbol):
    try:
        position = client.get_position_risk(symbol=symbol)
        if position:
            return float(position[0]['positionAmt'])
        
    except ClientError as error:
        logger.error("[{}] Found error. status: {}, error code: {}, error message: {}".format(symbol, error.status_code, error.error_code, error.error_message))


# Close open position for the needed symbol
def close_open_position(symbol):
    try:
        position_size = get_pos_size(symbol)
        if position_size != 0:
            side = "SELL" if position_size > 0 else "BUY"
            size = abs(position_size)
            
            resp = client.new_order(symbol=symbol, side=side, type="MARKET", quantity=size, reduceOnly=True)
            print(resp)
            return resp

    except ClientError as error:
        logger.error("[{}] Found error. status: {}, error code: {}, error message: {}".format(symbol, error.status_code, error.error_code, error.error_message))


# Current orders (returns the symbols list)
def check_orders():
    try:
        response = client.get_orders(recvWindow=6000)
        sym = []
        for elem in response:
            sym.append(elem['symbol'])
        return sym
    
    except ClientError as error:
        logger.error("Found error. status: {}, error code: {}, error message: {}".format(error.status_code, error.error_code, error.error_message))


# Close open orders for the needed symbol. If one stop order is executed and another one is still there
def close_open_orders(symbol):
    try:
        response = client.cancel_open_orders(symbol=symbol, recvWindow=6000)
        print(response)
    except ClientError as error:
        logger.error("[{}] Found error. status: {}, error code: {}, error message: {}".format(symbol, error.status_code, error.error_code, error.error_message))


# Getting your futures balance in USDT
def get_balance_usdt():
    try:
        response = client.balance(recvWindow=6000)
        for elem in response:
            if elem['asset'] == 'USDT':
                return float(elem['balance'])

    except ClientError as error:
        logger.error("Found error. status: {}, error code: {}, error message: {}".format(error.status_code, error.error_code, error.error_message))


# Getting your futures unrealized profit in USDT
def get_unrealized_profit():
    try:
        response = client.account(recvWindow=6000)
        return float(response['totalUnrealizedProfit'])
    except ClientError as error:
        logger.error("Found error. status: {}, error code: {}, error message: {}".format(error.status_code, error.error_code, error.error_message))
        return 0


# Open new order
def open_order(symbol, side, volume=trading_setup.VOLUME, sl=trading_setup.SL, tp=trading_setup.TP, trade_time=trading_setup.TRADE_TIME, type='LIMIT'):
    qty_precision = get_qty_precision(symbol)
    price_precision = get_price_precision(symbol)

    for attempt in range(5):
        kl = klines(symbol, trade_time, 1)
        now_utc = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=3)
        now_utc_1 = now_utc - timedelta(minutes=1)
        if now_utc == kl.index[-1] or now_utc_1 == kl.index[-1]:
            price = float(kl['Open'].iloc[-1])
            qty = round(volume/price, qty_precision)
            break
    if attempt == 4:
        logger.error(f'[{symbol}] Number of attempts exceeded: Wrong candle - {now_utc} UTC')
        return 'error'
    
    if side == 'buy':
        try:
            if type == 'MARKET':
                resp1 = client.new_order(symbol=symbol, side='BUY', type='MARKET', quantity=qty)
            else:
                resp1 = client.new_order(symbol=symbol, side='BUY', type='LIMIT', quantity=qty, timeInForce='GTC', price="{:.{}f}".format(price, price_precision))
            print(resp1)
            time.sleep(0.5)
            sl_price = round(price - price*sl, price_precision)
            resp2 = client.new_order(symbol=symbol, side='SELL', type='STOP_MARKET', closePosition='true', timeInForce='GTC', stopPrice="{:.{}f}".format(sl_price, price_precision))
            print(resp2)
            time.sleep(0.5)
            tp_price = round(price + price * tp, price_precision)
            resp3 = client.new_order(symbol=symbol, side='SELL', type='TAKE_PROFIT_MARKET', closePosition='true', timeInForce='GTC', stopPrice="{:.{}f}".format(tp_price, price_precision))
            print(resp3)
        except ClientError as error:
            logger.error("[{}] Found error. status: {}, error code: {}, error message: {}".format(symbol, error.status_code, error.error_code, error.error_message))
            return 'error'
    
    if side == 'sell':
        try:
            if type == 'MARKET':
                resp1 = client.new_order(symbol=symbol, side='SELL', type='MARKET', quantity=qty)
            else:
                resp1 = client.new_order(symbol=symbol, side='SELL', type='LIMIT', quantity=qty, timeInForce='GTC', price="{:.{}f}".format(price, price_precision))
            print(resp1)
            time.sleep(0.5)
            sl_price = round(price + price*sl, price_precision)
            resp2 = client.new_order(symbol=symbol, side='BUY', type='STOP_MARKET', closePosition='true', timeInForce='GTC', stopPrice="{:.{}f}".format(sl_price, price_precision))
            print(resp2)
            time.sleep(0.5)
            tp_price = round(price - price * tp, price_precision)
            resp3 = client.new_order(symbol=symbol, side='BUY', type='TAKE_PROFIT_MARKET', closePosition='true', timeInForce='GTC', stopPrice="{:.{}f}".format(tp_price, price_precision))
            print(resp3)
            
        except ClientError as error:
            logger.error("[{}] Found error. status: {}, error code: {}, error message: {}".format(symbol, error.status_code, error.error_code, error.error_message))
            return 'error'

    # Logging the order
    mesg = f"{side}\t{qty}\t{symbol}:\tprice {price}\t|\tsl {sl_price} - tp {tp_price}"
    logger.warning(mesg)

    return resp3['clientOrderId']