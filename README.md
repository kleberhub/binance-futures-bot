# Binance Futures Trading Bot
This is a short-selling bot that uses momentum ROC and volume spikes to decide when to enter a trade.

## ▶️ How to use
1. Installing the requirements: `pip install -r requirements.txt`
2. Add *API key* and *Secret key* to `keys.py`. You can get it from https://www.binance.com/en/my/settings/api-management
3. Run the script `backtest_strategy.ipynb`, it will select the best symbols to trade based on a 30-day backtest
4. Take the result from the `symbols_to_trade` variable and update it in the `trading_setup.py` file
5. In the bot script `run_bot.py`, change `ENABLE_TRADE = False` to `True`
6. Run the bot script `run_bot.py`


## 📈 How it works - Strategy
1. Direction: short (sell)
2. Indicators: volume and ROC (rate of change)
3. Entry Condition: no open position, and momentum is strongly negative, and volume spike is present
4. The bot always wakes up every `TRADE_TIME`, analyzes all the `SYMBOLS` for entry conditions and makes the trades fully automatically


## 📌 Tips
1. All of the `trading_setup.py` parameters have been extensively tested and have shown the best performance, but you're free to run other tests (`backtest_strategy.ipynb` is for this!)
2. You can update the list of `SYMBOLS` every week *(How to use - steps 3 and 4)*
3. The clock must be synchronized to a NTP server very frequently to avoid problems with communication to the exchange


## ⚠️ Disclaimer
**Legal Notice:**
- This project is provided for educational purposes only.
- The author assumes no responsibility for any losses, damages, or consequences resulting from the use of this code.
- Trading cryptocurrencies involves high financial risk and may result in the total loss of your invested capital.
- Use this bot at your own risk, and always test it in a demo environment (testnet) before considering any real trading.

**Additionally:**
- This code is not financial advice or an investment recommendation.
- You are solely responsible for configuring, running, and securing your Binance account and API keys.
- The bot’s performance depends on external factors such as internet connectivity, the stability of the exchange's API, and market behavior, which are beyond the author's control.
- If you do not fully understand the risks involved, do not use this bot.