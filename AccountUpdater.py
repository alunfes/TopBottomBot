import asyncio
import time
import pandas as pd

from AccountData import AccountData
from CCXTRestApiParser import CCXTRestApiParser
from CCXTRestApi import CCXTRestApi
from Settings import Settings
from Flags import Flags


'''
Filled, Closedになった場合はその時のavgPriceでpnl計算すればいい。
Partialの場合は稀にしか発生しないと思うが、部分約定の度にavgPriceでpnl計算すると場合によっては値が間違ってしまう。
（とりあえずpartialの時もavgPriceで簡易的に計算して、実際のpnlへの反映はfilled,closedの時のみ行うようにするか？）
いずれの取引所もaverage_priceは約定した時のみ表示される。


status一覧:
binance:NEW, FILLED, CANCELED
bybit:open, closed, canceled
okx:open, closed

orderの約定確認:
・__get_all_latest_ordersで各取引所のexec qtyなどを同じフォーマットで取得できる。AccountDataのexec_qtyとの差が新しく約定した量。

feeの計算:
・__get_all_latest_ordersで各取引所のfeeを同じフォーマットで取得できる、

pnlの計算:
・qty * (exec_price - entry_price)で計算できるので、exitの約定がある場合に計算できる。
しかし、APIで直接realized pnlを取得する手段が必要。

positionの更新確認:
・fetch_positionsで現在のposi, unrealized_pnlなど取得できる。

対応できない状況
・異なる価格で複数回に分けて利確した場合
・同じ銘柄を他のbotや人が持っていた場合。（根本的にはsub accountに分けるしかない）
・orderのpriceとavgPirceが異なる場合。（filled/closed/cancelledになったときにその時のexecuted_qtyをaccountのqtyから引いてaccount qtyが0以下になったらpositionを消す）
'''


