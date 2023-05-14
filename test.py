from CCXTRestApiParser import CCXTRestApiParser
from CCXTRestApi import CCXTRestApi
from Settings import Settings
from AccountData import AccountData
from AccountUpdater import AccountUpdater
from Flags import Flags
from TargetSymbolsData import TargetSymbolsData
from TargetSymbolsDataInjector import TargetSymbolsDataInjector
from Communication import Communication
from CommunicationData import CommunicationData
from ActionData import ActionData
from Strategy import Strategy
from DisplayMessage import DisplayMessage


import asyncio
import pandas as pd
import time

class Test:
    def __init__(self):
        CCXTRestApiParser.initialize()
        self.crp = CCXTRestApi()
        self.loop = asyncio.get_event_loop()
        AccountData.initialize()

    async def start(self):
        orders = await self.crp.get_all_orders('bybit')
        bybit = CCXTRestApiParser.parse_get_all_orders_general('bybit', orders)
        biorders = await self.crp.get_all_orders('binance')
        bitrades = await self.get_binance_all_trades()
        binance = CCXTRestApiParser.parse_get_all_orders_binance(all_orders=biorders, binace_trades=bitrades)
        okorders = await self.crp.get_all_orders('okx')
        okx = CCXTRestApiParser.parse_get_all_orders_okx(open_orders=okorders['open_orders'], closed_orders=okorders['closed_orders'])
        
        con_df = pd.concat([bybit, binance, okx], ignore_index=True)
        print(con_df)
        self.add_account_data(con_df.iloc[10:12])
        print(AccountData.get_order_df())
        self.check_executions(con_df)


    async def get_all_orders(self, ex_name):
        return await self.crp.get_all_orders(ex_name)
    
    async def get_binance_all_trades(self):
        return await self.crp.binance_get_trades()

    def add_account_data(self, df):
        for index, row in df.iterrows():
            AccountData.add_order(row['ex_name'], row['id'], row['symbol'], row['side'], row['type'], row['price'], 'NEW', row['original_qty'],
                                  row['executed_qty'], row['fee'], row['fee_currency'], row['ts'])

    def check_executions(self, latest_order_df):
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


class TestMain:
    def __init__(self):
        Flags.initialize()
        Settings.initialize()
        TargetSymbolsData.initialize()
        self.crp = CCXTRestApi()
        self.crp.initialize()

        #tsdi = TargetSymbolsDataInjector(self.crp, 1000000.0)
        #tsdi.inject_target_data()
        #tsdi.inject_ohlcv_data(14)
        #tsdi.read_target_tickers()
        #tsdi.read_all_ohlcv()
    
    '''
    botでorder出す時は、ex_name, base assetが一致するtarget_dfのデータのsymbolを使うべき
    '''
    def __generate_test_action_data(self):
        ad = ActionData()
        ad.add_action(action='buy', order_id='', ex_name='binance', symbol='GTCUSDT', base_asset='GTC', quote_asset='USDT', order_type='market', price=0, qty=5)
        #ad.add_action(action='buy', order_id='', ex_name='binance', symbol='CELRUSDT', base_asset='CERL', quote_asset='USDT',order_type='limit', price=0, qty=230)
        #ad.add_action(action='sell', order_id='', ex_name='okx', symbol='CSPR-USDT-SWAP', base_asset='CSPR', quote_asset='USDT',order_type='limit', price=0, qty=90)
        #ad.add_action(action='sell', order_id='', ex_name='bybit', symbol='COREUSDT', base_asset='CORE', quote_asset='USDT',order_type='limit', price=0, qty=2)
        return ad.get_action()

    def __generate_test_exit_action_data(self):
        ad = ActionData()
        order_df = AccountData.get_order_df()
        holding_df = AccountData.get_holding_df()
        for index, order in order_df.iterrows():
            ad.add_action(action='cancel', order_id=order['id'], ex_name=order['ex_name'], symbol=order['symbol'], base_asset=order['base_asset'], quote_asset=order['quote_asset'], order_type='', price=0, qty=0)
        for index, holding in holding_df.iterrows():
            ad.add_action(action='buy' if holding['side']=='short' else 'sell', order_id='', ex_name=holding['ex_name'], symbol=holding['symbol'], base_asset=holding['base_asset'], quote_asset=holding['quote_asset'], order_type='limit', price=0, qty=holding['qty'])
        return ad.get_action()

    async def bot(self):
        actions = self.__generate_test_action_data()
        strategy = Strategy(self.crp)
        pt_ratio = 0.01
        lc_ratio = -0.01
        action_data = await strategy.get_actions(pt_ratio, lc_ratio)
        for action in action_data.actions:
            if action['action'] == 'buy' or action['action'] == 'sell':
                res = await self.crp.send_order(
                        ex_name=action['ex_name'],
                        symbol=action['symbol'],
                        order_type=action['order_type'],
                        side=action['action'],
                        price=action['price'],
                        amount=action['qty']
                    )
                if 'status' in res:
                    AccountData.add_order(action['ex_name'],res['orderId'],action['symbol'],action['base_asset'],action['quote_asset'],
                                          action['action'], action['order_type'], action['price'],
                                          0,res['status'],action['qty'],0,0,'',time.time())
            elif action['action'] == 'cancel':
                res = await self.crp.cancel_order(
                    ex_name=action['ex_name'],
                    symbol=action['symbol'],
                    order_id=action['id'],
                )
                if 'status' in res:
                    pass


        holding = AccountData.get_holding_df()
        order = AccountData.get_order_df()
        print('Holding:')
        print(holding[['ex_name', 'symbol', 'side', 'price', 'qty', 'unrealized_pnl_usd']])
        print('Order:')
        print(order[['ex_name', 'symbol', 'side', 'avg_price', 'original_qty']])
        await asyncio.sleep(60)


    async def main(self):
        ccxt_api = CCXTRestApi()
        account = AccountUpdater(ccxt_api)
        communication = Communication()
        await asyncio.gather(
            account.start_update(),
            self.bot(),
            communication.main_loop(),
        )


class TestComm:
    def __init__(self):
        self.communication = Communication()
    
    async def main(self):
        await asyncio.gather(
            self.communication.main_loop(),
        )

class TestStrategy:
    def __init__(self):
        Settings.initialize()
        crp = CCXTRestApi()
        TargetSymbolsData.initialize()
        tsdi = TargetSymbolsDataInjector(crp, 1000000.0)
        #tsdi.inject_target_data()
        #tsdi.inject_ohlcv_data(14)
        tsdi.read_target_tickers()
        tsdi.read_all_ohlcv()
        strategy = Strategy(crp)
        strategy.calc_change_ratio()
        strategy.detect_top_bottom_targets()
        strategy.calc_lot()
        
    

if __name__ == '__main__':
    #ts = TestStrategy()
    #tc = TestComm()
    #asyncio.run(tc.main())
    tm = TestMain()
    asyncio.run(tm.main())
    #test = Test()
    #po = asyncio.run(test.crp.fetch_positions('okx'))
    #df = CCXTRestApiParser.parse_fetch_holding_position_okx(po)
    #print(df)
    