import asyncio
import time
import pandas as pd

from AccountData import AccountData
from CCXTRestApiParser import CCXTRestApiParser
from CCXTRestApi import CCXTRestApi
from Settings import Settings
from Flags import Flags
from DisplayMessage import DisplayMessage
from CommunicationData import CommunicationData


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
        await asyncio.sleep(10)
        num_account_loop = 0
        while Flags.get_system_flag():
            await self.__update_free_cash()
            api_orders_df = await self.__get_all_latest_orders(Settings.exchanges)
            self.__check_executions(api_orders_df)
            con_posi_df = await self.__get_all_current_positions(Settings.exchanges)
            self.__check_positions(con_posi_df)
            await self.__sync_holding_data(con_posi_df)
            self.__sync_order_data(api_orders_df)
            self.__update_unrealized_pnl()
            self.__update_total_pnl()
            self.__update_total_amount()
            print('********************************************')
            print('Account #',num_account_loop)
            print('total pnl=', AccountData.get_total_pnl())
            print('total unrealized pnl=', AccountData.get_total_unrealized_pnl())
            print('total realized pnl=', AccountData.get_total_realized_pnl())
            print('total fee=', AccountData.get_total_fee())
            print('num trade=', AccountData.get_num_trade())
            print('num win=', AccountData.get_num_win())
            AccountData.display_balance_sheet()
            print('********************************************')
            CommunicationData.add_message('update', 'AccountUpdater', 'start_update', 'total pnl='+str(AccountData.get_total_pnl()))
            num_account_loop += 1
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
                df = await self.__get_okx_all_orders()
                ex_df['okx'] = pd.concat([ex_df['okx'], df], axis=0)
            else:
                orders = await self.crp.get_all_orders(ex)
                ex_df[ex] = CCXTRestApiParser.parse_get_all_orders_general(ex, orders)
        # 一意のインデックスを生成する
        for key, value in ex_df.items():
            value.reset_index(drop=True, inplace=True)

        con_df = pd.concat(list(ex_df.values()), axis=0, ignore_index=True)
        con_df.reset_index(drop=True, inplace=True)
        return con_df
    

    async def __get_okx_all_orders(self):
        okorders = await self.crp.get_all_orders('okx')
        api_df = CCXTRestApiParser.parse_get_all_orders_okx(open_orders=okorders['open_orders'], closed_orders=okorders['closed_orders'])
        order_df = AccountData.get_order_df()
        dict_list = []
        for index, account_order in order_df.iterrows():
            if account_order['ex_name'] == 'okx' and account_order['id'] not in list(api_df['id']):
                order = await self.crp.fetch_order(ex_name='okx', symbol=account_order['symbol'], order_id=account_order['id'])
                if len(order) > 1:
                    dict_list.append({'ex_name':'okx', 'id':order['id'], 'symbol':order['symbol'], 'base_asset':order['symbol'].split('/')[0], 
                                  'quote_asset':order['symbol'].split(':')[-1], 'status':order['status'], 'price':order['price'], 
                                  'avg_price':order['average'], 'side':order['side'], 'type':order['type'], 'original_qty':order['amount'],
                                  'executed_qty':order['filled'], 'ts':order['timestamp'], 'fee':order['fee']['cost'], 'fee_currency':order['fee']['currency']})
                else:
                    DisplayMessage.display_message('AccountUpdater','__get_okx_all_orders', 'error', ['Order length invalid!', account_order, order])
        if len(dict_list) > 0:
            return pd.DataFrame(dict_list)
        else:
            return pd.DataFrame()





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
                    DisplayMessage('AccounUpdater','__check_order_matching', ['OKX '+account_order_df['side']+ ' order for '+account_order_df['symbol']+' has been canceled.'] )
                    AccountData.remove_order(account_order_df['id'])
                    return False
                else:
                    DisplayMessage.display_message('AccounUpdater','__check_order_matching', 'error', ['AccountData order '+ account_order_df['id']+ '  was not found !'])    
            elif len(matched_api_order_df) > 1: #multiple orders were identified
                DisplayMessage.display_message('AccounUpdater','__check_order_matching', 'error', ['Fund multiple orders', matched_api_order_df])
                return True
            else:
                return True


        def __check_exec_qty_validation(matched_api_order_df, account_order_df):
            if matched_api_order_df['executed_qty'].iloc[-1] > account_order_df['executed_qty']:
                return matched_api_order_df['executed_qty'].iloc[-1] - account_order_df['executed_qty']
            elif matched_api_order_df['executed_qty'].iloc[-1] == account_order_df['executed_qty']:
                return 0
            elif matched_api_order_df['executed_qty'].iloc[-1] < account_order_df['executed_qty']:
                DisplayMessage('AccountUpdater','__check_exec_qty_validation',['Executed_qty was decreased in '+ account_order_df['id']+ '!',
                                                                               'matched_df:',
                                                                               matched_api_order_df,
                                                                               'AccountData:',
                                                                               account_order_df])
                return -1

        def __calc_fee(ex_name, base, quote, additional_fee, fee_currency, price):
            current_fee = AccountData.get_total_fees(ex_name, base, quote)
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

        def __calc_realized_pnl(ex_name, base, quote, additional_exec_qty, avg_exec_price, matched_holding_df):
            current_pnl = AccountData.get_realized_pnls(ex_name, base, quote)
            additional_pnl = additional_exec_qty * (avg_exec_price - matched_holding_df['price'].iloc[-1]) if matched_holding_df['side'].iloc[-1] == 'long' else additional_exec_qty * (matched_holding_df['price'].iloc[-1] - avg_exec_price)
            if current_pnl is not None:
                return current_pnl + additional_pnl
            else:
                return additional_pnl
            

        def __process_new_execution(matched_api_order_dict):
            print('New execution: ', matched_api_order_dict['ex_name'], ':', matched_api_order_dict['symbol'], '-', matched_api_order_dict['side'], ' x ', matched_api_order_dict['executed_qty'], ' @ ', matched_api_order_dict['avg_price'], )
            AccountData.add_holding(
                ex_name = matched_api_order_dict['ex_name'],
                symbol = matched_api_order_dict['symbol'],
                base_asset=matched_api_order_dict['base_asset'],
                quote_asset=matched_api_order_dict['quote_asset'],
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
            #print('Additional execution: ', matched_api_order_dict['ex_name'], ':', matched_api_order_dict['symbol'], '-', matched_api_order_dict['side'], ' x ', matched_api_order_dict['executed_qty'], ' @ ', matched_api_order_dict['avg_price'], )
            DisplayMessage.display_message('AccountUpdater', '__process_additional_execution', 'message', [matched_api_order_dict['ex_name']+ ':'+ matched_api_order_dict['symbol']+ '-'+ matched_api_order_dict['side']+ ' x '+ str(matched_api_order_dict['executed_qty']) + ' @ '+ str(matched_api_order_dict['avg_price'])])
            new_avg_price = (matched_holding_df['price'].iloc[0] * matched_holding_df['qty'].iloc[0] + matched_api_order_dict['avg_price'] * matched_api_order_dict['executed_qty']) / (matched_holding_df['qty'].iloc[0] + matched_api_order_dict['executed_qty'])
            AccountData.update_holding(
                ex_name = matched_holding_df['ex_name'].iloc[0],
                base_asset=matched_holding_df['base_asset'].iloc[0],
                quote_asset=matched_holding_df['quote_asset'].iloc[0],
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
            #print('Patial exit execution: ', matched_api_order_dict['ex_name'], ':', matched_api_order_dict['symbol'], '-', matched_api_order_dict['side'], ' x ', matched_api_order_dict['executed_qty'], ' @ ', matched_api_order_dict['avg_price'], )
            DisplayMessage.display_message('AccountUpdater', '__process_partial_exit_execution', 'message', ['Patial exit execution: '+ matched_api_order_dict['ex_name']+ ':'+ matched_api_order_dict['symbol']+ '-'+ matched_api_order_dict['side']+ ' x '+ str(matched_api_order_dict['executed_qty'])+ ' @ '+ str(matched_api_order_dict['avg_price'])])
            realized_pnl = __calc_realized_pnl(matched_holding_df['ex_name'].iloc[0], matched_holding_df['base_asset'].iloc[0],matched_holding_df['quote_asset'].iloc[0], additional_exec_qty, matched_api_order_dict['avg_price'], matched_holding_df)
            AccountData.set_realized_pnls(matched_holding_df['ex_name'].iloc[0], matched_holding_df['base_asset'].iloc[0], matched_holding_df['quote_asset'].iloc[0], realized_pnl)
            AccountData.update_holding(
                ex_name = matched_holding_df['ex_name'].iloc[0],
                base_asset=matched_holding_df['based'].iloc[0],
                quote_asset=matched_holding_df['quote'].iloc[0],
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
            #print('Full exit execution: ', matched_api_order_dict['ex_name'], ':', matched_api_order_dict['symbol'], '-', matched_api_order_dict['side'], ' x ', matched_api_order_dict['executed_qty'], ' @ ', matched_api_order_dict['avg_price'], )
            DisplayMessage.display_message('AccountUpdater', '__process_full_exit_execution', 'message', ['Full exit execution: '+ matched_api_order_dict['ex_name']+ ':'+ matched_api_order_dict['symbol']+ '-'+ matched_api_order_dict['side']+ ' x '+ str(matched_api_order_dict['executed_qty'])+ ' @ '+ str(matched_api_order_dict['avg_price'])])
            realized_pnl = __calc_realized_pnl(matched_holding_df['ex_name'].iloc[0], matched_holding_df['base_asset'].iloc[0],matched_holding_df['quote_asset'].iloc[0], additional_exec_qty, matched_api_order_dict['avg_price'], matched_holding_df)
            AccountData.set_realized_pnls(matched_holding_df['ex_name'].iloc[0], matched_holding_df['base_asset'].iloc[0], matched_holding_df['quote_asset'].iloc[0], realized_pnl)
            AccountData.remove_holding(matched_holding_df['ex_name'].iloc[0], matched_holding_df['base_asset'].iloc[0], matched_holding_df['quote_asset'].iloc[0])
            if realized_pnl > 0:
                num_win = AccountData.get_num_win()
                AccountData.set_num_win(num_win+1)
            num_trade = AccountData.get_num_trade()
            AccountData.set_num_trade(num_trade+1)
            if matched_api_order_dict['status'] == 'filled' or matched_api_order_dict['status'] == 'closed' or matched_api_order_dict['status'] == 'canceled': #order to be removed
                AccountData.remove_order(matched_api_order_dict['id'])
            else: #order still active
                AccountData.update_order(
                    order_id = matched_api_order_dict['id'],
                    executed_qty = matched_api_order_dict['executed_qty'],
                )

        def __process_exit_and_opposite_entry(matched_api_order_dict, matched_holding_df):
            print('Exit and opposite entry execution: ', matched_api_order_dict['ex_name'], ':', matched_api_order_dict['symbol'], '-', matched_api_order_dict['side'], ' x ', matched_api_order_dict['executed_qty'], ' @ ', matched_api_order_dict['avg_price'], )
            realized_pnl = __calc_realized_pnl(matched_holding_df['ex_name'].iloc[0], matched_holding_df['base_asset'].iloc[0], matched_holding_df['quote_asset'].iloc[0], matched_holding_df['qty'].iloc[0], matched_api_order_dict['avg_price'], matched_holding_df)
            AccountData.set_realized_pnls(matched_holding_df['ex_name'].iloc[0], matched_holding_df['base_asset'].iloc[0], matched_holding_df['quote_asset'].iloc[0], realized_pnl)
            new_holding_qty = matched_api_order_dict['executed_qty'] - matched_holding_df['qty'].iloc[0]
            AccountData.remove_holding(matched_holding_df['ex_name'].iloc[0], matched_holding_df['base_asset'].iloc[0], matched_holding_df['quote_asset'].iloc[0])
            AccountData.add_holding(
                ex_name = matched_api_order_dict['ex_name'],
                base_asset=matched_api_order_dict['base_asset'],
                quote_asset=matched_api_order_dict['quote_asset'],
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

        orders = AccountData.get_order_df()
        for index, account_order in orders.iterrows():
            matched_api_order_df = api_orders_df[api_orders_df['id']==account_order['id']] #約定確認したいorder_idに一致するAPIで取得したorder data
            #if __check_okx_order_cancel(matched_api_order_df, account_order):
            if __check_order_matching(matched_api_order_df, account_order):
                if account_order['type'] == 'limit':
                    if __check_exec_qty_validation(matched_api_order_df, account_order) > 0: #約定あり
                        matched_api_order_dict = matched_api_order_df.to_dict(orient='records')[-1]
                        additional_exec_qty = matched_api_order_dict['executed_qty'] -  account_order['executed_qty']
                        holding_data_df = AccountData.get_holding_df()
                        matched_holding_data_df = pd.DataFrame()
                        if len(holding_data_df) > 0:
                            matched_holding_data_df = holding_data_df[(holding_data_df['ex_name']==matched_api_order_dict['ex_name']) & (holding_data_df['base_asset']==matched_api_order_dict['base_asset']) & (holding_data_df['quote_asset']==matched_api_order_dict['quote_asset'])]
                        new_fee = __calc_fee(matched_api_order_dict['ex_name'], matched_api_order_dict['base_asset'], matched_api_order_dict['quote_asset'], matched_api_order_dict['fee'], matched_api_order_dict['fee_currency'], matched_api_order_df['price'])
                        AccountData.set_total_fees(matched_api_order_dict['ex_name'], matched_api_order_dict['base_asset'], matched_api_order_dict['quote_asset'], new_fee)
                        order_side = {'buy':'long', 'sell':'short'}[matched_api_order_dict['side']] #to convert buy/sell to long/short to compare with holding side
                        if len(matched_holding_data_df) == 0: #new execution
                            __process_new_execution(matched_api_order_dict)
                        elif len(matched_holding_data_df) == 1 and order_side == matched_holding_data_df['side'].iloc[-1]: #additional execution
                            __process_additional_execution(matched_api_order_dict, matched_holding_data_df, additional_exec_qty)
                        elif len(matched_holding_data_df) == 1 and order_side != matched_holding_data_df['side'].iloc[-1]: #opposite execution
                            if matched_holding_data_df['qty'].iloc[-1] > matched_api_order_dict['executed_qty']: #partial exit
                                __process_partial_exit_execution(matched_api_order_dict, matched_holding_data_df, additional_exec_qty)
                            elif matched_holding_data_df['qty'].iloc[-1] == matched_api_order_dict['executed_qty']: #full exit
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
                            matched_api_order_dict = matched_api_order_df.to_dict(orient='records')[-1]
                            order_side = {'buy':'long', 'sell':'short'}[matched_api_order_dict['side']] #to convert buy/sell to long/short to compare with holding side
                            additional_exec_qty = matched_api_order_dict['executed_qty'] -  account_order['executed_qty']
                            holding_data_df = AccountData.get_holding_df()
                            matched_holding_data_df = pd.DataFrame()
                            if len(holding_data_df) > 0:
                                matched_holding_data_df = holding_data_df[(holding_data_df['ex_name']==matched_api_order_dict['ex_name']) & (holding_data_df['base_asset']==matched_api_order_dict['base_asset']) & (holding_data_df['quote_asset']==matched_api_order_dict['quote_asset'])]
                            new_fee = __calc_fee(matched_api_order_dict['ex_name'], matched_api_order_dict['base_asset'], matched_api_order_dict['quote_asset'], matched_api_order_dict['fee'], matched_api_order_dict['fee_currency'], matched_api_order_df['price'])
                            AccountData.set_total_fees(matched_api_order_dict['ex_name'], matched_api_order_dict['base_asset'], matched_api_order_dict['quote_asset'], new_fee)
                            if len(matched_holding_data_df) == 0: #new execution
                                __process_new_execution(matched_api_order_dict)
                            elif len(matched_holding_data_df) == 1 and order_side == matched_holding_data_df['side'].iloc[-1]: #additional execution
                                __process_additional_execution(matched_api_order_dict, matched_holding_data_df, additional_exec_qty)
                            elif len(matched_holding_data_df) == 1 and order_side != matched_holding_data_df['side'].iloc[-1]: #opposite execution
                                if matched_holding_data_df['qty'].iloc[-1] > matched_api_order_dict['executed_qty']: #partial exit
                                    __process_partial_exit_execution(matched_api_order_dict, matched_holding_data_df, additional_exec_qty)
                                elif matched_holding_data_df['qty'].iloc[-1] == matched_api_order_dict['executed_qty']: #full exit
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
            matched_position_df = curernt_position_df[(curernt_position_df['ex_name'] == row['ex_name']) & (curernt_position_df['base_asset'] == row['base_asset']) & (curernt_position_df['quote_asset'] == row['quote_asset'])]
            if len(matched_position_df) == 0: #AccountDataにあるholdingが実際には存在しない
                DisplayMessage.display_message('AccountUpdater', '__check_positions', 'error', ['No matched holding is not found!',row])
            else:#check positon data of matched data
                if matched_position_df['side'].iloc[0].lower() != row['side']:
                    DisplayMessage.display_message('AccountUpdater', '__check_positions', 'error', 
                                                   ['Holding side is not matched in '+row['ex_name']+ '-'+ row['symbol']+' with API data !',
                                                   matched_position_df['side'].iloc[0],
                                                   row])
                if abs(matched_position_df['price'].iloc[0] - row['price']) >= 0.1 * row['price']:
                    DisplayMessage.display_message('AccountUpdater', '__check_positions', 'error', ['Holding price is not matched in '+ row['ex_name']+ '-'+ row['symbol']+ ' with API data !',
                                                                                                    matched_position_df['price'].iloc[0],
                                                                                                    row])
                AccountData.update_holding(
                    ex_name=matched_position_df['ex_name'].iloc[0],
                    base_asset=matched_position_df['base_asset'].iloc[0],
                    quote_asset=matched_position_df['quote_asset'].iloc[0],
                    price=float(matched_position_df['price'].iloc[0]),
                    qty=float(abs(matched_position_df['qty'].iloc[0])),
                    unrealized_pnl_usd=float(matched_position_df['unrealized_pnl_usd'].iloc[0]),
                    unrealized_pnl_ratio=float(matched_position_df['unrealized_pnl_ratio'].iloc[0]),
                    liquidation_price=float(matched_position_df['liquidation_price'].iloc[0]),
                    margin_ratio=float(matched_position_df['margin_ratio'].iloc[0])
                )


    async def __sync_holding_data(self, curernt_position_df):
        holding_df = AccountData.get_holding_df()
        for index, holding in holding_df.iterrows():
            matched_current_position_df = curernt_position_df[(curernt_position_df['ex_name'] == holding['ex_name']) & (curernt_position_df['base_asset'] == holding['base_asset']) & (curernt_position_df['quote_asset'] == holding['quote_asset'])]
            if len(matched_current_position_df) == 1:
                matched_current_position_dict = matched_current_position_df.to_dict(orient='records')[0]
                AccountData.update_holding(
                    ex_name=matched_current_position_dict['ex_name'],
                    base_asset=matched_current_position_dict['base_asset'],
                    quote_asset=matched_current_position_dict['quote_asset'],
                    side = matched_current_position_dict['side'],
                    price=matched_current_position_dict['price'],
                    qty=matched_current_position_dict['qty'],
                    timestamp=matched_current_position_dict['timestamp'],
                    period=int(float(time.time()) - float(matched_current_position_dict['timestamp'])/1000.0),
                    unrealized_pnl_usd=matched_current_position_dict['unrealized_pnl_usd'],
                    unrealized_pnl_ratio=matched_current_position_dict['unrealized_pnl_ratio'],
                    liquidation_price=matched_current_position_dict['liquidation_price'],
                    margin_ratio=matched_current_position_dict['margin_ratio']
                )
            else:#executionをチェックした直後に全約定して該当のholdingがなくなることがあるので、対象のorderにのみ約定チェックを行う。
                order_df = AccountData.get_order_df()
                matched_order_df = order_df[(order_df['ex_name'] == holding['ex_name']) & (order_df['base_asset']==holding['base_asset']) & (order_df['quote_asset']==holding['quote_asset'])]
                if len(matched_order_df) > 0:
                    res = await self.__check_execution_of_specific_order(holding['ex_name'], holding['symbol'], matched_order_df['id'].iloc(0))
                    if res == None: #order dataが存在しない
                        DisplayMessage.display_message('AccountUpdater','__sync_holding_data','error',['Holding data is not found in CEX and order!', holding, order_df])
                else:#matchするorderがAccountDataにない。
                    DisplayMessage.display_message('AccountUpdater', '__sync_holding_data', 'error', 
                                                   ['Holding is not found in AccountData !',
                                                    'Account holding',
                                                    holding,
                                                    'Account order',
                                                    order_df,
                                                    'matched current position df',
                                                    matched_current_position_df])
        print('Completed sync all holdings.')


    def __sync_order_data(self, current_order_df):
        order_df = AccountData.get_order_df()
        for index, order in order_df.iterrows():
            matched_current_order_df = current_order_df[current_order_df['id'] == order['id']]
            if len(matched_current_order_df) == 1:
                matched_current_order_dict = matched_current_order_df.to_dict(orient='records')[0]
                AccountData.update_order(
                    order_id=matched_current_order_dict['id'],
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
                DisplayMessage.display_message('AccountUpdater','__sync_order_data', 'error',
                                               ['matched order data size is '+ str(len(matched_current_order_df))+' not 1 !',
                                                'matched_current_order_df',
                                                matched_current_order_df,
                                                'AccountData.order_df',
                                                order])


    '''
    get specific order and check execution
    '''
    async def __check_execution_of_specific_order(self, ex_name, symbol, order_id):
        order = await self.crp.fetch_order(ex_name=ex_name, symbol=symbol, order_id=order_id)
        if 'status' in order:
            order_df = pd.DataFrame()
            if ex_name == 'binance':
                trades = await self.crp.get_trades('binance')
                order_df = CCXTRestApiParser.parse_fetch_order_binance(order, trades)
            elif ex_name == 'bybit':
                order_df = CCXTRestApiParser.parse_fetch_order_bybit(order)
            elif ex_name == 'okx':
                order_df = CCXTRestApiParser.parse_fetch_order_okx(order)
            if len(order_df) > 0:
                self.__check_executions(order_df)
                return order_df
            else:
                DisplayMessage.display_message('AccountUpdater','__check_execution_of_specific_order','error',
                                               ['Order length is zero!',
                                                ex_name +'-'+ symbol +'-'+ str(order_id),
                                                order])
                return None
        else:
            DisplayMessage.display_message('AccountUpdater','__check_execution_of_specific_order','error',
                                               ['Order not found!',
                                                ex_name +'-'+ symbol +'-'+ str(order_id),
                                                order])
            return None



    async def __update_free_cash(self):
        balance_df = await self.__get_account_balance(Settings.exchanges)
        usdt_balance = balance_df.loc[balance_df['asset'] == 'USDT', 'balance'].sum()
        AccountData.set_total_cash(usdt_balance)


    def __update_unrealized_pnl(self):
        holding_df = AccountData.get_holding_df()
        AccountData.set_total_unrealized_pnl(sum(list(holding_df['unrealized_pnl_usd'])))

    def __update_total_pnl(self):
        total_pnl = AccountData.get_total_realized_pnl() + AccountData.get_total_unrealized_pnl() - AccountData.get_total_fee()
        AccountData.set_total_pnl(total_pnl)
        AccountData.add_total_pnl_log(total_pnl)

    def __update_total_amount(self):
        holding_df = AccountData.get_holding_df()
        amount = 0
        if len(holding_df) > 0:
            amount = (holding_df['price'] * holding_df['qty'].abs()).sum()
        AccountData.set_total_amount(amount)

        


        

        



