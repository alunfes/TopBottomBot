

from Settings import Settings

import asyncio
import pandas as pd

class TargetSymbolsData:
    @classmethod
    def initialize(cls):
        cls.target_df = pd.DataFrame()
        cls.target_ohlcv_df = {}
        cls.common_last_dt = None
    

    @classmethod
    def get_latest_price(cls, key):
        return float(cls.tar[key]['close'].iloc[-1])



if __name__ == '__main__':
    Settings.initialize()
    TargetSymbolsData.initialize(1000000.0)

