from TargetSymbolsData import TargetSymbolsData
from CCXTRestApi import CCXTRestApi
from Settings import Settings

import asyncio
import pandas as pd
import time
import math


class TargetSymbolsDataInjector:
    def __init__(self, ccxt_api:CCXTRestApi, vol_kijun_24h:float):
        TargetSymbolsData.initialize()
        self.loop = asyncio.new_event_loop()
        self.vol_kijun_24h = vol_kijun_24h
        self.crp =ccxt_api
    

    async def inject_ohlcv_data(self, data_days:int):
        print('Downloading 4h ohlc...')
        ohlc_min = 240
        since = (int(time.time()) - 60 * 1440 * data_days) * 1000
        #cex_df = cex_df[cex_df['ex_name']!='binance'] #for test
        cex_df = TargetSymbolsData.target_df.copy()
        cex_df = cex_df.sample(frac=1, random_state=42)
        #generate ex-symbol pairs for cex
        ex_symbol_pairs = []
        ex_names = list(cex_df.ex_name)
        symbols = list(cex_df.symbol)
        for i in range(len(symbols)):
            ex_symbol_pairs.append({'ex_name':ex_names[i], 'symbol':symbols[i]})
        #download for all cex symbols 
        i = 0
        num_cycle_downloads = 5
        #ex_symbol_pairs = ex_symbol_pairs[0:15] #for test
        all_download_done = 0
        while True:
            target = ex_symbol_pairs[i:i+num_cycle_downloads]
            await self.crp.get_multiple_ohlc(target, ohlc_min, since)
            all_download_done += 1
            if i + num_cycle_downloads > len(ex_symbol_pairs):
                break
            i += num_cycle_downloads
            print('Progress:', all_download_done,'/',math.ceil(len(ex_symbol_pairs) / num_cycle_downloads))
        self.read_all_ohlcv()
        print('Completed ohlcv download.')
        

    def read_all_ohlcv(self):
        cex_df = TargetSymbolsData.target_df.copy()
        for i in range(len(cex_df)):
            file_name = cex_df['ex_name'].iloc[i]+'-'+(cex_df['id'].iloc[i] if cex_df['ex_name'].iloc[i] != 'okx' else cex_df['symbol'].iloc[i].split(':')[0].replace('/',''))
            TargetSymbolsData.target_ohlcv_df[file_name] = pd.read_csv('./Data/ohlcv/'+file_name+'.csv')
        target_ohlcv_df = TargetSymbolsData.target_ohlcv_df.copy()
        TargetSymbolsData.target_ohlcv_df = self.__check_dt(target_ohlcv_df)
        print('Completed ohlcv download.')

    '''
    start, endのdtを合わせる。最後があってれば最初の日付が新しいものでも変化率は計算できるので使わなくてもいいかも。
    '''
    def __check_dt(self, target_ohlcv_df):
        # 与えられたdict内のDataFrameから、dt列を抽出してリストに格納
        first_dt_list = [df['dt'].iloc[0] for df in target_ohlcv_df.values()]
        last_dt_list = [df['dt'].iloc[-1] for df in target_ohlcv_df.values()]
        # dt列をpandas.Timestamp型に変換
        first_dt_list = [pd.to_datetime(dt) for dt in first_dt_list]
        last_dt_list = [pd.to_datetime(dt) for dt in last_dt_list]
        # 最も多いdtを取得
        most_common_first_df = max(set(first_dt_list), key=first_dt_list.count)
        most_common_last_df = max(set(last_dt_list), key=last_dt_list.count)
        TargetSymbolsData.common_last_dt = most_common_last_df
        # dict内のDataFrameをループし、dt列を最も多いdtでフィルタリング
        new_target_ohlcv_df = {}  # create a new dictionary to store the DataFrames that meet the conditions
        for key, df in target_ohlcv_df.items():
            dtlist = pd.to_datetime(df['dt'])
            if dtlist.iloc[0] != most_common_first_df:
                print('First dt in ', key, ' is not matched !', ': ',dtlist.iloc[0])
                continue  # skip this DataFrame
            if dtlist.iloc[-1] != most_common_last_df:
                print('Last dt in ', key, ' is not matched !', ': ',dtlist.iloc[-1])
                continue  # skip this DataFrame
            # if the DataFrame meets the conditions, add it to the new dictionary
            new_target_ohlcv_df[key] = df
        return new_target_ohlcv_df
        


    async def inject_target_data(self):
        print('Generating target ticker list...')
        df_ticker = []
        for ex in Settings.exchanges:
            if ex == 'binance':
                res = await self.__get_binance_target()
                df_ticker.append(res)
            elif ex == 'bybit':
                res = await self.__get_bybit_target()
                df_ticker.append(res)
            elif ex == 'okx':
                res = await self.__get_okx_target()
                df_ticker.append(res)
        target_df = pd.concat(df_ticker, axis=0).reset_index(drop=True)
        target_df = self.__remove_duplication(target_df)
        target_df.to_csv('./Data/target_df.csv', index=False)
        print('Completed target ticker list generation.')
        self.read_target_tickers()
        

    def read_target_tickers(self):
        TargetSymbolsData.target_df = pd.read_csv('./Data/target_df.csv', index_col=None)
        print('Completed read all ohlcv.')


    '''
    removed duplicated symbols and prioritize to use binance to optimize money efficiency
    '''
    def __remove_duplication(self, target_df):
        # 優先したい ex_name
        preferred_ex_name = 'binance'
        # 優先したい ex_name を最上位に持ってくるためのカラムを追加
        target_df['priority'] = (target_df['ex_name'] == preferred_ex_name).astype(int)
        # 'base' と 'quote' の組み合わせに対して、priority が高いものが優先されるようにソート
        df_sorted = target_df.sort_values(by=['base', 'quote', 'priority'], ascending=[True, True, False])
        # 重複を削除
        df_deduplicated = df_sorted.drop_duplicates(subset=['base', 'quote'], keep='first')
        # priority カラムを削除
        df_deduplicated = df_deduplicated.drop(columns=['priority'])
        return df_deduplicated



    async def __get_binance_target(self):
        tickers = await self.crp.get_tickers('binance')
        ticker_vols = await self.crp.get_tickers_24h_binance()
        #ticker_vols.to_csv('./binance_vol.csv')
        target = []
        sell_ok = []
        vols = []
        #check sell_ok and target(fitler by vol)
        for index, row in tickers.iterrows():
            if row['active'] == True and row['quoteId'] == 'USDT' and row['type'] == 'swap' and row['contract'] == True and 'USD' not in row['baseId']:
                sell_ok.append(True)
                vol_data = ticker_vols[ticker_vols['symbol'] == row['id']]
                vol = float(vol_data['weightedAvgPrice'].iloc[0]) * float(vol_data['volume'].iloc[0]) + float(vol_data['quoteVolume'].iloc[0])
                vols.append(vol)
                if vol >= self.vol_kijun_24h:
                    target.append(True)
                else:
                    target.append(False)
            else:
                sell_ok.append(False)
                target.append(False)
                vols.append(0) #targetじゃないので０を適当に入れる。
        tickers['sell_ok'] = sell_ok
        tickers['target'] = target
        tickers['volume'] = vols
        tickers['ex_name'] = ['binance'] * len(tickers)
        tickers = tickers[tickers['target']==True]
        selected_columns = ['ex_name', 'id', 'symbol', 'base', 'quote', 'type', 'taker', 'maker', 'sell_ok', 'target', 'volume']
        tickers = tickers[selected_columns]
        #tickers.to_csv('./binance_tickers.csv')
        return tickers


    async def __get_bybit_target(self):
        tickers = await self.crp.get_tickers('bybit')
        ticker_vols = await self.crp.get_tickers_24h_bybit()
        #ticker_vols.to_csv('./bybit_vol.csv')
        target = []
        sell_ok = []
        vols = []
        for index, row in tickers.iterrows():
            if row['active'] == True and row['quoteId'] == 'USDT' and row['type'] == 'swap' and 'USD' not in row['baseId']:
                sell_ok.append(True)
                vol_data = ticker_vols[ticker_vols['symbol'] == row['id']]
                vol = 0.5 * (float(vol_data['highPrice24h'].iloc[0]) + float(vol_data['lowPrice24h'].iloc[0])) * float(vol_data['volume24h'].iloc[0])
                vols.append(vol)
                if vol  >= self.vol_kijun_24h:
                    target.append(True)
                else:
                    target.append(False)
            else:
                sell_ok.append(False)
                target.append(False)
                vols.append(0)
        tickers['sell_ok'] = sell_ok
        tickers['target'] = target
        tickers['volume'] = vols
        tickers['ex_name'] = ['bybit'] * len(tickers)
        tickers = tickers[tickers['target']==True]
        selected_columns = ['ex_name', 'id', 'symbol', 'base', 'quote', 'type', 'taker', 'maker', 'sell_ok', 'target', 'volume']
        tickers = tickers[selected_columns]
        #tickers.to_csv('./bybit_tickers.csv')
        return tickers


    async def __get_okx_target(self):
        tickers = await self.crp.get_tickers('okx')
        ticker_vols = await self.crp.get_tickers_24h_okx()
        #ticker_vols.to_csv('./okx_vol.csv')
        target = []
        sell_ok = []
        vols = []
        for index, row in tickers.iterrows():
            if row['active'] == True and row['quoteId'] == 'USDT' and row['type'] == 'swap' and 'USD' not in row['baseId']:
                sell_ok.append(True)
                vol_data = ticker_vols[ticker_vols['symbol'] == row['symbol'].split(':')[0]]
                vol = float(vol_data['baseVolume'].iloc[0]) * float(vol_data['vwap'].iloc[0])  + float(vol_data['quoteVolume'].iloc[0])
                vols.append(vol)
                if vol >= self.vol_kijun_24h:
                    target.append(True)
                else:
                    target.append(False)
            else:
                sell_ok.append(False)
                target.append(False)
                vols.append(0)
        tickers['sell_ok'] = sell_ok
        tickers['target'] = target
        tickers['volume'] = vols
        tickers['ex_name'] = ['okx'] * len(tickers)
        tickers = tickers[tickers['target']==True]
        selected_columns = ['ex_name', 'id', 'symbol', 'base', 'quote', 'type', 'taker', 'maker', 'sell_ok', 'target', 'volume']
        tickers = tickers[selected_columns]
        #tickers.to_csv('./okx_tickers.csv')
        return tickers


    

if __name__ == '__main__':
    Settings.initialize()
    crp = CCXTRestApi()
    TargetSymbolsData.initialize()
    tsdi = TargetSymbolsDataInjector(crp, 1000000.0)
    tsdi.inject_target_data()
    tsdi.inject_ohlcv_data(14)
    #tsdi.read_target_tickers()
    #tsdi.read_all_ohlcv()





