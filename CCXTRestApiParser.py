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
            order = {'id': d['id'], 'symbol': d['symbol'], 'status': d['status'], 'price': float(d['price']),'avg_price': float(d['average']), 'type':d['type'],
                    'side': d['side'], 'original_qty': float(d['amount']), 'executed_qty': float(d['filled']),
                    'timestamp': pd.to_datetime(d['timestamp'], unit='ms'), 'fee': float(d['fee']['cost']), 'fee_currency': d['fee']['currency']}
            orders.append(order)
        # 辞書型のリストからdataframeを作成する
        df = pd.DataFrame(orders, columns=['id', 'symbol', 'status', 'price', 'avg_price', 'side', 'type',
                                        'original_qty', 'executed_qty', 'ts', 'fee', 'fee_currency'])
        df['ex_name'] = [ex_name] * len(df)
        return df
    

    @classmethod
    def parse_get_all_orders_okx(cls, open_orders, closed_orders):
        '''
                        id         symbol  status    price  side  original_qty  executed_qty      ts      fee fee_currency ex_name
        0  566288611784986625      DOGE/USDT  closed  0.08185   buy          10.0          10.0  1681285726183  0.00800         DOGE     okx
        1  566291942305632275      DOGE/USDT  closed  0.08200  sell          10.0          10.0  1681286520241  0.00082         USDT     okx
        2  566646923047145473  DOT/USDT:USDT    open  6.00000   buy           1.0           0.0  1681371154245  0.00000         USDT     okx
        '''
        # closed_ordersからDataFrameを作成
        processed_data = []
        for item in closed_orders:
            id = item['id']
            symbol = item['symbol']
            status = item['status'].lower()
            price = float(item['price'])
            avg_price = float(item['avgPx']) if item['avgPx'] != ''  else 0.0
            side = item['side'].lower()
            otype = item['type'].lower()
            original_qty = float(item['amount'])
            executed_qty = float(item['filled'])
            timestamp = item['timestamp']
            fee = float(item['fee']['cost'])
            fee_currency = item['fee']['currency']
            processed_data.append([id, symbol, status, price, avg_price, side, otype, original_qty, executed_qty, timestamp, fee, fee_currency])
        columns = ['id', 'symbol', 'status', 'price', 'avg_price', 'side', 'type', 'original_qty', 'executed_qty', 'ts', 'fee', 'fee_currency']
        closed_orders_df = pd.DataFrame(processed_data, columns=columns)
        closed_orders_df['ex_name'] = ['okx'] * len(closed_orders_df)
        # open_ordersからDataFrameを作成
        processed_data = []
        for item in open_orders:
            id = item['id']
            symbol = item['symbol']
            status = item['status']
            price = float(item['price'])
            avg_price = float(item['avgPx']) if item['avgPx'] != ''  else 0.0
            side = item['side']
            otype = item['type']
            original_qty = float(item['amount'])
            executed_qty = float(item['filled'])
            timestamp = item['timestamp']
            fee = float(item['fee']['cost'])
            fee_currency = item['fee']['currency']
            processed_data.append([id, symbol, status, price, avg_price, side, otype, original_qty, executed_qty, timestamp, fee, fee_currency])
        columns = ['id', 'symbol', 'status', 'price', 'avg_price', 'side', 'type', 'original_qty', 'executed_qty', 'ts', 'fee', 'fee_currency']
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
        order_cols = ['orderId', 'symbol', 'status', 'price', 'avgPrice', 'side', 'type', 'origQty', 'executedQty', 'time']
        order_df = pd.DataFrame(order_df, columns=order_cols)
        order_df = order_df['price'].astype(float)
        order_df = order_df['avgPrice'].astype(float)
        order_df = order_df['origQty'].astype(float)
        order_df = order_df['executedQty'].astype(float)
        order_df = order_df['side'].str.lower()
        order_df = order_df['status'].str.lower()
        fees = []
        fee_currency = []
        for i in range(len(order_df)):
            if order_df['orderId'].iloc[i] in list(trade_df['orderId']):
                commision = trade_df.loc[trade_df['orderId'] == order_df['orderId'].iloc[i], 'commission'].item()
                currency = trade_df.loc[trade_df['orderId'] == order_df['orderId'].iloc[i], 'commissionAsset'].item()
                fees.append(float(commision))
                fee_currency.append(currency)
            else:
                fees.append(0.0)
                fee_currency.append('')
        order_df['fee'] = fees
        order_df['fee_currency'] = fee_currency
        order_df['ex_name'] = ['binance'] * len(order_df)
        order_df.rename(columns={'orderId': 'id', 'avgPrice': 'avg_price', 'origQty': 'original_qty', 'executedQty': 'executed_qty', 'time': 'ts'}, inplace=True)
        return order_df


    
    @classmethod
    def parse_fetch_position_binance(cls, binance_position):
        '''
               symbol   side    price    qty     timestamp  unrealized_pnl  unrealized_pnl_ratio  liquidation_price  margin_ratio
        22  TRX/USDT:USDT  short  0.06381  100.0  1.681288e+12       -0.216356                -65.58           1.056954        0.0004
        '''
        # 必要なカラムを用意
        columns = ['symbol', 'side', 'price', 'qty', 'timestamp', 'unrealized_pnl', 'unrealized_pnl_ratio', 'liquidation_price', 'margin_ratio']
        # カラムに対応する値を格納するリストを作成
        records = []
        for d in binance_position:
            symbol = d['symbol']
            side = d['side']
            price = float(d['entryPrice'])
            qty = float(d['contracts'])
            timestamp = d['timestamp']
            unrealized_pnl = float(d['unrealizedPnl'])
            unrealized_pnl_ratio = float(d['percentage'])
            liquidation_price = float(d['liquidationPrice'])
            margin_ratio = float(d['marginRatio'])
            # 各行の値をタプルとしてリストに追加
            records.append((symbol, side, price, qty, timestamp, unrealized_pnl, unrealized_pnl_ratio, liquidation_price, margin_ratio))
        # リストからデータフレームを作成
        df = pd.DataFrame(records, columns=columns)
        return df[df['side'].notnull()]
    
    

    @classmethod
    def parse_fetch_position_bybit(cls, bybit_positions):
        '''
        [{'info': {'positionIdx': '0', 'riskId': '1', 'riskLimitValue': '200000', 'symbol': 'OPUSDT', 'side': 'Buy', 'size': '1.0', 'avgPrice': '2.6123', 'positionValue': '2.6123', 'tradeMode': '0', 'positionStatus': 'Normal', 'autoAddMargin': '0', 'adlRankIndicator': '2', 'leverage': '10', 'markPrice': '2.6125', 'liqPrice': '0.0001', 'bustPrice': '0.0001', 'positionMM': '0.000001', 'positionIM': '0.052246', 'tpslMode': 'Full', 'takeProfit': '0.0000', 'stopLoss': '0.0000', 'trailingStop': '0.0000', 'unrealisedPnl': '0.0002', 'cumRealisedPnl': '-0.0015809', 'createdTime': '1681266516015', 'updatedTime': '1681448615072'}, 'id': None, 'symbol': 'OP/USDT:USDT', 'timestamp': 1681448615072, 'datetime': '2023-04-14T05:03:35.072Z', 'lastUpdateTimestamp': None, 'initialMargin': 0.26123, 'initialMarginPercentage': 0.1, 'maintenanceMargin': 0.0, 'maintenanceMarginPercentage': 0.0, 'entryPrice': 2.6123, 'notional': 2.6123, 'leverage': 10.0, 'unrealizedPnl': 0.0002, 'contracts': 1.0, 'contractSize': 1.0, 'marginRatio': None, 'liquidationPrice': 0.0001, 'markPrice': 2.6125, 'lastPrice': None, 'collateral': None, 'marginMode': 'cross', 'side': 'long', 'percentage': None}]
            symbol  side   price  qty      timestamp  unrealized_pnl_usd unrealized_pnl_ratio  liquidation_price margin_ratio
        0  OP/USDT:USDT  long  2.6123  1.0  1681448615072          0.0095                 None             0.0001         None
        '''
        # データを整形
        formatted_data = []
        for item in bybit_positions:
            entry_price = item['entryPrice']
            price = item['markPrice']
            unrealized_pnl_ratio = (price - entry_price) / entry_price if item['side'] == 'long' else (entry_price - price) / entry_price
            formatted_data.append({
                'symbol': item['symbol'],
                'side': item['side'],
                'price': float(item['entryPrice']),
                'qty': float(item['contracts']),
                'timestamp': item['timestamp'],
                'unrealized_pnl_usd': float(item['unrealizedPnl']),
                'unrealized_pnl_ratio': float(unrealized_pnl_ratio),
                'liquidation_price': float(item['liquidationPrice']),
                'margin_ratio': float(item['marginRatio']) if item['marginRatio'] != None else None,
            })
        # データフレームを生成
        df = pd.DataFrame(formatted_data, columns=['symbol', 'side', 'price', 'qty', 'timestamp', 'unrealized_pnl_usd', 'unrealized_pnl_ratio', 'liquidation_price', 'margin_ratio'])
        return df


    @classmethod
    def parse_fetch_position_okx(cls, okx_position):
        '''
            symbol  side  price  qty      timestamp  unrealized_pnl  unrealized_pnl_ratio liquidation_price  margin_ratio
        0  DOT/USDT:USDT  long  6.793  1.0  1681453967915          -0.009             -0.132314              None     -0.397468
        '''
        records = []
        for d in okx_position:
            symbol = d['symbol']
            side = d['side']
            price = float(d['info']['markPx'])
            qty = float(d['info']['pos'])
            timestamp = d['timestamp']
            unrealized_pnl = float(d['unrealizedPnl'])
            entry_price = float(d['info']['avgPx'])
            # Calculate unrealized_pnl_ratio
            unrealized_pnl_ratio = (price - entry_price) / entry_price if side == 'long' else (entry_price - price) / entry_price
            margin_ratio = float(d['info']['mgnRatio'])
            liquidation_price = float(d['liquidationPrice']) if d['liquidationPrice']!=None else None
            records.append([symbol, side, entry_price, qty, timestamp, unrealized_pnl, unrealized_pnl_ratio, liquidation_price, margin_ratio])
        df = pd.DataFrame(records, columns=['symbol', 'side', 'price', 'qty', 'timestamp', 'unrealized_pnl', 'unrealized_pnl_ratio', 'liquidation_price', 'margin_ratio'])
        return df


    @classmethod
    def parse_fetch_account_balance_binance(cls, binance_balance):
        '''
        fapiPrivateGetBalance
                accountAlias asset      balance withdrawAvailable     updateTime
        8   sRFzSgXqfWsRAu  USDT   100.005708       99.46825798  1681288077482
        10  sRFzSgXqfWsRAu  USDC  1000.000000     1000.00000000  1681256494484
        '''
        df = pd.DataFrame(binance_balance)
        df['balance'] = df['balance'].astype(float)
        df = df[df['balance']>0]
        df['ex_name'] = ['binance'] * len(df)
        return df[['ex_name', 'asset','balance']]


    @classmethod
    def parse_fetch_account_balance_okx(cls, okx_balance):
        '''
        {'info': {'code': '0', 'data': [{'adjEq': '994.8411120620503', 'details': [{'availBal': '994.3836955620919', 'availEq': '994.3836955620919', 'cashBal': '994.3836955620919', 'ccy': 'USDT', 'crossLiab': '0', 'disEq': '994.8411120620503', 'eq': '994.3836955620919', 'eqUsd': '994.8411120620503', 'fixedBal': '0', 'frozenBal': '0', 'interest': '0', 'isoEq': '0', 'isoLiab': '0', 'isoUpl': '0', 'liab': '0', 'maxLoan': '9943.836955620918', 'mgnRatio': '', 'notionalLever': '', 'ordFrozen': '0', 'spotInUseAmt': '', 'stgyEq': '0', 'twap': '0', 'uTime': '1681563116783', 'upl': '0', 'uplLiab': '0'}], 'imr': '0', 'isoEq': '0', 'mgnRatio': '', 'mmr': '0', 'notionalUsd': '0', 'ordFroz': '0', 'totalEq': '994.8411120620503', 'uTime': '1681795224218'}], 'msg': ''}, 'USDT': {'free': 994.3836955620919, 'used': 0.0, 'total': 994.3836955620919}, 'timestamp': 1681795224218, 'datetime': '2023-04-18T05:20:24.218Z', 'free': {'USDT': 994.3836955620919}, 'used': {'USDT': 0.0}, 'total': {'USDT': 994.3836955620919}}
        '''
        df = pd.DataFrame({'currency': ['USDT'], 'amount': [okx_balance['USDT']['free']]})
        df = df.rename(columns={'currency': 'asset', 'amount':'balance'})
        df['balance'] = df['balance'].astype(float)
        df['ex_name'] = ['okx'] * len(df)
        df = df[df['balance']>0]
        return df
    

    @classmethod
    def parse_fetch_account_balance_bybit(cls, bybit_balance):
        '''
            asset     balance ex_name
        3   XRP    0.013226   bybit
        4  USDT  995.959343   bybit
        '''
        data = {'asset': [], 'balance': []}
        for item in bybit_balance['info']['result']['list']:
            data['asset'].append(item['coin'])
            data['balance'].append(float(item['equity']))
        df = pd.DataFrame(data)
        df = df[df['balance'] > 0]
        df['ex_name'] = ['bybit'] * len(df)
        return df