# STARTUP
from keys import api, secret
import trading_setup
import binance_futures
from binance.um_futures import UMFutures
import ta
import time
from tqdm import tqdm
import pandas as pd
from binance.error import ClientError
import logger_bot, logging
from datetime import datetime, timedelta
import concurrent.futures

client = UMFutures(key=api, secret=secret)


# BOT STARTUP
ENABLE_TRADE = False
SYMBOLS = trading_setup.SYMBOLS
SETUP = f"interval {trading_setup.TRADE_TIME}, size {trading_setup.VOLUME:.1f} USDT, leverage {trading_setup.LEVERAGE}, tp/sl ({trading_setup.TP}/{trading_setup.SL})"
logger = logger_bot.get_logger()
logger.warning('Starting bot...')
logger.warning(SETUP)
logger.warning(SYMBOLS)


# Get signals
def get_signal(symbol):
    try:
        for attempt in range(5):
            kl = binance_futures.klines(symbol, trading_setup.TRADE_TIME, 250)
            
            now_utc = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=3)
            if now_utc == kl.index[-1]:
                kl = kl.iloc[:-1]
                close_prices = kl.Close

                roc = ta.momentum.ROCIndicator(close_prices, window=trading_setup.ROC_PERIOD).roc()
                th = kl.Volume[-(trading_setup.VOL_PERIOD+1):-1].mean() * trading_setup.VOL_TH

                if roc.iloc[-1] < -trading_setup.ROC_TH and kl.Volume.iloc[-1] > th:
                    return symbol
                else:
                    return None
            
            time.sleep(1)
        logger.error(f'{symbol} - Number of attempts exceeded: Wrong candle - {now_utc} UTC')

    except Exception as err:
        print(symbol, err)
    
    return None


# Main LOOP ###########################################################################################################
interval = binance_futures.intervals[trading_setup.TRADE_TIME]
resp = ''
pos = []
ord = []

while True:
    try:
        # Performs analysis every {TRADE_TIME} minutes
        now = datetime.now()
        if now.minute % interval == 0:
            start_time = time.time()
            now = now.replace(second=0, microsecond=0)
            next_run_time = now + timedelta(minutes=interval)

            # Get balance to check if the connection is good, or you have all the needed permissions
            balance = binance_futures.get_balance_usdt()
            unrealized = binance_futures.get_unrealized_profit()
            time.sleep(1)

            if balance == None:
                logger.error('Cant connect to API. Check IP, restrictions or wait some time')
            
            elif balance < trading_setup.CRITICAL_BALANCE:
                logger.error(f"CRITICAL BALANCE: {balance} USDT")
            
            # Bot working...
            else:
                logger.info(f'Your balance is: {balance} USDT')
                logger.info(f'Unrealized profit: {unrealized} USDT')

                # Getting position list
                pos = binance_futures.get_pos()
                if pos:
                    logger.info(f'You have {len(pos)} opened positions: {pos}')
                
                # Getting order list
                ord = binance_futures.check_orders()

                # Removing stop orders for closed positions
                for elem in ord:
                    if not elem in pos:
                        binance_futures.close_open_orders(elem)
                        ord = binance_futures.check_orders()

                # Checking for signals and trading
                count = len(pos)
                if count < trading_setup.MAX_POSITIONS:
                    symbols = [item for item in SYMBOLS if item not in pos]
                    symbols_down = []
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        results = list(tqdm(executor.map(get_signal, symbols), total=len(symbols)))
                    symbols_down = [symbol for symbol in results if symbol]

                    for symbol in symbols_down:
                        count += 1
                        
                        if ENABLE_TRADE == True:
                            resp = binance_futures.open_order(symbol=symbol, side='sell', volume=trading_setup.VOLUME)
                        else:
                            print(f'Signal (sell) for {symbol}')

                        if resp == 'error':
                            binance_futures.close_open_position(symbol)

                        if count >= trading_setup.MAX_POSITIONS:
                            break


            # Next time to run
            end_time = time.time()
            execution_time = end_time - start_time
            
            sleep_duration = (next_run_time - datetime.now()).total_seconds()
            print(f"The analysis took {execution_time:.2f} seconds to run. Waiting {sleep_duration:.2f} seconds to the next...")
            time.sleep(sleep_duration + 1)

        else:
            time.sleep(10)


    except Exception as e:
        logger.error(f"Error: {e}")

    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt")
        exit()