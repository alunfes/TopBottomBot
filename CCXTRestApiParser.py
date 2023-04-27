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
            order = {'id': d['id'], 'symbol': d['symbol'], 'base_asset': str(d['symbol'].split('/')[0]), 'quote_asset': str(d['symbol'].split(':')[-1]), 'status': d['status'], 'price': float(d['price']),'avg_price': float(d['average']) if d['average']!=None else float(d['price']), 'type':d['type'],
                    'side': d['side'], 'original_qty': float(d['amount']), 'executed_qty': float(d['filled']),
                    'timestamp': pd.to_datetime(d['timestamp'], unit='ms'), 'fee': float(d['fee']['cost']), 'fee_currency': d['fee']['currency']}
            orders.append(order)
        # 辞書型のリストからdataframeを作成する
        df = pd.DataFrame(orders, columns=['id', 'symbol', 'base_asset', 'quote_asset', 'status', 'price', 'avg_price', 'side', 'type',
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
            base_asset = str(item['symbol'].split('/')[0])
            quote_asset = str(item['symbol'].split('/')[1])
            status = item['status'].lower()
            price = float(item['price'])
            avg_price = float(item['average']) if item['average'] != ''  else 0.0
            side = item['side'].lower()
            otype = item['type'].lower()
            original_qty = float(item['amount'])
            executed_qty = float(item['filled'])
            timestamp = item['timestamp']
            fee = float(item['fee']['cost'])
            fee_currency = item['fee']['currency']
            processed_data.append([id, symbol, base_asset, quote_asset, status, price, avg_price, side, otype, original_qty, executed_qty, timestamp, fee, fee_currency])
        columns = ['id', 'symbol', 'base_asset', 'quote_asset', 'status', 'price', 'avg_price', 'side', 'type', 'original_qty', 'executed_qty', 'ts', 'fee', 'fee_currency']
        closed_orders_df = pd.DataFrame(processed_data, columns=columns)
        closed_orders_df['ex_name'] = ['okx'] * len(closed_orders_df)
        # open_ordersからDataFrameを作成
        processed_data = []
        for item in open_orders:
            id = item['id']
            symbol = item['symbol']
            base_asset = str(item['symbol'].split('/')[0])
            quote_asset = str(item['symbol'].split(':')[-1])
            status = item['status']
            price = float(item['price'])
            avg_price = float(item['average']) if item['average'] != None  else 0.0
            side = item['side']
            otype = item['type']
            original_qty = float(item['amount'])
            executed_qty = float(item['filled'])
            timestamp = item['timestamp']
            fee = float(item['fee']['cost'])
            fee_currency = item['fee']['currency']
            processed_data.append([id, symbol, base_asset, quote_asset, status, price, avg_price, side, otype, original_qty, executed_qty, timestamp, fee, fee_currency])
        columns = ['id', 'symbol', 'base_asset', 'quote_asset', 'status', 'price', 'avg_price', 'side', 'type', 'original_qty', 'executed_qty', 'ts', 'fee', 'fee_currency']
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
        if len(order_df) > 0 and len(binace_trades) > 0:
            order_cols = ['orderId', 'symbol', 'status', 'price', 'avgPrice', 'side', 'type', 'origQty', 'executedQty', 'time']
            order_df = pd.DataFrame(order_df, columns=order_cols)
            order_df['base_asset'] = order_df['symbol'].str.replace('USDT', '')
            order_df['quote_asset'] = ['USDT'] * len(order_df)
            order_df['price'] = order_df['price'].astype(float)
            order_df['avgPrice'] = order_df['avgPrice'].astype(float)
            order_df['origQty'] = order_df['origQty'].astype(float)
            order_df['executedQty'] = order_df['executedQty'].astype(float)
            order_df['side'] = order_df['side'].str.lower()
            order_df['status'] = order_df['status'].str.lower()
            fees = []
            fee_currency = []
            for i in range(len(order_df)):
                if order_df['orderId'].iloc[i] in list(trade_df['orderId']):
                    commision_rows = trade_df[trade_df['orderId'] == order_df['orderId'].iloc[i]]
                    commision_sum = 0
                    currency = trade_df.loc[trade_df['orderId'] == order_df['orderId'].iloc[i], 'commissionAsset'].values[0]
                    for _, row in commision_rows.iterrows():
                        commision_sum += float(row['commission'])
                    fees.append(commision_sum)
                    fee_currency.append(currency)
                else:
                    fees.append(0.0)
                    fee_currency.append('')
            order_df['fee'] = fees
            order_df['fee_currency'] = fee_currency
            order_df['ex_name'] = ['binance'] * len(order_df)
            order_df.rename(columns={'orderId': 'id', 'avgPrice': 'avg_price', 'origQty': 'original_qty', 'executedQty': 'executed_qty', 'time': 'ts'}, inplace=True)
            return order_df
        else:
            return None


    
    @classmethod
    def parse_fetch_position_binance(cls, binance_position):
        '''
               symbol   side    price    qty     timestamp  unrealized_pnl  unrealized_pnl_ratio  liquidation_price  margin_ratio
        22  TRX/USDT:USDT  short  0.06381  100.0  1.681288e+12       -0.216356                -65.58           1.056954        0.0004
        '''
        # 必要なカラムを用意
        columns = ['symbol', 'base_asset', 'quote_asset', 'side', 'price', 'qty', 'timestamp', 'unrealized_pnl_usd', 'unrealized_pnl_ratio', 'liquidation_price', 'margin_ratio']
        # カラムに対応する値を格納するリストを作成
        records = []
        for d in binance_position:
            if abs(float(d['contracts'])) > 0:
                symbol = d['symbol']
                base_asset = d['symbol'].split('/')[0]
                quote_asset = d['symbol'].split(':')[-1]
                side = d['side']
                price = float(d['entryPrice'])
                qty = float(d['contracts'])
                timestamp = d['timestamp']
                unrealized_pnl_usd = float(d['unrealizedPnl']) if d['unrealizedPnl'] != None else 0.0
                unrealized_pnl_ratio = float(d['percentage']) if d['percentage'] != None else 0.0
                liquidation_price = float(d['liquidationPrice']) if d['liquidationPrice'] != None else 0.0
                margin_ratio = float(d['marginRatio']) if d['marginRatio'] != None else 0.0
                records.append({'symbol':symbol, 'base_asset':base_asset, 'quote_asset':quote_asset, 'side':side, 'price':price, 'qty':qty, 
                                'timestamp':timestamp, 'unrealized_pnl_usd':unrealized_pnl_usd, 'unrealized_pnl_ratio':unrealized_pnl_ratio, 
                                'liquidation_price':liquidation_price, 'margin_ratio':margin_ratio})
        # リストからデータフレームを作成
        df = pd.DataFrame(records, columns=columns)
        df['ex_name'] = ['binance'] * len(df)
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
                'base_asset': str(item['symbol'].split('/')[0]),
                'quote_asset': str(item['symbol'].split(':')[-1]),
                'side': item['side'],
                'price': float(item['entryPrice']),
                'qty': float(item['contracts']),
                'timestamp': item['timestamp'],
                'unrealized_pnl_usd': float(item['unrealizedPnl']) if item['unrealizedPnl'] != None else 0.0,
                'unrealized_pnl_ratio': float(unrealized_pnl_ratio),
                'liquidation_price': float(item['liquidationPrice']),
                'margin_ratio': float(item['marginRatio']) if item['marginRatio'] != None else 0.0,
            })
        # データフレームを生成
        df = pd.DataFrame(formatted_data, columns=['symbol', 'base_asset', 'quote_asset', 'side', 'price', 'qty', 'timestamp', 'unrealized_pnl_usd', 'unrealized_pnl_ratio', 'liquidation_price', 'margin_ratio'])
        df['ex_name'] = ['bybit'] * len(df)
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
            base_asset = str(d['symbol'].split('/')[0])
            quote_asset = str(d['symbol'].split(':')[-1])
            side = d['side']
            price = float(d['info']['markPx'])
            qty = float(d['info']['pos'])
            timestamp = d['timestamp']
            unrealized_pnl_usd = float(d['unrealizedPnl'])
            entry_price = float(d['info']['avgPx'])
            # Calculate unrealized_pnl_ratio
            unrealized_pnl_ratio = (price - entry_price) / entry_price if side == 'long' else (entry_price - price) / entry_price
            margin_ratio = float(d['info']['mgnRatio'])
            liquidation_price = float(d['liquidationPrice']) if d['liquidationPrice']!=None else 0.0
            records.append([symbol, base_asset, quote_asset, side, entry_price, qty, timestamp, unrealized_pnl_usd, unrealized_pnl_ratio, liquidation_price, margin_ratio])
        df = pd.DataFrame(records, columns=['symbol', 'base_asset', 'quote_asset', 'side', 'price', 'qty', 'timestamp', 'unrealized_pnl_usd', 'unrealized_pnl_ratio', 'liquidation_price', 'margin_ratio'])
        df['ex_name'] = ['okx'] * len(df)
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
        coin_data = bybit_balance['info']['result']['list']
        # assetとbalanceカラムを持つ空のDataFrameを作成
        df = pd.DataFrame(columns=['asset', 'balance'])
        # データを処理してDataFrameに追加
        for entry in coin_data:
            asset = entry['coin']
            balance = float(entry['walletBalance'])
            # balanceが0以上の場合に限り、DataFrameに追加
            if balance > 0:
                new_row = pd.DataFrame({'asset': [asset], 'balance': [balance]})
                df = pd.concat([df, new_row], ignore_index=True)
        df['ex_name'] = ['bybit'] * len(df)
        return df


    @classmethod
    def parse_fetch_trades_okx(cls, trades):
        return pd.json_normalize(trades['data'])
    

    '''
    order -> {'orderId': '32945045423', 'symbol': 'XRPUSDT', 'status': 'NEW', 'clientOrderId': 'TF1xtGYnCJFTQh48NUPjDd', 'price': '0.4500', 'avgPrice': '0.00000', 'origQty': '15', 'executedQty': '0', 'cumQuote': '0', 'timeInForce': 'GTC', 'type': 'LIMIT', 'reduceOnly': False, 'closePosition': False, 'side': 'BUY', 'positionSide': 'BOTH', 'stopPrice': '0', 'workingType': 'CONTRACT_PRICE', 'priceProtect': False, 'origType': 'LIMIT', 'time': '1682483987613', 'updateTime': '1682483987613'}
    trades -> [{'symbol': 'CELRUSDT', 'id': '159843507', 'orderId': '2827747675', 'side': 'BUY', 'price': '0.02624', 'qty': '200', 'realizedPnl': '0', 'marginAsset': 'USDT', 'quoteQty': '5.24800', 'commission': '0.00209919', 'commissionAsset': 'USDT', 'time': '1681971413213', 'positionSide': 'BOTH', 'buyer': True, 'maker': False}, {'symbol': 'CELRUSDT', 'id': '159867547', 'orderId': '2828056546', 'side': 'BUY', 'price': '0.02602', 'qty': '200', 'realizedPnl': '0', 'marginAsset': 'USDT', 'quoteQty': '5.20400', 'commission': '0.00208160', 'commissionAsset': 'USDT', 'time': '1681976259062', 'positionSide': 'BOTH', 'buyer': True, 'maker': False}, {'symbol': 'GTCUSDT', 'id': '125445719', 'orderId': '2068027124', 'side': 'BUY', 'price': '1.696', 'qty': '5', 'realizedPnl': '0', 'marginAsset': 'USDT', 'quoteQty': '8.4800', 'commission': '0.00339200', 'commissionAsset': 'USDT', 'time': '1681976600412', 'positionSide': 'BOTH', 'buyer': True, 'maker': False}, {'symbol': 'CELRUSDT', 'id': '159868555', 'orderId': '2828072296', 'side': 'BUY', 'price': '0.02606', 'qty': '200', 'realizedPnl': '0', 'marginAsset': 'USDT', 'quoteQty': '5.21200', 'commission': '0.00208480', 'commissionAsset': 'USDT', 'time': '1681976600713', 'positionSide': 'BOTH', 'buyer': True, 'maker': False}, {'symbol': 'GTCUSDT', 'id': '125445951', 'orderId': '2068034747', 'side': 'SELL', 'price': '1.694', 'qty': '5', 'realizedPnl': '-0.01000000', 'marginAsset': 'USDT', 'quoteQty': '8.4700', 'commission': '0.00338800', 'commissionAsset': 'USDT', 'time': '1681976841220', 'positionSide': 'BOTH', 'buyer': False, 'maker': False}, {'symbol': 'CELRUSDT', 'id': '159869392', 'orderId': '2828085592', 'side': 'SELL', 'price': '0.02602', 'qty': '600', 'realizedPnl': '-0.05200000', 'marginAsset': 'USDT', 'quoteQty': '15.61200', 'commission': '0.00624480', 'commissionAsset': 'USDT', 'time': '1681976842647', 'positionSide': 'BOTH', 'buyer': False, 'maker': False},
    '''
    @classmethod
    def parse_fetch_order_binance(cls, order, trades):
        if 'status' in order:
            commission = 0
            commission_asset = ''
            for trade in trades:
                if trade['symbol'] == order['symbol']:
                    commission = trade['commission']
                    commission_asset = trade['commissionAsset']
            return pd.DataFrame({'ex_name':'binance', 'id':order['orderId'], 'symbol':order['symbol'], 'base_asset':order['symbol'].replace('USDT',''), 'quote_asset':'USDT',
             'status':order['status'].lower(), 'price':float(order['price']), 'avg_price':float(order['avgPrice']), 'side':order['side'],
               'type':order['type'].lower(), 'original_qty':float(order['origQty']), 'executed_qty':float(order['executedQty']),
               'ts':order['time'], 'fee':float(commission), 'fee_currency':commission_asset})
        else:
            print('****************************************')
            print('Binance Order data is invalid to parse!')
            print(order)
            print('****************************************')

    '''
    {'info': {'orderId': 'b1a18135-5982-4758-ada4-58026d1a2c8a', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'OPUSDT', 'price': '2.1104', 'qty': '1.0', 'side': 'Sell', 'isLeverage': '', 'positionIdx': '0', 'orderStatus': 'Filled', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '2.220720000', 'leavesQty': '0.0', 'leavesValue': '0', 'cumExecQty': '1.0', 'cumExecValue': '2.22072', 'cumExecFee': '0.00133244', 'timeInForce': 'IOC', 'orderType': 'Market', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.0000', 'takeProfit': '0.0000', 'stopLoss': '0.0000', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '0.0000', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1681285869078', 'updatedTime': '1681285869080', 'placeType': ''}, 'id': 'b1a18135-5982-4758-ada4-58026d1a2c8a', 'clientOrderId': None, 'timestamp': 1681285869078, 'datetime': '2023-04-12T07:51:09.078Z', 'lastTradeTimestamp': 1681285869080, 'symbol': 'OP/USDT:USDT', 'type': 'market', 'timeInForce': 'IOC', 'postOnly': False, 'reduceOnly': False, 'side': 'sell', 'price': 2.1104, 'stopPrice': None, 'triggerPrice': None, 'amount': 1.0, 'cost': 2.22072, 'average': 2.22072, 'filled': 1.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': 0.00133244, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.00133244, 'currency': 'USDT'}]}
    '''
    @classmethod
    def parse_fetch_order_bybit(cls, order):
        if 'status' in order:
            return pd.DataFrame({'ex_name':'bybit', 'id':order['id'], 'symbol':order['symbol'], 'base_asset':order['symbol'].split('/')[0], 
                                 'quote_asset':order['symbol'].split(':')[-1], 'status':order['status'].lower(), 'price':float(order['info']['price']),
                                   'avg_price':float(order['info']['avgPrice']), 'side':order['side'],'type':order['type'].lower(), 
                                   'original_qty':float(order['filled']) + float(order['remaining']), 'executed_qty':float(order['filled']),'ts':order['timestamp'], 
                                   'fee':float(order['fees']['cost']), 'fee_currency':order['fees']['currency']})
        else:
            print('****************************************')
            print('Bybit Order data is invalid to parse!')
            print(order)
            print('****************************************')



    '''
    {'info': {'accFillSz': '10', 'algoClOrdId': '', 'algoId': '', 'avgPx': '0.081858', 'cTime': '1681285189513', 'cancelSource': '', 'cancelSourceReason': '', 'category': 'normal', 'ccy': '', 'clOrdId': 'e847386590ce4dBC6b998cb4b173f5e2', 'fee': '-0.40929', 'feeCcy': 'USDT', 'fillPx': '0.08185', 'fillSz': '2', 'fillTime': '1681285189514', 'instId': 'DOGE-USDT-SWAP', 'instType': 'SWAP', 'lever': '3.0', 'ordId': '566286360827858944', 'ordType': 'market', 'pnl': '0', 'posSide': 'net', 'px': '', 'quickMgnType': '', 'rebate': '0', 'rebateCcy': 'USDT', 'reduceOnly': 'false', 'side': 'sell', 'slOrdPx': '', 'slTriggerPx': '', 'slTriggerPxType': '', 'source': '', 'state': 'filled', 'sz': '10', 'tag': 'e847386590ce4dBC', 'tdMode': 'cross', 'tgtCcy': '', 'tpOrdPx': '', 'tpTriggerPx': '', 'tpTriggerPxType': '', 'tradeId': '224719298', 'uTime': '1681285189515'}, 
    'id': '566286360827858944', 'clientOrderId': 'e847386590ce4dBC6b998cb4b173f5e2', 'timestamp': 1681285189513, 'datetime': '2023-04-12T07:39:49.513Z', 'lastTradeTimestamp': 1681285189514, 'symbol': 'DOGE/USDT:USDT', 'type': 'market', 'timeInForce': 'IOC', 'postOnly': None, 'side': 'sell', 'price': 0.081858, 'stopLossPrice': None, 'takeProfitPrice': None, 'stopPrice': None, 'triggerPrice': None, 'average': 0.081858, 'cost': 818.58, 'amount': 10.0, 'filled': 10.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': 0.40929, 'currency': 'USDT'}, 'trades': [], 'reduceOnly': False, 'fees': [{'cost': 0.40929, 'currency': 'USDT'}]}
    '''
    @classmethod
    def parse_fetch_order_okx(cls, order):
        if 'status' in order:
            return pd.DataFrame({'ex_name':'okx', 'id':order['id'], 'symbol':order['symbol'], 'base_asset':order['symbol'].split('/')[0], 
                                 'quote_asset':order['symbol'].split(':')[-1], 'status':order['status'].lower(), 'price':float(order['info']['price']),
                                   'avg_price':float(order['average']), 'side':order['side'],'type':order['type'].lower(), 
                                   'original_qty':float(order['filled']) + float(order['remaining']), 'executed_qty':float(order['filled']),'ts':order['timestamp'], 
                                   'fee':float(order['fees']['cost']), 'fee_currency':order['fees']['currency']})
        else:
            print('****************************************')
            print('OKX Order data is invalid to parse!')
            print(order)
            print('****************************************')



