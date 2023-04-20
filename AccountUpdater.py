import asyncio
import time
import pandas as pd

from AccountData import AccountData
from CCXTRestApiParser import CCXTRestApiParser
from CCXTRestApi import CCXTRestApi
from Settings import Settings
from Flags import Flags


'''
Botが行なった取引はRESTAPIで取得した情報そのままを正として使う。
WSはrealtimeの約定確認に使えるがRESTAPIを正のデータとする。

botがorder or holdしているsymbolは他のbotや人間が取引しないことを前提にしている。




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
・holdingがなくなったらデータも取れなくなるのでpnlなどはexit約定があるたびに計算して記録する必要がある。
・約定済みのqtyをholdから減らしていき、0になった時点で全部exitとしてholdから消す。

対応できない状況
・異なる価格で複数回に分けて利確した場合
・同じ銘柄を他のbotや人が持っていた場合。（根本的にはsub accountに分けるしかない）
・orderのpriceとavgPirceが異なる場合。（filled/closed/cancelledになったときにその時のexecuted_qtyをaccountのqtyから引いてaccount qtyが0以下になったらpositionを消す）
'''


class AccountUpdater:
    def __init__(self, ccxt_api:CCXTRestApi):
        AccountData.initialize()
        self.crp = ccxt_api
    

    async def start_update(self):
        '''
        常時order, positionを取得してAccountDataを更新する。
        '''
        while Flags.get_system_flag():
            await self.__update_free_cash()
            api_orders_df = await self.__get_all_latest_orders(Settings.exchanges)
            self.__check_executions(api_orders_df)
            con_posi_df = await self.__get_all_current_positions(Settings.exchanges)
            self.__check_positions(con_posi_df)
            self.__sync_holding_data(con_posi_df)
            self.__sync_order_data(api_orders_df)
            self.__update_unrealized_pnl()
            await asyncio.sleep(Settings.account_update_freq)

    async def __get_account_balance(self, target_exchanges:list):
        ex_df = {}
        for ex in target_exchanges:
            res = await self.crp.fetch_account_balance(ex)
            if ex == 'binance':
                ex_df[ex] = CCXTRestApiParser.parse_fetch_account_balance_binance(res)
            elif ex == 'bybit':
                ex_df[ex] = CCXTRestApiParser.parse_fetch_account_balance_bybit(res)
            elif ex == 'okx':
                ex_df[ex] = CCXTRestApiParser.parse_fetch_account_balance_okx(res)
        con_df = pd.concat(list(ex_df.values()), ignore_index=True)
        return con_df


    async def __get_all_latest_orders(self, target_exchanges:list):
        ex_df = {}
        for ex in target_exchanges:
            if ex=='binance':
                biorders = await self.crp.get_all_orders('binance')
                bitrades = await self.crp.binance_get_trades()
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
        

    def __check_executions(self, api_orders_df):
        '''
        ・exec qtyの変化は約定、その後statusの変化でpartial, full, cancelを判定。
        ・exec qtyが変化せずに、cancelになったときは単純にorder削除。Openの時はstatusのみ更新。
        ・okx以外のorderがlatest_order_dfに存在しない場合は何らかの問題がある。okxの場合はキャンセルとして処理する。
        '''

        def __check_order_matching(matched_api_order_df, account_order_df):
            if len(matched_api_order_df) == 0: #matched order data not found
                if account_order_df['ex_name'] == 'okx':
                    print('OKX ', account_order_df['side'], ' order for ', account_order_df['symbol'], ' has been canceled.')
                    AccountData.remove_order(account_order_df['id'])
                    return False
                else:
                    print('AccountData order ', account_order_df['id'], '  was not found !')
            elif len(matched_api_order_df) > 1: #multiple orders were identified
                print('Fund multiple orders')
                print(matched_api_order_df)
                return True
            else:
                return True

        def __check_exec_qty_validation(matched_api_order_df, account_order_df):
            if matched_api_order_df['executed_qty'].iloc[0] > account_order_df['executed_qty']:
                return matched_api_order_df['executed_qty'].iloc[0] - account_order_df['executed_qty']
            elif matched_api_order_df['executed_qty'].iloc[0] == account_order_df['executed_qty']:
                return 0
            elif matched_api_order_df['executed_qty'].iloc[0] < account_order_df['executed_qty']:
                print('Executed_qty was decreased in ', account_order_df['id'], '!')
                print('matched_df:')
                print(matched_api_order_df)
                print('AccountData:')
                print(account_order_df)
                return -1

        def __calc_fee(ex_name, symbol, additional_fee, fee_currency, price):
            current_fee = AccountData.get_total_fees(ex_name, symbol)
            if current_fee is not None:
                if fee_currency == 'USDT':
                    return current_fee + additional_fee
                else:
                    return current_fee + additional_fee * price
            else:
                if fee_currency == 'USDT':
                    return additional_fee
                else:
                    return additional_fee * price

        def __calc_realized_pnl(ex_name, symbol, additional_exec_qty, avg_exec_price, matched_holding_df):
            current_pnl = AccountData.get_realized_pnls(ex_name, symbol)
            additional_pnl = additional_exec_qty * (avg_exec_price - matched_holding_df['price'].iloc[0]) if matched_holding_df['side'] == 'long' else additional_exec_qty * (matched_holding_df['price'].iloc[0] - avg_exec_price)
            if current_pnl is not None:
                return current_pnl + additional_pnl
            else:
                return additional_pnl
            

        def __process_new_execution(matched_api_order_dict):
            print('New execution: ', matched_api_order_dict['ex_name'], ':', matched_api_order_dict['symbol'], '-', matched_api_order_dict['side'], ' x ', matched_api_order_dict['executed_qty'], ' @ ', matched_api_order_dict['avg_price'], )
            AccountData.add_holding(
                ex_name = matched_api_order_dict['ex_name'],
                symbol = matched_api_order_dict['symbol'],
                side = matched_api_order_dict['side'],
                price = matched_api_order_dict['avg_price'],
                qty = matched_api_order_dict['executed_qty'],
                timestamp = matched_api_order_dict['ts'],
                period = 0,
                unrealized_pnl_usd = 0,
                unrealized_pnl_ratio = 0,
                liquidation_price = 0,
                margin_ratio = 0
            )
            if matched_api_order_dict['status'] == 'filled' or matched_api_order_dict['status'] == 'closed' or matched_api_order_dict['status'] == 'canceled': #order to be removed
                AccountData.remove_order(matched_api_order_dict['id'])
            else: #order still active
                AccountData.update_order(
                    order_id = matched_api_order_dict['id'],
                    executed_qty = matched_api_order_dict['executed_qty'],
                )
            


        def __process_additional_execution(matched_api_order_dict, matched_holding_df, additional_exec_qty):
            print('Additional execution: ', matched_api_order_dict['ex_name'], ':', matched_api_order_dict['symbol'], '-', matched_api_order_dict['side'], ' x ', matched_api_order_dict['executed_qty'], ' @ ', matched_api_order_dict['avg_price'], )
            new_avg_price = (matched_holding_df['price'] * matched_holding_df['qty'].iloc[0] + matched_api_order_dict['avg_price'] * matched_api_order_dict['executed_qty']) / (matched_holding_df['qty'].iloc[0] + matched_api_order_dict['executed_qty'])
            AccountData.update_holding(
                ex_name = account_order['ex_name'],
                symbol = account_order['symbol'],
                qty = additional_exec_qty + holding_data_df['qty'].iloc[0],
                price = new_avg_price
            )
            if matched_api_order_dict['status'] == 'filled' or matched_api_order_dict['status'] == 'closed' or matched_api_order_dict['status'] == 'canceled': #order to be removed
                AccountData.remove_order(matched_api_order_dict['id'])
            else: #order still active
                AccountData.update_order(
                    order_id = matched_api_order_dict['id'],
                    executed_qty = matched_api_order_dict['executed_qty'],
                )


        def __process_partial_exit_execution(matched_api_order_dict, matched_holding_df, additional_exec_qty):
            print('Patial exit execution: ', matched_api_order_dict['ex_name'], ':', matched_api_order_dict['symbol'], '-', matched_api_order_dict['side'], ' x ', matched_api_order_dict['executed_qty'], ' @ ', matched_api_order_dict['avg_price'], )
            realized_pnl = __calc_realized_pnl(matched_holding_df['ex_name'].iloc[0], matched_holding_df['symbol'].iloc[0], additional_exec_qty, matched_api_order_dict['avg_price'], matched_holding_df)
            AccountData.set_realized_pnls(matched_holding_df['ex_name'].iloc[0], matched_holding_df['symbol'].iloc[0], realized_pnl)
            AccountData.update_holding(
                ex_name = account_order['ex_name'],
                symbol = account_order['symbol'],
                qty = holding_data_df['qty'].iloc[0] - additional_exec_qty,
            )
            if matched_api_order_dict['status'] == 'filled' or matched_api_order_dict['status'] == 'closed' or matched_api_order_dict['status'] == 'canceled': #order to be removed
                AccountData.remove_order(matched_api_order_dict['id'])
            else: #order still active
                AccountData.update_order(
                    order_id = matched_api_order_dict['id'],
                    executed_qty = matched_api_order_dict['executed_qty'],
                )

        
        def __process_full_exit_execution(matched_api_order_dict, matched_holding_df, additional_exec_qty):
            print('Full exit execution: ', matched_api_order_dict['ex_name'], ':', matched_api_order_dict['symbol'], '-', matched_api_order_dict['side'], ' x ', matched_api_order_dict['executed_qty'], ' @ ', matched_api_order_dict['avg_price'], )
            realized_pnl = __calc_realized_pnl(matched_holding_df['ex_name'].iloc[0], matched_holding_df['symbol'].iloc[0], additional_exec_qty, matched_api_order_dict['avg_price'], matched_holding_df)
            AccountData.set_realized_pnls(matched_holding_df['ex_name'].iloc[0], matched_holding_df['symbol'].iloc[0], realized_pnl)
            AccountData.remove_holding(matched_holding_df['symbol'].iloc[0])
            if matched_api_order_dict['status'] == 'filled' or matched_api_order_dict['status'] == 'closed' or matched_api_order_dict['status'] == 'canceled': #order to be removed
                AccountData.remove_order(matched_api_order_dict['id'])
            else: #order still active
                AccountData.update_order(
                    order_id = matched_api_order_dict['id'],
                    executed_qty = matched_api_order_dict['executed_qty'],
                )

        def __process_exit_and_opposite_entry(matched_api_order_dict, matched_holding_df):
            print('Exit and opposite entry execution: ', matched_api_order_dict['ex_name'], ':', matched_api_order_dict['symbol'], '-', matched_api_order_dict['side'], ' x ', matched_api_order_dict['executed_qty'], ' @ ', matched_api_order_dict['avg_price'], )
            realized_pnl = __calc_realized_pnl(matched_holding_df['ex_name'].iloc[0], matched_holding_df['symbol'].iloc[0], matched_holding_df['qty'].iloc[0], matched_api_order_dict['avg_price'], matched_holding_df)
            AccountData.set_realized_pnls(matched_holding_df['ex_name'].iloc[0], matched_holding_df['symbol'].iloc[0], realized_pnl)
            new_holding_qty = matched_api_order_dict['executed_qty'] - matched_holding_df['qty'].iloc[0]
            AccountData.remove_holding(matched_holding_df['symbol'].iloc[0])
            AccountData.add_holding(
                ex_name = matched_api_order_dict['ex_name'],
                symbol = matched_api_order_dict['symbol'],
                side = matched_api_order_dict['side'],
                price = matched_api_order_dict['price'],
                qty =  new_holding_qty,
                timestamp = matched_api_order_dict['ts'],
                period = 0,
                unrealized_pnl_usd=0,
                unrealized_pnl_ratio=0,
                liquidation_price=0,
                margin_ratio=0
            )
            if matched_api_order_dict['status'] == 'filled' or matched_api_order_dict['status'] == 'closed' or matched_api_order_dict['status'] == 'canceled': #order to be removed
                AccountData.remove_order(matched_api_order_dict['id'])
            else: #order still active
                AccountData.update_order(
                    order_id = matched_api_order_dict['id'],
                    executed_qty = matched_api_order_dict['executed_qty'],
                )

        def __check_okx_order_cancel(matched_api_order_df, account_order):
            if account_order['ex_name'] == 'okx':
                matched_df = matched_api_order_df[matched_api_order_df['id'] == account_order['id']]
                if len(matched_df) == 0:
                    print('OKX order has been cancelled. symbol=', account_order['symbol'])
                    AccountData.remove_order(account_order['id'])
                    return False
            return True


        orders = AccountData.get_order_df()
        for index, account_order in orders.iterrows():
            matched_api_order_df = api_orders_df[api_orders_df['id']==account_order['id']] #約定確認したいorder_idに一致するAPIで取得したorder data
            if __check_okx_order_cancel(matched_api_order_df, account_order):
                if __check_order_matching(matched_api_order_df, account_order):
                    if account_order['type'] == 'limit':
                        if __check_exec_qty_validation(matched_api_order_df, account_order) > 0: #約定あり
                            matched_api_order_dict = matched_api_order_df.to_dict(orient='records')[0]
                            additional_exec_qty = matched_api_order_dict['executed_qty'] -  account_order['executed_qty']
                            holding_data_df = AccountData.get_holding_df()
                            matched_holding_data_df = pd.DataFrame()
                            if len(holding_data_df) > 0:
                                matched_holding_data_df = holding_data_df[(holding_data_df['ex_name']==matched_api_order_dict['ex_name']) & (holding_data_df['symbol']==matched_api_order_dict['symbol'])]
                            new_fee = __calc_fee(matched_api_order_dict['ex_name'], matched_api_order_dict['symbol'], matched_api_order_dict['fee'], matched_api_order_dict['fee_currency'], matched_api_order_df['price'])
                            AccountData.set_total_fees(matched_api_order_dict['ex_name'], matched_api_order_dict['symbol'], new_fee)
                            if len(matched_holding_data_df) == 0: #new execution
                                __process_new_execution(matched_api_order_dict)
                            elif len(matched_holding_data_df) == 1 and matched_api_order_dict['side'] == account_order['side']: #additional execution
                                __process_additional_execution(matched_api_order_dict, matched_holding_data_df, additional_exec_qty)
                            elif len(matched_holding_data_df) == 1 and matched_api_order_dict['side'] != account_order['side']: #opposite execution
                                if matched_holding_data_df['qty'] > matched_api_order_dict['executed_qty']: #partial exit
                                    __process_partial_exit_execution(matched_api_order_dict, matched_holding_data_df, additional_exec_qty)
                                elif matched_holding_data_df['qty'] == matched_api_order_dict['executed_qty']: #full exit
                                    __process_full_exit_execution(matched_api_order_dict, matched_holding_data_df, additional_exec_qty)
                                else: #exit and opposite entry
                                    print('Exit and opposite entry is not intended action !')
                                    print('Order:')
                                    print(matched_api_order_dict)
                                    print('Holding:')
                                    print(matched_holding_data_df)
                                    __process_exit_and_opposite_entry(matched_api_order_dict, matched_holding_data_df)
                        else: #no execution
                            if account_order['status']=='canceled':
                                print(account_order['ex_name'], ' order has been canceled.', 'symbol=',account_order['symbol'])
                                AccountData.remove_order(account_order['id'])
                            elif account_order['status']=='closed' or account_order['status']=='filled':
                                print(account_order['ex_name'], ' order has been unintentionally ',account_order['status'],  ', symbol=',account_order['symbol'])
                                AccountData.remove_order(account_order['id'])
                    else: #market order
                        counter = 0
                        while True:
                            time.sleep(1)
                            if __check_exec_qty_validation(matched_api_order_df, account_order) > 0: #約定あり
                                matched_api_order_dict = matched_api_order_df.to_dict(orient='records')[0]
                                additional_exec_qty = matched_api_order_dict['executed_qty'] -  account_order['executed_qty']
                                holding_data_df = AccountData.get_holding_df()
                                matched_holding_data_df = pd.DataFrame()
                                if len(holding_data_df) > 0:
                                    matched_holding_data_df = holding_data_df[(holding_data_df['ex_name']==matched_api_order_dict['ex_name']) & (holding_data_df['symbol']==matched_api_order_dict['symbol'])]
                                new_fee = __calc_fee(matched_api_order_dict['ex_name'], matched_api_order_dict['symbol'], matched_api_order_dict['fee'], matched_api_order_dict['fee_currency'], matched_api_order_df['price'])
                                AccountData.set_total_fees(matched_api_order_dict['ex_name'], matched_api_order_dict['symbol'], new_fee)
                                if len(matched_holding_data_df) == 0: #new execution
                                    __process_new_execution(matched_api_order_dict)
                                elif len(matched_holding_data_df) == 1 and matched_api_order_dict['side'] == account_order['side']: #additional execution
                                    __process_additional_execution(matched_api_order_dict, matched_holding_data_df, additional_exec_qty)
                                elif len(matched_holding_data_df) == 1 and matched_api_order_dict['side'] != account_order['side']: #opposite execution
                                    if matched_holding_data_df['qty'] > matched_api_order_dict['executed_qty']: #partial exit
                                        __process_partial_exit_execution(matched_api_order_dict, matched_holding_data_df, additional_exec_qty)
                                    elif matched_holding_data_df['qty'] == matched_api_order_dict['executed_qty']: #full exit
                                        __process_full_exit_execution(matched_api_order_dict, matched_holding_data_df, additional_exec_qty)
                                    else: #exit and opposite entry
                                        print('Exit and opposite entry is not intended action !')
                                        print('Order:')
                                        print(matched_api_order_dict)
                                        print('Holding:')
                                        print(matched_holding_data_df)
                                        __process_exit_and_opposite_entry(matched_api_order_dict, matched_holding_data_df)
                                break
                            counter += 1
                            if counter > 10:
                                print('Can not confirm execution of a market order !')
                                print('Order:')
                                print(account_order)
                                print('Holding:')
                                print(matched_holding_data_df)
                                return None





    def __check_positions(self, curernt_position_df):
        '''
        ・APIでpositionデータを取得してAccounDataのpositionとのギャップを確認。
        ・同一のsymbolの取引は当該botのみが行なっている前提。
        '''
        holding_df = AccountData.get_holding_df()
        for index, row in holding_df.iterrows():
            matched_position_df = curernt_position_df[curernt_position_df['symbol'].iloc[0] == row['symbol']]
            if len(matched_position_df) == 0: #no matched holding data from API not found
                print('No matched holding is not found!')
                print('AccountData.holding')
                print(row)
            else:
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


    def __sync_holding_data(self, curernt_position_df):
        holding_df = AccountData.get_holding_df()
        for index, holding in holding_df.iterrows():
            matched_current_position_df = curernt_position_df[(curernt_position_df['ex_name'].iloc[0] == holding['ex_name']) & (curernt_position_df['symbol'].iloc[0] == holding['symbol'])]
            if len(matched_current_position_df) == 1:
                matched_current_position_dict = matched_current_position_df.to_dict(orient='records')[0]
                AccountData.update_holding(
                    ex_name=matched_current_position_dict['ex_name'],
                    symbol=matched_current_position_dict['symbol'],
                    side = matched_current_position_dict['side'],
                    price=matched_current_position_dict['price'],
                    qty=matched_current_position_dict['qty'],
                    timestamp=matched_current_position_dict['timestamp'],
                    period=time.time() - float(matched_current_position_dict['period']),
                    unrealized_pnl_usd=matched_current_position_dict['unrealized_pnl'],
                    unrealized_pnl_ratio=matched_current_position_dict['unrealized_pnl_ratio'],
                    liquidation_price=matched_current_position_dict['liquidation_price'],
                    margin_ratio=matched_current_position_dict['margin_ratio']
                )
            else:
                print('Matched position df size is not 1 !')
                print('current positon df:')
                print(matched_current_position_dict)
                print('Holding df:')
                print(holding_df)
        print('Completed sync all holdings.')


    def __sync_order_data(self, current_order_df):
        order_df = AccountData.get_order_df()
        for index, order in order_df.iterrows():
            matched_current_order_df = current_order_df[current_order_df['id'] == order['id']]
            if len(matched_current_order_df) == 1:
                matched_current_order_dict = matched_current_order_df.to_dict(orient='records')[0]
                AccountData.update_order(
                    order_id=matched_current_order_dict['id'],
                    ex_name=matched_current_order_dict['ex_name'],
                    symbol=matched_current_order_dict['symbol'],
                    side = matched_current_order_dict['side'],
                    type=matched_current_order_dict['type'],
                    price=matched_current_order_dict['price'],
                    avg_price=matched_current_order_dict['avg_price'],
                    status=matched_current_order_dict['status'],
                    original_qty=matched_current_order_dict['original_qty'],
                    executed_qty=matched_current_order_dict['executed_qty'],
                    fee=matched_current_order_dict['fee'],
                    fee_currency=matched_current_order_dict['fee_currency'],
                )
            else:
                print('matched order data size is ', len(matched_current_order_df), ' not 1 !')
                print('matched_current_order_df')
                print(matched_current_order_df)
                print('AccountData.order_df')
                print(order)

    async def __update_free_cash(self):
        balance_df = await self.__get_account_balance(Settings.exchanges)
        usdt_balance = balance_df.loc[balance_df['asset'] == 'USDT', 'balance'].sum()
        AccountData.set_total_cash(usdt_balance)

    def __update_unrealized_pnl(self):
        holding_df = AccountData.get_holding_df()
        AccountData.set_total_unrealized_pnl(sum(list(holding_df['unrealized_pnl_usd'])))



        


        

        



