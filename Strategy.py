from TargetSymbolsData import TargetSymbolsData
from Settings import Settings
from AccountData import Account
from CCXTRestApiParser import CCXTRestApiWrapper

import pandas as pd 
import asyncio

'''
*単純にindexhじゃなくて一致するdt（もしくはそれより後のdtでもok）で計算するようにしないといけない。
・対象全銘柄の最終日時があっていることを確認する。
・任意の直近期間の変化率を計算して、top/bottomを算出。それぞれに対しての売買金額・lotを計算。
'''
class Strategy:
    def __init__(self):
        self.price_change_ratio = {}
        self.top_targets = {}
        self.bottom_targets = {}
        self.top_targets_df = pd.DataFrame()
        self.bottom_targets_df = pd.DataFrame()
        self.loop = asyncio.new_event_loop()
        

    def calc_change_ratio(self):
        target_ohlcv_df = TargetSymbolsData.target_ohlcv_df.copy()
        for k in target_ohlcv_df:
            kijun_index = min(Settings.before_kijun_period, len(target_ohlcv_df[k]['close']))
            cr = 100.0 * (target_ohlcv_df[k]['close'].iloc[-1] - target_ohlcv_df[k]['close'].iloc[-kijun_index]) / target_ohlcv_df[k]['close'].iloc[-kijun_index]
            self.price_change_ratio[k] = float(cr)
    
    def detect_top_bottom_targets(self):
        sorted_d = sorted(self.price_change_ratio.items(), key=lambda x: x[1])
        self.top_targets = sorted_d[-Settings.num_top_bottom_targets:]
        self.bottom_targets = sorted_d[:Settings.num_top_bottom_targets]
        self.top_targets_df = pd.DataFrame({'keys':[x[0] for x in self.top_targets], 'ex_name':[x[0].split('-')[0] for x in self.top_targets], 'change_ratio':[x[1] for x in self.top_targets]})
        self.bottom_targets_df = pd.DataFrame({'keys':[x[0] for x in self.bottom_targets], 'ex_name':[x[0].split('-')[0] for x in self.bottom_targets], 'change_ratio':[x[1] for x in self.bottom_targets]})
    

    def calc_lot(self):
        num_targets_ex = {}
        for ex in Settings.exchanges:
            num_targets_ex[ex] = 0
            for k in self.bottom_targets:
                if k[0].split('-')[0] == ex:
                    num_targets_ex[ex] += 1
            for k in self.top_targets:
                if k[0].split('-')[0] == ex:
                    num_targets_ex[ex] += 1
        print('num targets exchanges:')
        print(num_targets_ex)
        self.top_targets_df['allocation_percent'] = [round(1.0 / (len(self.top_targets_df) + len(self.bottom_targets_df)), 6)] * len(self.top_targets_df)
        self.top_targets_df['allocation_amount'] = [round(0.5 * Account.total_cash / (len(self.top_targets_df) + len(self.bottom_targets_df)), 2)] * len(self.top_targets_df)
        self.bottom_targets_df['allocation_percent'] = [round(1.0 / (len(self.top_targets_df) + len(self.bottom_targets_df)), 6)] * len(self.bottom_targets_df)
        self.bottom_targets_df['allocation_amount'] = [round(0.5 * Account.total_cash / (len(self.top_targets_df) + len(self.bottom_targets_df)), 2)] * len(self.bottom_targets_df)
        top_lots = []
        top_prices = []
        for i in range(len(self.top_targets_df)):
            symbol = self.top_targets_df.iloc[i]['keys'].split('-')[1] if self.top_targets_df.iloc[i]['ex_name'] != 'okx' else self.top_targets_df.iloc[i]['keys'].split('-')[1].replace('USDT','') + '-USDT-SWAP'
            res =  self.loop.run_until_complete(CCXTRestApiWrapper.crp.fetch_target_price(self.top_targets_df.iloc[i]['ex_name'], symbol))
            top_prices.append(float(res['last'].iloc[0]))
            top_lots.append(self.top_targets_df['allocation_amount'].iloc[i] / float(res['last'].iloc[0]))
        self.top_targets_df['allocation_lot'] = top_lots
        self.top_targets_df['allocation_price'] = top_prices
        bottom_lots = []
        bottom_prices = []
        for i in range(len(self.bottom_targets_df)):
            symbol = self.bottom_targets_df.iloc[i]['keys'].split('-')[1] if self.bottom_targets_df.iloc[i]['ex_name'] != 'okx' else self.bottom_targets_df.iloc[i]['keys'].split('-')[1].replace('USDT','') + '-USDT-SWAP'
            res =  self.loop.run_until_complete(CCXTRestApiWrapper.crp.fetch_target_price(self.bottom_targets_df.iloc[i]['ex_name'], symbol))
            bottom_prices.append(float(res['last'].iloc[0]))
            bottom_lots.append(self.bottom_targets_df['allocation_amount'].iloc[i] / float(res['last'].iloc[0]))
        self.bottom_targets_df['allocation_lot'] = bottom_lots
        self.bottom_targets_df['allocation_price'] = bottom_prices
        self.top_targets_df.to_csv('./top_targets_df.csv', index=False)
        self.bottom_targets_df.to_csv('./bottom_targets_df.csv', index=False)

        
            






