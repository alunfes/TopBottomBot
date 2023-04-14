import pandas as pd

class CCXTRestApiParser:
    @classmethod
    def initialize(cls):
        pass



    @classmethod
    def parse_get_all_orders_general(cls, ex_name, all_orders):
        """
        id, symbol, status, price, side, original_qty, executed_qty, timestamp, feeからなる
        dataframeを生成する関数
        
        Parameters:
            data (list): 取引データのリスト
        
        Returns:
                    id              symbol    status        price  side  ...  executed_qty  ts       fee  fee_currency ex_name
        0   be571b83-4e68-4510-858f-e34136dcc53e       ETH/USDT:USDT  canceled   984.100000   buy  ...           0.0 NaN  0.000000          USDT   bybit
        1   0a2ca8a0-9e07-49f2-8a37-93ecfdf9b066       ETH/USDT:USDT  canceled   979.400000   buy  ...           0.0 NaN  0.000000          USDT   bybit
        2   9eb7a71c-ad5b-4bd5-b931-fcc9c21b5f3e       ETH/USDT:USDT    closed  1001.750000   buy  ...         150.0 NaN  0.000000          USDT   bybit
        3   1e76f240-ebac-42d1-951f-7a4115b9509b       ETH/USDT:USDT  canceled  1031.800000  sell  ...           0.0 NaN  0.000000          USDT   bybit
        4   b9d576bc-2a99-4fb9-9abb-cad216f74315       ETH/USDT:USDT    closed  1043.000000   buy  ...         300.0 NaN  0.000000          USDT   bybit
        5   f5534c8c-8886-4e14-8f84-1f73e5cc68e3       ETH/USDT:USDT    closed  1062.500000  sell  ...         300.0 NaN  0.000000          USDT   bybit
        6   802aea43-e592-4260-a2ad-bd3aa895ef97       ETH/USDT:USDT    closed  1117.000000  sell  ...         150.0 NaN  0.000000          USDT   bybit
        7   bdd2e06d-e012-4619-bb3b-931cf9820023       ETH/USDT:USDT    closed  1103.000000   buy  ...         300.0 NaN  0.000000          USDT   bybit
        8   4f2fac31-6942-4d3e-9058-4cebd69d09ff       ETH/USDT:USDT    closed  1129.000000  sell  ...         150.0 NaN  0.000000          USDT   bybit
        9   f6e5e19a-e5be-41d1-9514-4ef3e544f15f       ETH/USDT:USDT  canceled   912.000000   buy  ...           0.0 NaN  0.000000          USDT   bybit
        10  92b51dc0-1cf3-43a6-89e5-5fce8d304ce3  SHIB1000/USDT:USDT    closed     0.045270   buy  ...      200000.0 NaN -2.263500          USDT   bybit
        11  a09a9b50-fe14-44d7-82db-f6aa975ece52  SHIB1000/USDT:USDT  canceled     0.048000  sell  ...           0.0 NaN  0.000000          USDT   bybit
        12  5d003ff2-4dc2-4e81-b635-a01e50f1711e  SHIB1000/USDT:USDT    closed     0.041235  sell  ...      200000.0 NaN  6.049500          USDT   bybit
        13  6dd7b512-5516-4383-85e1-66a31bc6e410       BSW/USDT:USDT  canceled     0.170000   buy  ...           0.0 NaN  0.000000          USDT   bybit
        14  e72e621c-e09a-4dc8-96a7-6e892879d290       BSW/USDT:USDT  canceled     0.170000   buy  ...           0.0 NaN  0.000000          USDT   bybit
        15  0c5cd103-df4c-4e44-844f-a7c12d722f7f       BSW/USDT:USDT  canceled     0.160000   buy  ...           0.0 NaN  0.000000          USDT   bybit
        16  60264d64-e12d-4d51-9a41-6c9ba9e5dfc8       BSW/USDT:USDT  canceled     0.170000   buy  ...           0.0 NaN  0.000000          USDT   bybit
        17  b1a18135-5982-4758-ada4-58026d1a2c8a        OP/USDT:USDT    closed     2.110400  sell  ...           1.0 NaN  0.001332          USDT   bybit
        18  df153856-c4eb-464d-a6d8-a0c90b71ffd8        OP/USDT:USDT    closed     2.219300   buy  ...           1.0 NaN  0.000222          USDT   bybit
        19  f8c8e4f8-8080-4c76-b0b7-9137e830f169        OP/USDT:USDT      open     2.000000   buy  ...           0.0 NaN  0.000000          USDT   bybit
        """
        
        # リストから必要な情報を取り出して辞書型のリストを作成する
        orders = []
        for d in all_orders:
            order = {'id': d['id'], 'symbol': d['symbol'], 'status': d['status'], 'price': d['price'], 'type':d['type'],
                    'side': d['side'], 'original_qty': d['amount'], 'executed_qty': d['filled'],
                    'timestamp': pd.to_datetime(d['timestamp'], unit='ms'), 'fee': d['fee']['cost'], 'fee_currency': d['fee']['currency']}
            orders.append(order)
        
        # 辞書型のリストからdataframeを作成する
        df = pd.DataFrame(orders, columns=['id', 'symbol', 'status', 'price', 'side', 'type',
                                        'original_qty', 'executed_qty', 'ts', 'fee', 'fee_currency'])
        df['ex_name'] = [ex_name] * len(df)
        return df
    

    @classmethod
    def parse_get_all_orders_okx(cls, open_orders, closed_orders):
        '''
                        id         symbol  status    price  side  original_qty  executed_qty      timestamp      fee fee_currency ex_name
        0  566288611784986625      DOGE/USDT  closed  0.08185   buy          10.0          10.0  1681285726183  0.00800         DOGE     okx
        1  566291942305632275      DOGE/USDT  closed  0.08200  sell          10.0          10.0  1681286520241  0.00082         USDT     okx
        2  566646923047145473  DOT/USDT:USDT    open  6.00000   buy           1.0           0.0  1681371154245  0.00000         USDT     okx
        '''
        # closed_ordersからDataFrameを作成
        processed_data = []
        for item in closed_orders:
            id = item['id']
            symbol = item['symbol']
            status = item['status']
            price = item['price']
            side = item['side']
            otype = item['type']
            original_qty = item['amount']
            executed_qty = item['filled']
            timestamp = item['timestamp']
            fee = item['fee']['cost']
            fee_currency = item['fee']['currency']
            processed_data.append([id, symbol, status, price, side, otype, original_qty, executed_qty, timestamp, fee, fee_currency])
        columns = ['id', 'symbol', 'status', 'price', 'side', 'type', 'original_qty', 'executed_qty', 'timestamp', 'fee', 'fee_currency']
        closed_orders_df = pd.DataFrame(processed_data, columns=columns)
        closed_orders_df['ex_name'] = ['okx'] * len(closed_orders_df)
        # open_ordersからDataFrameを作成
        processed_data = []
        for item in open_orders:
            id = item['id']
            symbol = item['symbol']
            status = item['status']
            price = item['price']
            side = item['side']
            otype = item['type']
            original_qty = item['amount']
            executed_qty = item['filled']
            timestamp = item['timestamp']
            fee = item['fee']['cost']
            fee_currency = item['fee']['currency']
            processed_data.append([id, symbol, status, price, side, otype, original_qty, executed_qty, timestamp, fee, fee_currency])
        columns = ['id', 'symbol', 'status', 'price', 'side', 'type', 'original_qty', 'executed_qty', 'timestamp', 'fee', 'fee_currency']
        open_orders_df = pd.DataFrame(processed_data, columns=columns)
        open_orders_df['ex_name'] = ['okx'] * len(open_orders_df)
        return pd.concat([closed_orders_df, open_orders_df], ignore_index=True)


    @classmethod
    def parse_get_all_orders_binance(cls, all_orders, binace_trades):
        '''
        id     symbol    status    price  side original_qty executed_qty             ts       fee fee_currency  ex_name
        0  4695008235  ALICEUSDT  CANCELED    1.780  SELL           10            0  1681256671435  0.000000               binance
        1  4695044324  ALICEUSDT  CANCELED    1.750  SELL           10            0  1681258340605  0.000000               binance
        2  4695181725  ALICEUSDT  CANCELED        1   BUY           10            0  1681263917931  0.000000               binance
        3  4695200291  ALICEUSDT  CANCELED        1   BUY           10            0  1681264352569  0.000000               binance
        4  4695221183  ALICEUSDT  CANCELED        1   BUY           10            0  1681264940381  0.000000               binance
        5  9446494975    TRXUSDT    FILLED        0  SELL          100          100  1681288077482  0.002552         USDT  binance
        6  9452120962    TRXUSDT       NEW  0.05700   BUY          100            0  1681345141176  0.000000               binance
        '''
        order_df = pd.DataFrame(all_orders)
        trade_df = pd.DataFrame(binace_trades)
        order_cols = ['orderId', 'symbol', 'status', 'price', 'side', 'type', 'origQty', 'executedQty', 'time']
        order_df = pd.DataFrame(order_df, columns=order_cols)
        fees = []
        fee_currency = []
        for i in range(len(order_df)):
            if order_df['orderId'].iloc[i] in list(trade_df['orderId']):
                commision = trade_df.loc[trade_df['orderId'] == order_df['orderId'].iloc[i], 'commission'].item()
                currency = trade_df.loc[trade_df['orderId'] == order_df['orderId'].iloc[i], 'commissionAsset'].item()
                fees.append(float(commision))
                fee_currency.append(currency)
            else:
                fees.append(0)
                fee_currency.append('')
        order_df['fee'] = fees
        order_df['fee_currency'] = fee_currency
        order_df['ex_name'] = ['binance'] * len(order_df)
        order_df.rename(columns={'orderId': 'id', 'origQty': 'original_qty', 'executedQty': 'executed_qty', 'time': 'ts'}, inplace=True)
        return order_df



    



