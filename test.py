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
   tm = TestMain()
   asyncio.run(tm.main())
    


'''
[{'info': {'orderId': 'be571b83-4e68-4510-858f-e34136dcc53e', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'ETHUSDT', 'price': '984.10', 'qty': '150.00', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '1', 'orderStatus': 'Cancelled', 'cancelType': 'CancelByUser', 'rejectReason': 'EC_NoError', 'avgPrice': '0', 'leavesQty': '0.00', 'leavesValue': '0', 'cumExecQty': '0.00', 'cumExecValue': '0', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.00', 'takeProfit': '0.00', 'stopLoss': '0.00', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '984.40', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1609729440756', 'updatedTime': '1609729536969', 'placeType': ''}, 'id': 'be571b83-4e68-4510-858f-e34136dcc53e', 'clientOrderId': None, 'timestamp': 1609729440756, 'datetime': '2021-01-04T03:04:00.756Z', 'lastTradeTimestamp': 1609729536969, 'symbol': 'ETH/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 984.1, 'stopPrice': None, 'triggerPrice': None, 'amount': 150.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 0.0, 'status': 'canceled', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': '0a2ca8a0-9e07-49f2-8a37-93ecfdf9b066', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'ETHUSDT', 'price': '979.40', 'qty': '150.00', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '1', 'orderStatus': 'Cancelled', 'cancelType': 'CancelByUser', 'rejectReason': 'EC_NoError', 'avgPrice': '0', 'leavesQty': '0.00', 'leavesValue': '0', 'cumExecQty': '0.00', 'cumExecValue': '0', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.00', 'takeProfit': '0.00', 'stopLoss': '0.00', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '984.70', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1609729569888', 'updatedTime': '1609732045797', 'placeType': ''}, 'id': '0a2ca8a0-9e07-49f2-8a37-93ecfdf9b066', 'clientOrderId': None, 'timestamp': 1609729569888, 'datetime': '2021-01-04T03:06:09.888Z', 'lastTradeTimestamp': 1609732045797, 'symbol': 'ETH/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 979.4, 'stopPrice': None, 'triggerPrice': None, 'amount': 150.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 0.0, 'status': 'canceled', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': '9eb7a71c-ad5b-4bd5-b931-fcc9c21b5f3e', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'ETHUSDT', 'price': '1001.75', 'qty': '150.00', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '1', 'orderStatus': 'Filled', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '1001.750', 'leavesQty': '0.00', 'leavesValue': '0', 'cumExecQty': '150.00', 'cumExecValue': '150262.5', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.00', 'takeProfit': '0.00', 'stopLoss': '0.00', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '1001.80', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1609731616717', 'updatedTime': '1609731637517', 'placeType': ''}, 'id': '9eb7a71c-ad5b-4bd5-b931-fcc9c21b5f3e', 'clientOrderId': None, 'timestamp': 1609731616717, 'datetime': '2021-01-04T03:40:16.717Z', 'lastTradeTimestamp': 1609731637517, 'symbol': 'ETH/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 1001.75, 'stopPrice': None, 'triggerPrice': None, 'amount': 150.0, 'cost': 150262.5, 'average': 1001.75, 'filled': 150.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': '1e76f240-ebac-42d1-951f-7a4115b9509b', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'ETHUSDT', 'price': '1031.80', 'qty': '300.00', 'side': 'Sell', 'isLeverage': '', 'positionIdx': '2', 'orderStatus': 'Cancelled', 'cancelType': 'CancelByUser', 'rejectReason': 'EC_NoError', 'avgPrice': '0', 'leavesQty': '0.00', 'leavesValue': '0', 'cumExecQty': '0.00', 'cumExecValue': '0', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.00', 'takeProfit': '0.00', 'stopLoss': '0.00', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '1025.05', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1609735061190', 'updatedTime': '1609735827101', 'placeType': ''}, 'id': '1e76f240-ebac-42d1-951f-7a4115b9509b', 'clientOrderId': None, 'timestamp': 1609735061190, 'datetime': '2021-01-04T04:37:41.190Z', 'lastTradeTimestamp': 1609735827101, 'symbol': 'ETH/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'sell', 'price': 1031.8, 'stopPrice': None, 'triggerPrice': None, 'amount': 300.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 0.0, 'status': 'canceled', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': 'b9d576bc-2a99-4fb9-9abb-cad216f74315', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'ETHUSDT', 'price': '1043.00', 'qty': '300.00', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '2', 'orderStatus': 'Filled', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '1042.98331', 'leavesQty': '0.00', 'leavesValue': '0', 'cumExecQty': '300.00', 'cumExecValue': '312894.994', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.00', 'takeProfit': '0.00', 'stopLoss': '0.00', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '1043.35', 'reduceOnly': True, 'closeOnTrigger': True, 'createdTime': '1609737449082', 'updatedTime': '1609737450896', 'placeType': ''}, 'id': 'b9d576bc-2a99-4fb9-9abb-cad216f74315', 'clientOrderId': None, 'timestamp': 1609737449082, 'datetime': '2021-01-04T05:17:29.082Z', 'lastTradeTimestamp': 1609737450896, 'symbol': 'ETH/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': True, 'side': 'buy', 'price': 1043.0, 'stopPrice': None, 'triggerPrice': None, 'amount': 300.0, 'cost': 312894.994, 'average': 1042.9833133333334, 'filled': 300.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': 'f5534c8c-8886-4e14-8f84-1f73e5cc68e3', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'ETHUSDT', 'price': '1062.50', 'qty': '300.00', 'side': 'Sell', 'isLeverage': '', 'positionIdx': '1', 'orderStatus': 'Filled', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '1062.50', 'leavesQty': '0.00', 'leavesValue': '0', 'cumExecQty': '300.00', 'cumExecValue': '318750', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.00', 'takeProfit': '0.00', 'stopLoss': '0.00', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '1055.35', 'reduceOnly': True, 'closeOnTrigger': True, 'createdTime': '1609737823074', 'updatedTime': '1609738162607', 'placeType': ''}, 'id': 'f5534c8c-8886-4e14-8f84-1f73e5cc68e3', 'clientOrderId': None, 'timestamp': 1609737823074, 'datetime': '2021-01-04T05:23:43.074Z', 'lastTradeTimestamp': 1609738162607, 'symbol': 'ETH/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': True, 'side': 'sell', 'price': 1062.5, 'stopPrice': None, 'triggerPrice': None, 'amount': 300.0, 'cost': 318750.0, 'average': 1062.5, 'filled': 300.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': '802aea43-e592-4260-a2ad-bd3aa895ef97', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'ETHUSDT', 'price': '1117.00', 'qty': '150.00', 'side': 'Sell', 'isLeverage': '', 'positionIdx': '2', 'orderStatus': 'Filled', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '1117.00', 'leavesQty': '0.00', 'leavesValue': '0', 'cumExecQty': '150.00', 'cumExecValue': '167550', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.00', 'takeProfit': '0.00', 'stopLoss': '0.00', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '1115.00', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1609741358643', 'updatedTime': '1609741360042', 'placeType': ''}, 'id': '802aea43-e592-4260-a2ad-bd3aa895ef97', 'clientOrderId': None, 'timestamp': 1609741358643, 'datetime': '2021-01-04T06:22:38.643Z', 'lastTradeTimestamp': 1609741360042, 'symbol': 'ETH/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'sell', 'price': 1117.0, 'stopPrice': None, 'triggerPrice': None, 'amount': 150.0, 'cost': 167550.0, 'average': 1117.0, 'filled': 150.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': 'bdd2e06d-e012-4619-bb3b-931cf9820023', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'ETHUSDT', 'price': '1103.00', 'qty': '300.00', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '2', 'orderStatus': 'Filled', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '1103.00', 'leavesQty': '0.00', 'leavesValue': '0', 'cumExecQty': '300.00', 'cumExecValue': '330900', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.00', 'takeProfit': '0.00', 'stopLoss': '0.00', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '1113.70', 'reduceOnly': True, 'closeOnTrigger': True, 'createdTime': '1609741417324', 'updatedTime': '1609743454793', 'placeType': ''}, 'id': 'bdd2e06d-e012-4619-bb3b-931cf9820023', 'clientOrderId': None, 'timestamp': 1609741417324, 'datetime': '2021-01-04T06:23:37.324Z', 'lastTradeTimestamp': 1609743454793, 'symbol': 'ETH/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': True, 'side': 'buy', 'price': 1103.0, 'stopPrice': None, 'triggerPrice': None, 'amount': 300.0, 'cost': 330900.0, 'average': 1103.0, 'filled': 300.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': '4f2fac31-6942-4d3e-9058-4cebd69d09ff', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'ETHUSDT', 'price': '1129.00', 'qty': '150.00', 'side': 'Sell', 'isLeverage': '', 'positionIdx': '2', 'orderStatus': 'Filled', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '1129.00', 'leavesQty': '0.00', 'leavesValue': '0', 'cumExecQty': '150.00', 'cumExecValue': '169350', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.00', 'takeProfit': '0.00', 'stopLoss': '0.00', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '1127.50', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1609741514765', 'updatedTime': '1609741567669', 'placeType': ''}, 'id': '4f2fac31-6942-4d3e-9058-4cebd69d09ff', 'clientOrderId': None, 'timestamp': 1609741514765, 'datetime': '2021-01-04T06:25:14.765Z', 'lastTradeTimestamp': 1609741567669, 'symbol': 'ETH/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'sell', 'price': 1129.0, 'stopPrice': None, 'triggerPrice': None, 'amount': 150.0, 'cost': 169350.0, 'average': 1129.0, 'filled': 150.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': 'f6e5e19a-e5be-41d1-9514-4ef3e544f15f', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'ETHUSDT', 'price': '912.00', 'qty': '150.00', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '1', 'orderStatus': 'Cancelled', 'cancelType': 'CancelByUser', 'rejectReason': 'EC_NoError', 'avgPrice': '0', 'leavesQty': '0.00', 'leavesValue': '0', 'cumExecQty': '0.00', 'cumExecValue': '0', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.00', 'takeProfit': '0.00', 'stopLoss': '0.00', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '935.90', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1609753320080', 'updatedTime': '1609753541978', 'placeType': ''}, 'id': 'f6e5e19a-e5be-41d1-9514-4ef3e544f15f', 'clientOrderId': None, 'timestamp': 1609753320080, 'datetime': '2021-01-04T09:42:00.080Z', 'lastTradeTimestamp': 1609753541978, 'symbol': 'ETH/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 912.0, 'stopPrice': None, 'triggerPrice': None, 'amount': 150.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 0.0, 'status': 'canceled', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': '92b51dc0-1cf3-43a6-89e5-5fce8d304ce3', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'SHIB1000USDT', 'price': '0.045270', 'qty': '200000', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '1', 'orderStatus': 'Filled', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '0.045270', 'leavesQty': '0', 'leavesValue': '0', 'cumExecQty': '200000', 'cumExecValue': '9054', 'cumExecFee': '-2.2635', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.000000', 'takeProfit': '0.000000', 'stopLoss': '0.000000', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '0.000000', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1638340273637', 'updatedTime': '1638340286475', 'placeType': ''}, 'id': '92b51dc0-1cf3-43a6-89e5-5fce8d304ce3', 'clientOrderId': None, 'timestamp': 1638340273637, 'datetime': '2021-12-01T06:31:13.637Z', 'lastTradeTimestamp': 1638340286475, 'symbol': 'SHIB1000/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 0.04527, 'stopPrice': None, 'triggerPrice': None, 'amount': 200000.0, 'cost': 9054.0, 'average': 0.04527, 'filled': 200000.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': -2.2635, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': -2.2635, 'currency': 'USDT'}]}, {'info': {'orderId': 'a09a9b50-fe14-44d7-82db-f6aa975ece52', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'SHIB1000USDT', 'price': '0.048000', 'qty': '200000', 'side': 'Sell', 'isLeverage': '', 'positionIdx': '1', 'orderStatus': 'Cancelled', 'cancelType': 'CancelAllBeforeLiq', 'rejectReason': 'EC_PerCancelRequest', 'avgPrice': '0', 'leavesQty': '0', 'leavesValue': '0', 'cumExecQty': '0', 'cumExecValue': '0', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.000000', 'takeProfit': '0.000000', 'stopLoss': '0.000000', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '0.000000', 'reduceOnly': True, 'closeOnTrigger': True, 'createdTime': '1638341761186', 'updatedTime': '1638414601153', 'placeType': ''}, 'id': 'a09a9b50-fe14-44d7-82db-f6aa975ece52', 'clientOrderId': None, 'timestamp': 1638341761186, 'datetime': '2021-12-01T06:56:01.186Z', 'lastTradeTimestamp': 1638414601153, 'symbol': 'SHIB1000/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': True, 'side': 'sell', 'price': 0.048, 'stopPrice': None, 'triggerPrice': None, 'amount': 200000.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 0.0, 'status': 'canceled', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': '5d003ff2-4dc2-4e81-b635-a01e50f1711e', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'SHIB1000USDT', 'price': '0.041235', 'qty': '200000', 'side': 'Sell', 'isLeverage': '', 'positionIdx': '1', 'orderStatus': 'Filled', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '0.040330', 'leavesQty': '0', 'leavesValue': '0', 'cumExecQty': '200000', 'cumExecValue': '8066', 'cumExecFee': '6.0495', 'timeInForce': 'FOK', 'orderType': 'Market', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.041233', 'takeProfit': '0.000000', 'stopLoss': '0.000000', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '0.000000', 'reduceOnly': True, 'closeOnTrigger': True, 'createdTime': '1638414601164', 'updatedTime': '1638414601164', 'placeType': ''}, 'id': '5d003ff2-4dc2-4e81-b635-a01e50f1711e', 'clientOrderId': None, 'timestamp': 1638414601164, 'datetime': '2021-12-02T03:10:01.164Z', 'lastTradeTimestamp': 1638414601164, 'symbol': 'SHIB1000/USDT:USDT', 'type': 'market', 'timeInForce': 'FOK', 'postOnly': False, 'reduceOnly': True, 'side': 'sell', 'price': 0.041235, 'stopPrice': 0.041233, 'triggerPrice': 0.041233, 'amount': 200000.0, 'cost': 8066.0, 'average': 0.04033, 'filled': 200000.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': 6.0495, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 6.0495, 'currency': 'USDT'}]}, {'info': {'orderId': '6dd7b512-5516-4383-85e1-66a31bc6e410', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'BSWUSDT', 'price': '0.1700', 'qty': '100', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '0', 'orderStatus': 'Cancelled', 'cancelType': 'CancelByUser', 'rejectReason': 'EC_PerCancelRequest', 'avgPrice': '0', 'leavesQty': '0', 'leavesValue': '0', 'cumExecQty': '0', 'cumExecValue': '0', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.0000', 'takeProfit': '0.0000', 'stopLoss': '0.0000', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '0.0000', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1681267968520', 'updatedTime': '1681267977944', 'placeType': ''}, 'id': '6dd7b512-5516-4383-85e1-66a31bc6e410', 'clientOrderId': None, 'timestamp': 1681267968520, 'datetime': '2023-04-12T02:52:48.520Z', 'lastTradeTimestamp': 1681267977944, 'symbol': 'BSW/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 0.17, 'stopPrice': None, 'triggerPrice': None, 'amount': 100.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 0.0, 'status': 'canceled', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': 'e72e621c-e09a-4dc8-96a7-6e892879d290', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'BSWUSDT', 'price': '0.1700', 'qty': '100', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '0', 'orderStatus': 'Cancelled', 'cancelType': 'CancelByUser', 'rejectReason': 'EC_PerCancelRequest', 'avgPrice': '0', 'leavesQty': '0', 'leavesValue': '0', 'cumExecQty': '0', 'cumExecValue': '0', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.0000', 'takeProfit': '0.0000', 'stopLoss': '0.0000', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '0.0000', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1681268201148', 'updatedTime': '1681268210717', 'placeType': ''}, 'id': 'e72e621c-e09a-4dc8-96a7-6e892879d290', 'clientOrderId': None, 'timestamp': 1681268201148, 'datetime': '2023-04-12T02:56:41.148Z', 'lastTradeTimestamp': 1681268210717, 'symbol': 'BSW/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 0.17, 'stopPrice': None, 'triggerPrice': None, 'amount': 100.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 0.0, 'status': 'canceled', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': '0c5cd103-df4c-4e44-844f-a7c12d722f7f', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'BSWUSDT', 'price': '0.1600', 'qty': '100', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '0', 'orderStatus': 'Cancelled', 'cancelType': 'CancelByUser', 'rejectReason': 'EC_PerCancelRequest', 'avgPrice': '0', 'leavesQty': '0', 'leavesValue': '0', 'cumExecQty': '0', 'cumExecValue': '0', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.0000', 'takeProfit': '0.0000', 'stopLoss': '0.0000', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '0.0000', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1681280873389', 'updatedTime': '1681282455316', 'placeType': ''}, 'id': '0c5cd103-df4c-4e44-844f-a7c12d722f7f', 'clientOrderId': None, 'timestamp': 1681280873389, 'datetime': '2023-04-12T06:27:53.389Z', 'lastTradeTimestamp': 1681282455316, 'symbol': 'BSW/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 0.16, 'stopPrice': None, 'triggerPrice': None, 'amount': 100.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 0.0, 'status': 'canceled', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': '60264d64-e12d-4d51-9a41-6c9ba9e5dfc8', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'BSWUSDT', 'price': '0.1700', 'qty': '100', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '0', 'orderStatus': 'Cancelled', 'cancelType': 'CancelByUser', 'rejectReason': 'EC_PerCancelRequest', 'avgPrice': '0', 'leavesQty': '0', 'leavesValue': '0', 'cumExecQty': '0', 'cumExecValue': '0', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.0000', 'takeProfit': '0.0000', 'stopLoss': '0.0000', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '0.0000', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1681282771566', 'updatedTime': '1681282857851', 'placeType': ''}, 'id': '60264d64-e12d-4d51-9a41-6c9ba9e5dfc8', 'clientOrderId': None, 'timestamp': 1681282771566, 'datetime': '2023-04-12T06:59:31.566Z', 'lastTradeTimestamp': 1681282857851, 'symbol': 'BSW/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 0.17, 'stopPrice': None, 'triggerPrice': None, 'amount': 100.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 0.0, 'status': 'canceled', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': 'b1a18135-5982-4758-ada4-58026d1a2c8a', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'OPUSDT', 'price': '2.1104', 'qty': '1.0', 'side': 'Sell', 'isLeverage': '', 'positionIdx': '0', 'orderStatus': 'Filled', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '2.220720000', 'leavesQty': '0.0', 'leavesValue': '0', 'cumExecQty': '1.0', 'cumExecValue': '2.22072', 'cumExecFee': '0.00133244', 'timeInForce': 'IOC', 'orderType': 'Market', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.0000', 'takeProfit': '0.0000', 'stopLoss': '0.0000', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '0.0000', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1681285869078', 'updatedTime': '1681285869080', 'placeType': ''}, 'id': 'b1a18135-5982-4758-ada4-58026d1a2c8a', 'clientOrderId': None, 'timestamp': 1681285869078, 'datetime': '2023-04-12T07:51:09.078Z', 'lastTradeTimestamp': 1681285869080, 'symbol': 'OP/USDT:USDT', 'type': 'market', 'timeInForce': 'IOC', 'postOnly': False, 'reduceOnly': False, 'side': 'sell', 'price': 2.1104, 'stopPrice': None, 'triggerPrice': None, 'amount': 1.0, 'cost': 2.22072, 'average': 2.22072, 'filled': 1.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': 0.00133244, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.00133244, 'currency': 'USDT'}]}, {'info': {'orderId': 'df153856-c4eb-464d-a6d8-a0c90b71ffd8', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'OPUSDT', 'price': '2.2193', 'qty': '1.0', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '0', 'orderStatus': 'Filled', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '2.21930000', 'leavesQty': '0.0', 'leavesValue': '0', 'cumExecQty': '1.0', 'cumExecValue': '2.2193', 'cumExecFee': '0.00022193', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.0000', 'takeProfit': '0.0000', 'stopLoss': '0.0000', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '0.0000', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1681286128157', 'updatedTime': '1681287714520', 'placeType': ''}, 'id': 'df153856-c4eb-464d-a6d8-a0c90b71ffd8', 'clientOrderId': None, 'timestamp': 1681286128157, 'datetime': '2023-04-12T07:55:28.157Z', 'lastTradeTimestamp': 1681287714520, 'symbol': 'OP/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 2.2193, 'stopPrice': None, 'triggerPrice': None, 'amount': 1.0, 'cost': 2.2193, 'average': 2.2193, 'filled': 1.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': 0.00022193, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.00022193, 'currency': 'USDT'}]}, {'info': {'orderId': 'f8c8e4f8-8080-4c76-b0b7-9137e830f169', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'OPUSDT', 'price': '2.0000', 'qty': '1.0', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '0', 'orderStatus': 'New', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '0', 'leavesQty': '1.0', 'leavesValue': '2', 'cumExecQty': '0.0', 'cumExecValue': '0', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.0000', 'takeProfit': '0.0000', 'stopLoss': '0.0000', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '0.0000', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1681370337308', 'updatedTime': '1681370337310', 'placeType': ''}, 'id': 'f8c8e4f8-8080-4c76-b0b7-9137e830f169', 'clientOrderId': None, 'timestamp': 1681370337308, 'datetime': '2023-04-13T07:18:57.308Z', 'lastTradeTimestamp': 1681370337310, 'symbol': 'OP/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 2.0, 'stopPrice': None, 'triggerPrice': None, 'amount': 1.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 1.0, 'status': 'open', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}]
'''