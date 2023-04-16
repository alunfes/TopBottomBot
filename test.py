from CCXTRestApiParser import CCXTRestApiParser
from CCXTRestApi import CCXTRestApi
from Settings import Settings
from AccountData import AccountData

import asyncio
import pandas as pd

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
    async def main(self):
        test = Test()
        await asyncio.gather(
            test.start()
        )
    

if __name__ == '__main__':
   #tm = TestMain()
   #asyncio.run(tm.main())
   test = Test()
   po = asyncio.run(test.crp.fetch_positions('okx'))
   df = CCXTRestApiParser.parse_fetch_holding_position_okx(po)
   print(df)
    