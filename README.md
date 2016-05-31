# ESKIMOTRON
Eskimotron - A little trading app originally designed for Monero (XMR). Works with Poloniex and Bittrex and supports other currencies.

#### Configuring default.cfg
1. Open the file called default.cfg
2. Enter your API details for Poloniex and/or Bittrex.
3. Save default.cfg

#### Configuring trading.cfg
1. Open the file called trading.cfg
2. Enter the trading pairs you wish to use. (e.g XMR/BTC)
3. Save trading.cfg

#### Running
1. Simply compile and run Eskimotron.py from a Python 2.7 IDE.

#### Trading

Eskimotron works as a time trader / threshold trader combination. When trading anything it will always ask you for the following four variables:-

1. Amount you wish to trade.
2. Trading threshold price.
3. Duration in hours of total program.
4. Frequency of trade attempts in seconds.

##### Time / Threshold Combination

Let's say you wanted to buy 5 BTC's worth of XMR on Poloniex, but only at a purchase price of under 0.0021. Also, the total buying program should last 6 hours (pending threshold satisfaction) with each buy attempt occuring every 120 seconds. You would perform the following steps:-

1. Select the Poloniex menu.
2. Select the XMR/BTC menu.
3. Select the Buy XMR option.
4. Enter 5 BTC.
5. Enter 0.0021 as the buy threshold.
6. Enter 6 for the duration (in hours).
7. Enter 120 for the frequency (in seconds).
8. Hit (Y) or (y) to start the program.

##### Threshold Only

For threshold only trades, enter the trading amount and threshold price as normal, but enter 0 for duration, and 0 for frequency.

##### Time Only

For time only trades, follow the same steps but simply widen the thresholds to make any trades a practical certainty. For example, suppose you wanted to sell on Time Only you would might set the threshold to 99999. 

 
That's it! Hope you have fun with it. 

#### DISCLAIMER: I should probably add that I only starting learning Python three weeks ago so don't blame if you lose everything. Operate at own risk.





 
