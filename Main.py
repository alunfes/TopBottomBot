
from Settings import Settings
from TargetSymbolsData import TargetSymbolsData
from TargetSymbolsDataInjector import TargetSymbolsDataInjector
from Strategy import Strategy
from AccountData import AccountData
from AccountUpdater import AccountUpdater
from Bot import Bot
from Flags import Flags
from CCXTRestApi import CCXTRestApi

import pandas as pd
import asyncio

class Main:
    def __init__(self):
        Flags.initialize()
        Settings.initialize()
        TargetSymbolsData.initialize()
        tsdi = TargetSymbolsDataInjector(1000000.0)
        
        #tsdi.inject_target_data()
        #tsdi.inject_ohlcv_data(14)
        tsdi.read_target_tickers()
        tsdi.read_all_ohlcv()
        strategy = Strategy()
        strategy.calc_change_ratio()
        strategy.detect_top_bottom_targets()
        #pd.DataFrame(strategy.top_targets).to_csv('./Data/top_targets.csv', index=False)
        #pd.DataFrame(strategy.bottom_targets).to_csv('./Data/bottom_targets.csv', index=False)
        strategy.calc_lot()
    
    async def main():
        ccxt_api = CCXTRestApi()
        account = AccountUpdater(ccxt_api)
        market_data = MarketData()
        strategy = Strategy()
        communication = Communication()
        bot = Bot()

        await asyncio.gather(
            account.start_update(),
            market_data.start_update(),
            strategy.start(),
            communication.start(),
            bot.start_bot()
        )
        


if __name__ == '__main__':
    m =  Main()