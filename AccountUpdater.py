import asyncio
import time
import pandas as pd

from AccountData import AccountData
from CCXTRestApiParser import CCXTRestApiParser
from CCXTRestApi import CCXTRestApi
from Settings import Settings
from Flags import Flags


'''
現在AccountDataに載っているorder idの現在の状況を確認して、それに応じてpnl, order, holdingを適切に更新したい。
通常はprivate wsで取得するにしても、REST APIでの確認は必要になる。
binanceとそれ以外でccxtの返り値の内容が異なる。
order_idを１つずつAPIで問い合わせて現在の情報を取得するのが一番シンプルで確実性が高い。
しかしapi callが増えて時間もかかる。
top/bottomで計20銘柄でbinanceで16くらいなので、callとしては問題ないはず。

binanceはorderのデータにfeeが含まれていないのでget tradesしてそこからorder idで該当のものを見つける必要がある。

exchangeごとの関数にorder_idをリストで渡したらそれぞれの現在の状態をAccountDataと同じ形式で返す関数を作って、それで更新有無に応じて


status一覧：
binance:NEW, FILLED, CANCELED
bybit:open, closed, canceled
okx:open, closed
'''


class AccountUpdater:
    def __init__(self):
        AccountData.initialize()
        self.crp = CCXTRestApi()
    

    async def start_update(self):
        '''
        常時order, positionを取得してAccountDataを更新する。
        '''
        while Flags.get_system_flag():
            con_df = await self.__get_all_latest_orders()
            #self.add_account_data(con_df.iloc[10:12])
            self.__check_executions(con_df)
            await asyncio.sleep(Settings.account_update_freq)


    async def __get_all_latest_orders(self, target_exchanges:list):
        ex_df = {}
        for ex in target_exchanges:
            if ex=='binance':
                biorders = await self.crp.get_all_orders('binance')
                bitrades = await self.crp.get_binance_all_trades()
                ex_df['binance'] = CCXTRestApiParser.parse_get_all_orders_binance(all_orders=biorders, binace_trades=bitrades)
            elif ex=='okx':
                okorders = await self.crp.get_all_orders('okx')
                ex_df['okx'] = CCXTRestApiParser.parse_get_all_orders_okx(open_orders=okorders['open_orders'], closed_orders=okorders['closed_orders'])
            else:
                orders = await self.crp.get_all_orders(ex)
                ex_df[ex] = CCXTRestApiParser.parse_get_all_orders_general(ex, orders)
        con_df = pd.concat(list(ex_df.values()), ignore_index=True)
        return con_df
        


    def __check_executions(self, latest_order_df):
        '''
        ・exec qtyの変化は約定、その後statusの変化でpartial, full, cancelを判定。
        ・exec qtyが変化せずに、cancelになったときは単純にorder削除。Openの時はstatusのみ更新。
        ・okx以外のorderがlatest_order_dfに存在しない場合は何らかの問題がある。okxの場合はキャンセルとして処理する。
        '''
        orders = AccountData.get_order_df()
        for index, row in orders.iterrows():
            matched_df = latest_order_df[latest_order_df['id']==row['id']]
            if len(matched_df) == 0:
                if row['ex_name'] == 'okx':
                    print('OKX ', row['side'], ' order for ', row['symbol'], ' has been canceled.')
                    AccountData.remove_order(row['id'])
                else:
                    print('AccountData order ', row['id'], '  was not found !')
            elif len(matched_df) > 1:
                print('Fund multiple orders')
                print(matched_df)
            else:
                if matched_df['executed_qty'].iloc[0] != row['executed_qty']: #execution
                    if matched_df['executed_qty'].iloc[0] > row['executed_qty']:
                        if matched_df['status'].iloc[0].lower() == 'open' or  matched_df['status'].iloc[0].lower() == 'new':#partial execution
                            print(row['ex_name'], row['side'] ,' order for ', row['symbol'], ' has been partially executed.')
                            AccountData.update_order(order_id=row['id'], executed_qty=matched_df['executed_qty'].iloc[0], status=matched_df['status'].iloc[0])
                            #AccountData.add_holding()
                            #calc pnl
                        elif matched_df['status'].iloc[0].lower() == 'filled' or  matched_df['status'].iloc[0].lower() == 'closed':#fully executed
                            print(row['ex_name'], row['side'] ,' order for ', row['symbol'], ' has been fully executed.')
                            AccountData.remove_order(row['id'])
                            #AccountData.add_holding()
                            #calc pnl
                    else:
                        print('Executed_qty was direased in ', row['id'], '!')
                        print('matched_df:')
                        print(matched_df)
                        print('AccountData:')
                        print(row)
                else: #no exdcution
                    if matched_df['status'].iloc[0].lower() == 'canceled':
                        print(row['ex_name'], row['side'] ,' order for ', row['symbol'], ' has been canceled.')
                        AccountData.remove_order(row['id'])
    
    def __process_execution(self, )