class AccountUpdater:
    def __init__(self, ccxt_api):
        AccountData.initialize()
        self.crp = ccxt_api
    

    async def start_update(self):
        '''
        常時order, positionを取得してAccountDataを更新する。
        '''
        while Flags.get_system_flag():
            con_df = await self.__get_all_latest_orders()
            #self.add_account_data(con_df.iloc[10:12])
            self.__check_executions(con_df)
            con_posi_df = await self.__get_all_current_positions()
            self.__check_positions(con_posi_df)
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
    
    async def __get_all_current_positions(self, target_exchanges:list):
        ex_df = {}
        for ex in target_exchanges:
            positions = await self.crp.fetch_positions(ex)
            if ex == 'binance':
                ex_df[ex] = CCXTRestApiParser.parse_fetch_position_binance(positions)
            elif ex == 'bybit':
                ex_df[ex] = CCXTRestApiParser.parse_fetch_position_bybit(positions)
            if ex == 'okx':
                ex_df[ex] = CCXTRestApiParser.parse_fetch_position_okx(positions)
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
            matched_df = latest_order_df[latest_order_df['id']==row['id']] #約定確認したいorder_idに一致するAPIで取得したorder data
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
                        if matched_df['executed_qty'].iloc[0] <= row['original_qty']:
                            additional_exec_qty = matched_df['executed_qty'].iloc[0] -  row['executed_qty']
                            if matched_df['status'].iloc[0].lower() == 'open' or  matched_df['status'].iloc[0].lower() == 'new':#partial execution
                                print(row['ex_name'], row['side'] ,' order for ', row['symbol'], ' has been partially executed.')
                                AccountData.update_order(order_id=row['id'], executed_qty=matched_df['executed_qty'].iloc[0], status=matched_df['status'].iloc[0])
                                self.__process_execution(matched_df, additional_exec_qty)
                            elif matched_df['status'].iloc[0].lower() == 'filled' or  matched_df['status'].iloc[0].lower() == 'closed':#fully executed
                                print(row['ex_name'], row['side'] ,' order for ', row['symbol'], ' has been fully executed.')
                                self.__log_full_execution(matched_df)
                                AccountData.remove_order(row['id'])
                                self.__process_execution(matched_df, additional_exec_qty)
                            elif matched_df['status'].iloc[0].lower() == 'canceled': #partial executed and canceled
                                print(row['ex_name'], row['side'] ,' order for ', row['symbol'], ' has been partially executed and canceled.')
                                self.__log_full_execution(matched_df)
                                AccountData.remove_order(row['id'])
                                self.__process_execution(matched_df, additional_exec_qty)
                        else:
                            print('Executed qty(', matched_df['executed_qty'].iloc[0] ,') in ',  row['ex_name'], 'for ', row['symbol'] ,' is larger than original qty(', row['original_qty'], ')')
                    else:
                        print('Executed_qty was decreased in ', row['id'], '!')
                        print('matched_df:')
                        print(matched_df)
                        print('AccountData:')
                        print(row)
                else: #no execution
                    if matched_df['status'].iloc[0].lower() == 'canceled':
                        print(row['ex_name'], row['side'] ,' order for ', row['symbol'], ' has been canceled.')
                        AccountData.remove_order(row['id'])
    

    def __process_execution(self, matched_order_df, exec_ex_name, exec_symbol, exec_side, exec_price, exec_qty, exec_ts, additional_exec_qty:float):
        '''
        ・symbolがholdingにない場合は、それを追加。
        ・symbolがholdingにあり同じsideの場合は追加して平均値を修正
        ・symbolがholdingにあり逆のsideの場合はholding qtyを減らして、realized pnlを計算、
        '''
        holding_df = AccountData.get_holding_df()
        matched_holding_df = holding_df[holding_df['symbol']==exec_symbol and holding_df['ex_name'] == exec_ex_name]
        if len(matched_holding_df) == 0:#new position
            AccountData.add_holding(
                exec_ex_name, 
                exec_symbol,
                exec_side,
                exec_price,
                exec_qty,
                exec_ts,
                0, 0, 0, 0, 0)
        else:
            if matched_holding_df['side'].iloc[0] == exec_side: #additional entry
                AccountData.update_holding(
                    symbol = exec_symbol,
                    qty = float(matched_order_df['executed_qty'].iloc[0]))
            else:#exit entry
                additional_realized_pnl = additional_exec_qty * (matched_order_df['price'] - matched_holding_df['price']) if matched_holding_df['side'] == 'long' else additional_exec_qty * (matched_holding_df['price'] - matched_order_df['price'])
                AccountData.update_holding(
                    symbol = matched_order_df['symbol'].iloc[0],
                    qty=matched_holding_df['qty'].iloc[0] - additional_exec_qty,
                )

    def __check_positions(self, curernt_position_df):
        '''
        ・APIでpositionデータを取得してAccounDataのpositionとのギャップを確認。
        ・同一のsymbolの取引は当該botのみが行なっている前提。
        '''
        holding_df = AccountData.get_holding_df()
        for index, row in holding_df.iterrows():
            matched_position_df = curernt_position_df[curernt_position_df['symbol'].iloc[0] == row['symbol']]
            if matched_position_df['side'].iloc[0] != row['side']:
                print('Holding side is not matched in ', row['ex_name'], '-', row['symbol'], ' with API data !')
                print(matched_position_df['side'].iloc[0])
                print(row)
            if abs(matched_position_df['price'].iloc[0] - row['price']) < 0.1 * row['price']:
                print('Holding price is not matched in ', row['ex_name'], '-', row['symbol'], ' with API data !')
                print(matched_position_df['side'].iloc[0])
                print(row)
            AccountData.update_holding(
                symbol=row['symbol'],
                price=float(matched_position_df['price']),
                qty=float(matched_position_df['qty']),
                unrealized_pnl_usd=float(matched_position_df['unrealized_pnl']),
                unrealized_pnl_ratio=float(matched_position_df['unrealized_pnl_ratio']),
                liquidation_price=float(matched_position_df['liquidation_price']),
                margin_ratio=float(matched_position_df['margin_ratio'])
            )

    def __log_full_execution(self, executed_order_data):
        holding_df = AccountData.get_holding_df()
        holding_df = holding_df[holding_df['symbol']==executed_order_data['symbol'].iloc[0]]
        AccountData.num_trade += 1 
        holding_df['qty'] * (executed_order_data['price'].iloc[0] - holding_df['price']) if executed_order_data['side'] == 'buy'

        


        

        



