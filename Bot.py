import time
import asyncio

from AccountData import AccountData
from Strategy import Strategy
from Settings import Settings
from Flags import Flags
from TargetSymbolsData import TargetSymbolsData
from TargetSymbolsDataInjector import TargetSymbolsDataInjector


class Bot:
    def __init__(self, ccxt_api):
        self.flg_main_process = True
        self.crp = ccxt_api
        self.tsdj = TargetSymbolsDataInjector(Settings.target_24h_vol_kijun)
        tsdi = TargetSymbolsDataInjector(self.crp, 1000000.0)
        tsdi.inject_target_data()
        tsdi.inject_ohlcv_data(14)

    

    async def start_bot(self):
        while Flags.get_system_flag():
            #download market data
            #get action from startegy
            #take action
            #take log
            #send message
            asyncio.sleep(60)

    