from TargetSymbolsData import TargetSymbolsData
from TargetSymbolsDataInjector import TargetSymbolsDataInjector
from Settings import Settings
from AccountData import AccountData
from CCXTRestApi import CCXTRestApi
from ActionData import ActionData
from DisplayMessage import DisplayMessage

import pandas as pd 
import asyncio
import math
import numpy as np

'''
*単純にindexhじゃなくて一致するdt（もしくはそれより後のdtでもok）で計算するようにしないといけない。
・対象全銘柄の最終日時があっていることを確認する。
・任意の直近期間の変化率を計算して、top/bottomを算出。それぞれに対しての売買金額・lotを計算。

基本戦略：
・topを売ってbottomを買う。2週間後に決済。
・個別銘柄一定以上の収益になったら利確・損切り
・その他、銘柄毎に4時間足でトレンド継続している間はエントリーしないなど。


process:
・最初は全ての銘柄のデータをダウンロードして変化率を計算して対象銘柄と取引lotを決める。
・その後は、pf全体の収益率でpt or lc or no actionを判断する。
・entryはlimit orderで出すが、約定しないでbid/askが不利な方向に変化したらmarket orderにする。
・個別銘柄でpt, lcの設定がある場合はそれに応じてactionを取る。
・一旦全部closeしたら次は同じように全銘柄のデータ取得して対象選定から実行（つまりTargetSymbolDataInjectはaccount holdingとorderがない時に実施すればいい。）

引数：
・

返り値：
・portfolioと取るべきアクション

'''
class Strategy:
    def __init__(self, ccxt_api:CCXTRestApi):
        self.crp = ccxt_api
        self.pf_status = 'None' #None, Entry, Hold, Exit
        self.test_qty_denominator = 0.1
        self.price_change_ratio = {}
        self.top_targets = {}
        self.bottom_targets = {}
        self.top_targets_df = pd.DataFrame()
        self.bottom_targets_df = pd.DataFrame()
        self.tsdi = TargetSymbolsDataInjector(self.crp, 1000000.0)
        
    

    async def get_actions(self, pf_pt_ratio, pf_lc_ratio) -> ActionData:
        holding_df = AccountData.get_holding_df()
        order_df = AccountData.get_order_df()
        ad = ActionData() 
        if len(holding_df) == 0 and len(order_df) == 0: #no position / order, entry for initial limit orders for all top/bottom targets
            await self.tsdi.inject_target_data()
            await self.tsdi.inject_ohlcv_data(14)
            self.calc_change_ratio()
            self.detect_top_bottom_targets()
            await self.calc_lot()
            for index, top in self.top_targets_df.iterrows():
                symbol = top['key'].split('-')[-1] if top['ex_name'] != 'okx' else top['key'].split('-')[-1].replace('USDT','')+'-USDT-SWAP'
                base = top['key'].split('-')[-1].replace('USDT','')
                book = await self.crp.fetch_order_book(top['ex_name'], symbol)
                ad.add_action(action='sell', order_id='', ex_name=top['ex_name'], symbol=symbol, base_asset=base, quote_asset='USDT', order_type='limit', price=float(book['asks'][0][0]), qty=top['allocation_lot'])
            for index, bottom in self.bottom_targets_df.iterrows():
                symbol = bottom['key'].split('-')[-1] if bottom['ex_name'] != 'okx' else bottom['key'].split('-')[-1].replace('USDT','')+'-USDT-SWAP'
                base = bottom['key'].split('-')[-1].replace('USDT','')
                book = await self.crp.fetch_order_book(bottom['ex_name'], symbol)
                ad.add_action(action='buy', order_id='', ex_name=top['ex_name'], symbol=symbol, base_asset=base, quote_asset='USDT', order_type='limit', price=float(book['bids'][0][0]), qty=bottom['allocation_lot'])
            self.pf_status = 'Entry'
        elif self.pf_status == 'Entry' or self.pf_status == 'Hold': #entry in-progress or holding status
            pnl_ratio = 0.0 if AccountData.get_total_amount() > 0 else AccountData.get_total_pnl() / AccountData.get_total_amount()
            if pnl_ratio >= pf_pt_ratio: #take profit
                self.pf_status = 'Exit'
                ad = self.__cancel_all(ad)
                for index, holding in holding_df.iterrows():
                    symbol = holding['symbol'] if holding['ex_name'] != 'okx' else holding['base_asset'] + '-USDT-SWAP'
                    side = 'sell' if holding['side'] == 'long' else 'buy'
                    book = await self.crp.fetch_order_book(holding['ex_name'], symbol)
                    ad.add_action(action=side, order_id='', ex_name=holding['ex_name'],
                                  symbol=holding['symbol'], base_asset=holding['base_asset'], quote_asset=holding['quote_asset'],
                                  order_type='limit', price=float(book['bids'][0][0]) if side == 'buy' else float(book['asks'][0][0]), qty=holding['qty'])
            elif (pnl_ratio <= pf_lc_ratio): #loss cut
                self.pf_status = 'Exit'
                ad = self.__cancel_all(ad)
                for index, holding in holding_df.iterrows():
                    side = 'sell' if holding['side'] == 'long' else 'buy'
                    ad.add_action(action=side, order_id='', ex_name=holding['ex_name'],
                                  symbol=holding['symbol'], base_asset=holding['base_asset'], quote_asset=holding['quote_asset'],
                                  order_type='market', price=0, qty=holding['qty'])
            else:
                if len(order_df) > 0: #check if current bid/ask is unfavorable
                    for index, order in order_df.iterrows():
                        symbol = order['symbol'] if order['ex_name'] != 'okx' else order['base_asset']+'-USDT-SWAP'
                        res = await self.crp.fetch_target_price(order['ex_name'], symbol)
                        if (order['side'] == 'buy' and float(res['ask'].iloc[0]) > order['price']) or (order['side'] == 'sell' and float(res['bid'].iloc[0]) < order['price']): #bid/ask is unfavorable
                            ad.add_action(action='cancel', order_id=order['id'], ex_name=order['ex_name'], symbol=symbol, base_asset=order['base_asset'], quote_asset=order['quote_asset'], order_type='', price=0, qty=0)
                            ad.add_action(action=order['side'], order_id='', ex_name=order['ex_name'], symbol=symbol, base_asset=order['base_asset'], quote_asset=order['quote_asset'], order_type='market', price=0, qty=order['original_qty'] - order['executed_qty'])
        elif self.pf_status == 'Exit' and len(order_df) > 0: #monitor exit orders
            if len(holding_df) == 0: #invalid situation
                ad = self.__cancel_all()
                DisplayMessage.display_message('Strategy', 'get_actions', 'error', 
                                           [
                                               'Exit status and no holding but order remains !',
                                               'Cancelled all orders.',
                                               'Holding',
                                               holding_df,
                                               'Order',
                                               order_df
                                               ])
            else: #check if exit order price 
                for index, order in order_df.iterrows():
                    symbol = order['symbol'] if order['ex_name'] != 'okx' else order['base_asset']+'-USDT-SWAP'
                    res = await self.crp.fetch_target_price(order['ex_name'], symbol)
                    if (order['side'] == 'buy' and float(res['ask'].iloc[0]) > order['price']) or (order['side'] == 'sell' and float(res['bid'].iloc[0]) < order['price']): #bid/ask is unfavorable
                        ad.add_action(action='cancel', order_id=order['id'], ex_name=order['ex_name'], symbol=symbol, base_asset=order['base_asset'], quote_asset=order['quote_asset'], order_type='', price=0, qty=0)
                        ad.add_action(action=order['side'], order_id='', ex_name=order['ex_name'], symbol=symbol, base_asset=order['base_asset'], quote_asset=order['quote_asset'], order_type='market', price=0, qty=order['original_qty'] - order['executed_qty'])
        elif self.pf_status == 'Exit' and len(order_df) == 0 and len(holding_df) > 0: #invalid situation
            DisplayMessage.display_message('Strategy', 'get_actions', 'error', 
                                           [
                                               'Exit status but no order and holding remains!',
                                               'Holding',
                                               holding_df,
                                               'Order',
                                               order_df
                                               ])
        elif self.pf_status == 'Exit' and len(order_df) == 0 and len(holding_df) == 0: #completed all exit
            self.pf_status = 'None'
        else:#unknown situation
            DisplayMessage.display_message('Strategy', 'get_actions', 'error', 
                                           [
                                               'Unknown Situation!',
                                               'Holding',
                                               holding_df,
                                               'Order',
                                               order_df
                                               ])
        return ad


    def __cancel_all(self, ad:ActionData):
        order_df = AccountData.get_order_df()
        for index, order in order_df.iterrows():
            symbol = order['symbol'] if order['ex_name'] != 'okx' else order['base_asset']+'-USDT-SWAP'
            ad.add_action(action='cancel', order_id=order['id'], ex_name=order['ex_name'], symbol=symbol, base_asset=order['base_asset'], quote_asset=order['quote_asset'], order_type='', price=0, qty=0)
        return ad


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
        self.top_targets_df = pd.DataFrame({'key':[x[0] for x in self.top_targets], 'ex_name':[x[0].split('-')[0] for x in self.top_targets], 'change_ratio':[x[1] for x in self.top_targets]})
        self.bottom_targets_df = pd.DataFrame({'key':[x[0] for x in self.bottom_targets], 'ex_name':[x[0].split('-')[0] for x in self.bottom_targets], 'change_ratio':[x[1] for x in self.bottom_targets]})
    

    async def calc_lot(self):
        async def round_lot(ex_name, symbol, lot, price):
            '''
            min_order_amount以上かつamount_to_precisionでlotを算出して、その後実際のbidsに小数点以下のamountあるか確認してない場合は四捨五入してintにする
            '''
            if lot * price < Settings.min_order_amount: #amount should be larger than minimul amount
                lot = Settings.min_order_amount / price
            precision = self.crp.amount_to_precision(ex_name, symbol, lot)
            book = await self.crp.fetch_order_book(ex_name, symbol)
            decimal_numbers = [bid[1] for bid in book['bids'] if isinstance(bid[1], float) and not bid[1].is_integer()]
            decimals = np.log10(precision).astype(int)
            new_lot = np.around(precision, decimals=2 - decimals)
            new_lot = int(new_lot) if new_lot.is_integer() else new_lot
            if len(decimal_numbers) == 0:
                new_lot = round(new_lot)
            if 'TOMO' in symbol:
                print('kita')
            return new_lot

        
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
        self.top_targets_df['allocation_amount'] = [round(0.5 * AccountData.get_total_cash() / (len(self.top_targets_df) + len(self.bottom_targets_df)), 2)] * len(self.top_targets_df)
        self.bottom_targets_df['allocation_percent'] = [round(1.0 / (len(self.top_targets_df) + len(self.bottom_targets_df)), 6)] * len(self.bottom_targets_df)
        self.bottom_targets_df['allocation_amount'] = [round(0.5 * AccountData.get_total_cash() / (len(self.top_targets_df) + len(self.bottom_targets_df)), 2)] * len(self.bottom_targets_df)
        top_lots = []
        top_prices = []
        for i in range(len(self.top_targets_df)):
            symbol = self.top_targets_df.iloc[i]['key'].split('-')[1] if self.top_targets_df.iloc[i]['ex_name'] != 'okx' else self.top_targets_df.iloc[i]['key'].split('-')[1].replace('USDT','') + '-USDT-SWAP'
            res = await self.crp.fetch_target_price(self.top_targets_df.iloc[i]['ex_name'], symbol)
            top_prices.append(float(res['last'].iloc[0]))
            top_lot = self.test_qty_denominator * self.top_targets_df['allocation_amount'].iloc[i] / float(res['last'].iloc[0])
            symbol = self.top_targets_df['key'].iloc[i].split('-')[1] if self.top_targets_df['ex_name'].iloc[i] != 'okx' else self.top_targets_df['key'].iloc[i].split('-')[1].replace('USDT','')+'-USDT-SWAP'
            rounded_lot = await round_lot(self.top_targets_df['ex_name'].iloc[i], symbol, top_lot, float(res['last'].iloc[0]))
            top_lots.append(rounded_lot)
            print(symbol, ' : original_lot=', top_lot, ', rounded_lot=', rounded_lot, 'ratio=', top_lot / rounded_lot)
        self.top_targets_df['allocation_lot'] = top_lots
        self.top_targets_df['allocation_price'] = top_prices
        bottom_lots = []
        bottom_prices = []
        for i in range(len(self.bottom_targets_df)):
            symbol = self.bottom_targets_df.iloc[i]['key'].split('-')[1] if self.bottom_targets_df.iloc[i]['ex_name'] != 'okx' else self.bottom_targets_df.iloc[i]['key'].split('-')[1].replace('USDT','') + '-USDT-SWAP'
            res =  await self.crp.fetch_target_price(self.bottom_targets_df.iloc[i]['ex_name'], symbol)
            bottom_prices.append(float(res['last'].iloc[0]))
            bottom_lot = self.test_qty_denominator * self.bottom_targets_df['allocation_amount'].iloc[i] / float(res['last'].iloc[0]) 
            symbol = self.bottom_targets_df['key'].iloc[i].split('-')[1] if self.bottom_targets_df['ex_name'].iloc[i] != 'okx' else self.bottom_targets_df['key'].iloc[i].split('-')[1].replace('USDT','')+'-USDT-SWAP'
            rounded_lot = await round_lot(self.bottom_targets_df['ex_name'].iloc[i], symbol, bottom_lot, float(res['last'].iloc[0]))
            bottom_lots.append(rounded_lot)
            print(symbol, ' : original_lot=', bottom_lot, ', rounded_lot=', rounded_lot, 'ratio=', bottom_lot / rounded_lot)
        self.bottom_targets_df['allocation_lot'] = bottom_lots
        self.bottom_targets_df['allocation_price'] = bottom_prices
        self.top_targets_df.to_csv('./Data/top_targets_df.csv', index=False)
        self.bottom_targets_df.to_csv('./Data/bottom_targets_df.csv', index=False)

        
    






