from TargetSymbolsData import TargetSymbolsData
from CommunicationData import CommunicationData
from CCXTRestApiParser import CCXTRestApiParser

import ccxt.async_support as ccxt
import time
import datetime
import itertools
import asyncio
import aiohttp
import pandas as pd
import os
import numpy as np
import yaml



'''
・Binance, Bybit, OKXに対して発注・口座管理を行う。
・Binance, Bybit, OKXの取り扱い銘柄、出来高、sell okの情報を取得する。
・Binance, Bybit, OKXから指定された銘柄の指定期間のohlcvを取得する。

API classでは単純にccxtのwrapperとしての役割に限定して、
'''
class CCXTRestApi:
    __instance = None

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance
    
    def __init__(self):
        self.exchanges = ['binance', 'bybit', 'okx']
        self.__read_api_key()
        self.ccxt_exchanges = {}
        for ex in self.exchanges:
            self.ccxt_exchanges[ex] = self.__get_exchanges(ex)
            if ex=='binance':
                #self.ccxt_exchanges[ex].options = {'defaultType': 'linear', 'adjustForTimeDifference': True}
                pass
        self.ex_num_downloads = {'okx':100, 'bybit':100, 'binance':500}
        

    def __read_api_key(self):
        self.public_keys = {}
        self.secret_keys = {}
        self.password = {}
        with open('./ignore/api.yaml', 'r') as f:
            api_keys = yaml.load(f, Loader=yaml.FullLoader)
            for ex in self.exchanges:
                self.public_keys[ex] = api_keys[ex]['public_key']
                self.secret_keys[ex] = api_keys[ex]['secret_key']
                if ex == 'okx':
                    self.password[ex] = api_keys[ex]['password']
                else:
                    self.password[ex] = ''
                

    
    def __get_exchanges(self, ex_name:str):
        #return getattr(ccxt, ex_name)({ 'enableRateLimit': True })
        exchange_class = getattr(ccxt, ex_name)
        exchange_instance = exchange_class({
            'apiKey': self.public_keys[ex_name],
            'secret': self.secret_keys[ex_name],
            'password': self.password[ex_name],
            'enableRateLimit': True,
        })
        return exchange_instance
    

    '''
    id	symbol	base	quote	baseId	quoteId	active	type	linear	inverse	spot	swap	future	option	margin	contract	contractSize	expiry	expiryDatetime	optionType	strike	settle	settleId	precision	limits	info	percentage	feeSide	tierBased	taker	maker	lowercaseId
    '''
    async def get_tickers(self, ex_name):
        res = await self.ccxt_exchanges[ex_name].load_markets()
        df = pd.DataFrame(res).transpose()
        return df[df['active'] == True]
    
    

    '''
    priceChange	priceChangePercent	weightedAvgPrice	prevClosePrice	lastPrice	lastQty	bidPrice	bidQty	askPrice	askQty	openPrice	highPrice	lowPrice	volume	quoteVolume	openTime	closeTime	firstId	lastId	count
    for binance
    '''
    async def get_tickers_24h_binance(self):
        res_pub = await self.ccxt_exchanges['binance'].public_get_ticker_24hr()
        res_fapi = await self.ccxt_exchanges['binance'].fapiPublic_get_ticker_24hr()
        #pd.DataFrame(res_pub).to_csv('./binance_vol1.csv')
        #pd.DataFrame(res_fapi).to_csv('./binance_vol2.csv')
        res_pub = pd.DataFrame(res_pub)[['symbol', 'weightedAvgPrice', 'volume', 'quoteVolume']]
        res_fapi = pd.DataFrame(res_fapi)[['symbol', 'weightedAvgPrice', 'volume', 'quoteVolume']]
        return pd.concat([res_pub, res_fapi], ignore_index=True)


    async def get_tickers_24h_bybit(self):
        res = await self.ccxt_exchanges['bybit'].public_get_derivatives_v3_public_tickers()
        return pd.DataFrame(res['result']['list'])


    async def get_tickers_24h_okx(self):
        res = await self.ccxt_exchanges['okx'].fetch_tickers()
        return pd.DataFrame(res).transpose()


    async def __get_ohlc(self, ex_name, symbol:str, timeframe:str, since_ts, num_downloads):
        res = []
        try:
            res = await self.ccxt_exchanges[ex_name].fetch_ohlcv(
                    symbol=symbol,     # 暗号資産[通貨]
                    timeframe = timeframe,    # 時間足('1m', '5m', '1h', '1d')
                    since=since_ts,          # 取得開始時刻(Unix Timeミリ秒)
                    limit=num_downloads,           # 取得件数(デフォルト:100、最大:500)
                    #params={}             # 各種パラメータ
                )
        except Exception as e:
            print('Error-__get_ohlc: ', e)
            print('ex:',ex_name, ', symbol:',symbol, ', timeframe:',timeframe, ', since_ts:',since_ts, ', res:', res)
        return res

    async def get_ohlc(self, ex_name:str, symbol:str, ohlc_min:int, since_ts):
        ohlcv = []
        timeframe = {1:'1m', 5:'5m', 60:'1h', 240:'4h', 480:'8h', 1440:'1d'}[ohlc_min]
        num_downloads = self.ex_num_downloads[ex_name]
        while True:
            res = await self.__get_ohlc(ex_name, symbol, timeframe, since_ts, num_downloads)
            await asyncio.sleep(0.1)
            if len(res) > 0:
                ohlcv.extend(res)
                since_ts = res[-1][0] + ohlc_min
                #print(ex_name, '-', symbol, ' len=', len(res), ', since_ts=',since_ts, ', res last=', res[-1][0])
            if len(res) < num_downloads*0.5:
                print('ohlc download completed - ', ex_name, ' : ', symbol, ', res=',len(res), ':', num_downloads)
                break
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['dt'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.reindex(columns=['timestamp','dt','open','high','low','close','volume'])
        df.set_index('timestamp', inplace=True)
        # ダウンロードしたデータをCSVファイルに保存
        filename = ex_name+'-'+symbol.replace('/','').split(':')[0]+'.csv'
        df.to_csv('./Data/ohlcv/'+filename, index=False)
        return {'symbol':symbol, 'ohlcv':ohlcv}


    '''
    ex_symbol_pairs = 
    '''
    async def get_multiple_ohlc(self, ex_symbol_pairs:list, ohlc_min:int, since_ts):
        data = {}
        tasks = {}
        if len(ex_symbol_pairs) > 0:    
            async with asyncio.TaskGroup() as tg:
                for ex_symbol_pair in ex_symbol_pairs: 
                    task = tg.create_task(self.get_ohlc(ex_symbol_pair['ex_name'], ex_symbol_pair['symbol'], ohlc_min, since_ts))
                task_name = ex_symbol_pair['ex_name'] + '-' + ex_symbol_pair['symbol']
                data[task_name] = await task
        return data

    '''
        symbol                bids                asks      timestamp                  datetime          nonce
    0    1000LUNC/USDT:USDT  [0.1256, 158408.0]   [0.1257, 27027.0]  1681028005449  2023-04-09T08:13:25.449Z  2722331501170
    1    1000LUNC/USDT:USDT  [0.1255, 262032.0]  [0.1258, 224375.0]  1681028005449  2023-04-09T08:13:25.449Z  2722331501170
    499  1000LUNC/USDT:USDT    [0.0655, 1526.0]    [0.176, 19934.0]  1681028005449  2023-04-09T08:13:25.449Z  2722331501170
    '''
    async def fetch_order_book(self, ex_name, symbol):
        res = await crp.ccxt_exchanges[ex_name].fetch_order_book(symbol)
        return pd.DataFrame(res)
    
    '''
    symbol,markPrice,indexPrice,estimatedSettlePrice,lastFundingRate,interestRate,nextFundingTime,time
    '''
    async def get_all_prices_binance(self):
        res = asyncio.run(crp.ccxt_exchanges['binance'].fapiPublic_get_premiumindex())
        return pd.DataFrame(res)
        
    '''
    ex_name, symbol	timestamp	datetime	high	low	bid	bidVolume	ask	askVolume	vwap	open	close	last	previousClose	change	percentage	average	baseVolume	quoteVolume	info
    '''
    async def fetch_all_target_prices(self, ex_name):
        usdt_perpetual_tickers = {}
        target_df = TargetSymbolsData.target_df.copy()
        #target_df = pd.read_csv('./Data/target_df.csv')
        for i in range(len(target_df)):
            if target_df['ex_name'].iloc[i] == ex_name:
                ticker = await self.ccxt_exchanges[ex_name].fetch_ticker(target_df['symbol'].iloc[i])
                usdt_perpetual_tickers[target_df['symbol'].iloc[i]] = ticker
        df = pd.DataFrame(usdt_perpetual_tickers).transpose()
        df['ex_name'] = [ex_name] * len(df)
        return df

    
    async def fetch_target_price(self, ex_name, symbol):
        '''
        ,ask,askVolume,average,baseVolume,bid,bidVolume,change,close,datetime,high,info,last,low,open,percentage,previousClose,quoteVolume,symbol,timestamp,vwap
        '''
        ticker = await self.ccxt_exchanges[ex_name].fetch_ticker(symbol)
        return pd.DataFrame({symbol:ticker}).transpose()

    
    async def fetch_account_balance(self, ex_name):
        '''
        binance:
        {'info': {'makerCommission': '10', 'takerCommission': '10', 'buyerCommission': '0', 'sellerCommission': '0', 'commissionRates': {'maker': '0.00100000', 'taker': '0.00100000', 'buyer': '0.00000000', 'seller': '0.00000000'}, 'canTrade': True, 'canWithdraw': True, 'canDeposit': True, 'brokered': False, 'requireSelfTradePrevention': False, 'updateTime': '1681258145176', 'accountType': 'SPOT', 'balances': [{'asset': 'BTC', 'free': '0.00000000', 'locked': '0.00000000'}, {'asset': 'LTC', 'free': '0.00000000', 'locked': '0.00000000'}, {'asset': 'ETH', 'free': '0.00000000', 'locked': '0.00000000'}, {'asset': 'NEO', 'free': '0.00000000', 'locked': '0.00000000'}, {'asset': 'BNB', 'free': '0.00000000', 'locked': '0.00000000'}, {'asset': 'QTUM', 'free': '0.00000000', 'locked': '0.00000000'}, {'asset': 'EOS', 'free': '0.00000000', 'locked': '0.00000000'}, {'asset': 'SNT', 'free': '0.00000000', 'locked': '0.00000000'},}
        bybit:
        {'info': {'retCode': '0', 'retMsg': 'OK', 'result': {'list': [{'coin': 'BTC', 'equity': '0', 'walletBalance': '0', 'positionMargin': '0', 'availableBalance': '0', 'orderMargin': '0', 'occClosingFee': '0', 'occFundingFee': '0', 'unrealisedPnl': '0', 'cumRealisedPnl': '-0.47585393', 'givenCash': '0', 'serviceCash': '0', 'accountIM': '', 'accountMM': ''}, {'coin': 'ETH', 'equity': '0', 'walletBalance': '0', 'positionMargin': '0', 'availableBalance': '0', 'orderMargin': '0', 'occClosingFee': '0', 'occFundingFee': '0', 'unrealisedPnl': '0', 'cumRealisedPnl': '191.09269265', 'givenCash': '0', 'serviceCash': '0', 'accountIM': '', 'accountMM': ''}, {'coin': 'EOS', 'equity': '0', 'walletBalance': '0', 'positionMargin': '0', 'availableBalance': '0', 'orderMargin': '0', 'occClosingFee': '0', 'occFundingFee': '0', 'unrealisedPnl': '0', 'cumRealisedPnl': '0', 'givenCash': '0', 'serviceCash': '0', 'accountIM': '', 'accountMM': ''}, {'coin': 'XRP', 'equity': '0.01322603', 'walletBalance': '0.01322603', 'positionMargin': '0', 'availableBalance': '0.01322603', 'orderMargin': '0', 'occClosingFee': '0', 'occFundingFee': '0', 'unrealisedPnl': '0', 'cumRealisedPnl': '1242.16322603', 'givenCash': '0', 'serviceCash': '0', 'accountIM': '', 'accountMM': ''}, {'coin': 'USDT', 'equity': '995.91984767', 'walletBalance': '995.91972767', 'positionMargin': '0.22353768', 'availableBalance': '995.69618999', 'orderMargin': '0', 'occClosingFee': '0.11999988', 'occFundingFee': '0', 'unrealisedPnl': '0.00012', 'cumRealisedPnl': '16625.14302767', 'givenCash': '0', 'serviceCash': '0', 'accountIM': '', 'accountMM': ''}, {'coin': 'DOT', 'equity': '0', 'walletBalance': '0', 'positionMargin': '0', 'availableBalance': '0', 'orderMargin': '0', 'occClosingFee': '0', 'occFundingFee': '0', 'unrealisedPnl': '0', 'cumRealisedPnl': '0', 'givenCash': '0', 'serviceCash': '0', 'accountIM': '', 'accountMM': ''}, {'coin': 'LTC', 'equity': '0', 'walletBalance': '0', 'positionMargin': '0', 'availableBalance': '0', 'orderMargin': '0', 'occClosingFee': '0', 'occFundingFee': '0', 'unrealisedPnl': '0', 'cumRealisedPnl': '0', 'givenCash': '0', 'serviceCash': '0', 'accountIM': '', 'accountMM': ''}, {'coin': 'BIT', 'equity': '0', 'walletBalance': '0', 'positionMargin': '0', 'availableBalance': '0', 'orderMargin': '0', 'occClosingFee': '0', 'occFundingFee': '0', 'unrealisedPnl': '0', 'cumRealisedPnl': '0', 'givenCash': '0', 'serviceCash': '0', 'accountIM': '', 'accountMM': ''}, {'coin': 'USDC', 'equity': '0', 'walletBalance': '0', 'positionMargin': '0', 'availableBalance': '0', 'orderMargin': '0', 'occClosingFee': '0', 'occFundingFee': '0', 'unrealisedPnl': '0', 'cumRealisedPnl': '0', 'givenCash': '0', 'serviceCash': '0', 'accountIM': '0', 'accountMM': '0'}, {'coin': 'ADA', 'equity': '0', 'walletBalance': '0', 'positionMargin': '0', 'availableBalance': '0', 'orderMargin': '0', 'occClosingFee': '0', 'occFundingFee': '0', 'unrealisedPnl': '0', 'cumRealisedPnl': '0', 'givenCash': '0', 'serviceCash': '0', 'accountIM': '', 'accountMM': ''}, {'coin': 'MANA', 'equity': '0', 'walletBalance': '0', 'positionMargin': '0', 'availableBalance': '0', 'orderMargin': '0', 'occClosingFee': '0', 'occFundingFee': '0', 'unrealisedPnl': '0', 'cumRealisedPnl': '0', 'givenCash': '0', 'serviceCash': '0', 'accountIM': '', 'accountMM': ''}]}, 'retExtInfo': {}, 'time': '1681285933593'}, 'BTC': {'free': 0.0, 'used': 0.0, 'total': 0.0}, 'ETH': {'free': 0.0, 'used': 0.0, 'total': 0.0}, 'EOS': {'free': 0.0, 'used': 0.0, 'total': 0.0}, 'XRP': {'free': 0.01322603, 'used': 0.0, 'total': 0.01322603}, 'USDT': {'free': 995.69618999, 'used': 0.22353768, 'total': 995.91972767}, 'DOT': {'free': 0.0, 'used': 0.0, 'total': 0.0}, 'LTC': {'free': 0.0, 'used': 0.0, 'total': 0.0}, 'BIT': {'free': 0.0, 'used': 0.0, 'total': 0.0}, 'USDC': {'free': 0.0, 'used': 0.0, 'total': 0.0}, 'ADA': {'free': 0.0, 'used': 0.0, 'total': 0.0}, 'MANA': {'free': 0.0, 'used': 0.0, 'total': 0.0}, 'free': {'BTC': 0.0, 'ETH': 0.0, 'EOS': 0.0, 'XRP': 0.01322603, 'USDT': 995.69618999, 'DOT': 0.0, 'LTC': 0.0, 'BIT': 0.0, 'USDC': 0.0, 'ADA': 0.0, 'MANA': 0.0}, 'used': {'BTC': 0.0, 'ETH': 0.0, 'EOS': 0.0, 'XRP': 0.0, 'USDT': 0.22353768, 'DOT': 0.0, 'LTC': 0.0, 'BIT': 0.0, 'USDC': 0.0, 'ADA': 0.0, 'MANA': 0.0}, 'total': {'BTC': 0.0, 'ETH': 0.0, 'EOS': 0.0, 'XRP': 0.01322603, 'USDT': 995.91972767, 'DOT': 0.0, 'LTC': 0.0, 'BIT': 0.0, 'USDC': 0.0, 'ADA': 0.0, 'MANA': 0.0}}
        okx:
        {'info': {'code': '0', 'data': [{'adjEq': '996.3416641222', 'details': [{'availBal': '723.1372633333333', 'availEq': '723.1372633333334', 'cashBal': '995.22393', 'ccy': 'USDT', 'crossLiab': '0', 'disEq': '996.3416641222', 'eq': '995.80393', 'eqUsd': '996.3416641222', 'fixedBal': '0', 'frozenBal': '272.6666666666667', 'interest': '0', 'isoEq': '0', 'isoLiab': '0', 'isoUpl': '0', 'liab': '0', 'maxLoan': '7231.372633333332', 'mgnRatio': '', 'notionalLever': '', 'ordFrozen': '0', 'spotInUseAmt': '', 'stgyEq': '0', 'twap': '0', 'uTime': '1681285189515', 'upl': '0.5800000000000249', 'uplLiab': '0'}], 'imr': '272.8139066666667', 'isoEq': '0', 'mgnRatio': '115.93944929561067', 'mmr': '8.1844172', 'notionalUsd': '818.44172', 'ordFroz': '0', 'totalEq': '996.3416641222', 'uTime': '1681285648795'}], 'msg': ''}, 'USDT': {'free': 723.1372633333334, 'used': 272.6666666666666, 'total': 995.80393}, 'timestamp': 1681285648795, 'datetime': '2023-04-12T07:47:28.795Z', 'free': {'USDT': 723.1372633333334}, 'used': {'USDT': 272.6666666666666}, 'total': {'USDT': 995.80393}}
        '''
        if ex_name == 'binance':
            res = await self.ccxt_exchanges['binance'].fapiPrivateGetBalance()
        else:
            res = await self.ccxt_exchanges[ex_name].fetch_balance()
        return res

    
    async def fetch_holding_position(self, ex_name):
        '''
        実際にポジション持っている時のデータを取る必要がある、col=symbolで該当するもののポジションを取ることができる。
        binance:

        bybit:
        [{'info': {'positionIdx': '0', 'riskId': '1', 'riskLimitValue': '200000', 'symbol': 'OPUSDT', 'side': 'Sell', 'size': '1.0', 'avgPrice': '2.22072', 'positionValue': '2.22072', 'tradeMode': '0', 'positionStatus': 'Normal', 'autoAddMargin': '0', 'adlRankIndicator': '2', 'leverage': '10', 'markPrice': '2.2209', 'liqPrice': '199.9998', 'bustPrice': '199.9998', 'positionMM': '1.999998', 'positionIM': '0.0444144', 'tpslMode': 'Full', 'takeProfit': '0.0000', 'stopLoss': '0.0000', 'trailingStop': '0.0000', 'unrealisedPnl': '-0.00018', 'cumRealisedPnl': '-0.00133244', 'createdTime': '1681266516015', 'updatedTime': '1681285869080'}, 'id': None, 'symbol': 'OP/USDT:USDT', 'timestamp': 1681285869080, 'datetime': '2023-04-12T07:51:09.080Z', 'lastUpdateTimestamp': None, 'initialMargin': 0.222072, 'initialMarginPercentage': 0.1, 'maintenanceMargin': 0.0, 'maintenanceMarginPercentage': 0.0, 'entryPrice': 2.22072, 'notional': 2.22072, 'leverage': 10.0, 'unrealizedPnl': -0.00018, 'contracts': 1.0, 'contractSize': 1.0, 'marginRatio': None, 'liquidationPrice': 199.9998, 'markPrice': 2.2209, 'lastPrice': None, 'collateral': None, 'marginMode': 'cross', 'side': 'short', 'percentage': None}]
        okx:
        [{'info': {'adl': '1', 'availPos': '', 'avgPx': '0.081858', 'baseBal': '', 'baseBorrowed': '', 'baseInterest': '', 'bizRefId': '', 'bizRefType': '', 'cTime': '1681285189515', 'ccy': 'USDT', 'closeOrderAlgo': [], 'deltaBS': '', 'deltaPA': '', 'gammaBS': '', 'gammaPA': '', 'imr': '273.03333333333336', 'instId': 'DOGE-USDT-SWAP', 'instType': 'SWAP', 'interest': '', 'last': '0.08191', 'lever': '3', 'liab': '', 'liabCcy': '', 'liqPx': '0.1794956615280094', 'margin': '', 'markPx': '0.08191', 'mgnMode': 'cross', 'mgnRatio': '115.65585107929144', 'mmr': '8.190999999999999', 'notionalUsd': '819.5259320000001', 'optVal': '', 'pendingCloseOrdLiabVal': '', 'pos': '-10', 'posCcy': '', 'posId': '566286360836247552', 'posSide': 'net', 'quoteBal': '', 'quoteBorrowed': '', 'quoteInterest': '', 'spotInUseAmt': '', 'spotInUseCcy': '', 'thetaBS': '', 'thetaPA': '', 'tradeId': '224719298', 'uTime': '1681285189515', 'upl': '-0.5199999999999649', 'uplRatio': '-0.0019057392069195', 'usdPx': '', 'vegaBS': '', 'vegaPA': ''}, 'id': None, 'symbol': 'DOGE/USDT:USDT', 'notional': 819.5259320000001, 'marginMode': 'cross', 'liquidationPrice': 0.1794956615280094, 'entryPrice': 0.081858, 'unrealizedPnl': -0.5199999999999649, 'percentage': -0.19057392069195, 'contracts': 10.0, 'contractSize': 1000.0, 'markPrice': 0.08191, 'lastPrice': None, 'side': 'short', 'hedged': False, 'timestamp': 1681285189515, 'datetime': '2023-04-12T07:39:49.515Z', 'lastUpdateTimestamp': None, 'maintenanceMargin': 8.190999999999999, 'maintenanceMarginPercentage': 0.01, 'collateral': 272.5133333333334, 'initialMargin': 273.03333333333336, 'initialMarginPercentage': 0.3331, 'leverage': 3.0, 'marginRatio': 0.03}]
        '''
        if ex_name == 'binance':
            #res = await self.ccxt_exchanges['binance'].fapiPrivateV2_get_account()
            res = await self.ccxt_exchanges['binance'].fetchPositions()
            return res['positions']
        else:
            res = await self.ccxt_exchanges[ex_name].fetch_positions()
            return res

    async def fetch_positions(self, ex_name):
        res = await self.ccxt_exchanges[ex_name].fetchPositions()
        return res


    async def get_all_orders(self, ex_name):
        '''
        binance:
        [{'orderId': '4695008235', 'symbol': 'ALICEUSDT', 'status': 'CANCELED', 'clientOrderId': 'web_k5XLetP8GdD13nXKmeH9', 'price': '1.780', 'avgPrice': '0.0000', 'origQty': '10', 'executedQty': '0', 'cumQuote': '0', 'timeInForce': 'GTC', 'type': 'LIMIT', 'reduceOnly': False, 'closePosition': False, 'side': 'SELL', 'positionSide': 'BOTH', 'stopPrice': '0', 'workingType': 'CONTRACT_PRICE', 'priceProtect': False, 'origType': 'LIMIT', 'time': '1681256671435', 'updateTime': '1681256677457'}, {'orderId': '4695044324', 'symbol': 'ALICEUSDT', 'status': 'CANCELED', 'clientOrderId': 'web_YtYQlimZ9D83hPRvtn9O', 'price': '1.750', 'avgPrice': '0.0000', 'origQty': '10', 'executedQty': '0', 'cumQuote': '0', 'timeInForce': 'GTC', 'type': 'LIMIT', 'reduceOnly': False, 'closePosition': False, 'side': 'SELL', 'positionSide': 'BOTH', 'stopPrice': '0', 'workingType': 'CONTRACT_PRICE', 'priceProtect': False, 'origType': 'LIMIT', 'time': '1681258340605', 'updateTime': '1681258346332'}, {'orderId': '4695181725', 'symbol': 'ALICEUSDT', 'status': 'CANCELED', 'clientOrderId': '3OBMscMBHWcBXmXnzJ7deT', 'price': '1', 'avgPrice': '0.0000', 'origQty': '10', 'executedQty': '0', 'cumQuote': '0', 'timeInForce': 'GTC', 'type': 'LIMIT', 'reduceOnly': False, 'closePosition': False, 'side': 'BUY', 'positionSide': 'BOTH', 'stopPrice': '0', 'workingType': 'CONTRACT_PRICE', 'priceProtect': False, 'origType': 'LIMIT', 'time': '1681263917931', 'updateTime': '1681263949531'}, {'orderId': '4695200291', 'symbol': 'ALICEUSDT', 'status': 'CANCELED', 'clientOrderId': 'ZUaqCp5xEBjTSpzJlk1mZC', 'price': '1', 'avgPrice': '0.0000', 'origQty': '10', 'executedQty': '0', 'cumQuote': '0', 'timeInForce': 'GTC', 'type': 'LIMIT', 'reduceOnly': False, 'closePosition': False, 'side': 'BUY', 'positionSide': 'BOTH', 'stopPrice': '0', 'workingType': 'CONTRACT_PRICE', 'priceProtect': False, 'origType': 'LIMIT', 'time': '1681264352569', 'updateTime': '1681264592891'}, {'orderId': '4695221183', 'symbol': 'ALICEUSDT', 'status': 'NEW', 'clientOrderId': 'g5Vek7273Mjckodq3BwJmm', 'price': '1', 'avgPrice': '0.0000', 'origQty': '10', 'executedQty': '0', 'cumQuote': '0', 'timeInForce': 'GTC', 'type': 'LIMIT', 'reduceOnly': False, 'closePosition': False, 'side': 'BUY', 'positionSide': 'BOTH', 'stopPrice': '0', 'workingType': 'CONTRACT_PRICE', 'priceProtect': False, 'origType': 'LIMIT', 'time': '1681264940381', 'updateTime': '1681264940381'}]
        bybit:
        [{'info': {'orderId': 'be571b83-4e68-4510-858f-e34136dcc53e', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'ETHUSDT', 'price': '984.10', 'qty': '150.00', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '1', 'orderStatus': 'Cancelled', 'cancelType': 'CancelByUser', 'rejectReason': 'EC_NoError', 'avgPrice': '0', 'leavesQty': '0.00', 'leavesValue': '0', 'cumExecQty': '0.00', 'cumExecValue': '0', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.00', 'takeProfit': '0.00', 'stopLoss': '0.00', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '984.40', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1609729440756', 'updatedTime': '1609729536969', 'placeType': ''}, 'id': 'be571b83-4e68-4510-858f-e34136dcc53e', 'clientOrderId': None, 'timestamp': 1609729440756, 'datetime': '2021-01-04T03:04:00.756Z', 'lastTradeTimestamp': 1609729536969, 'symbol': 'ETH/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 984.1, 'stopPrice': None, 'triggerPrice': None, 'amount': 150.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 0.0, 'status': 'canceled', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': '0a2ca8a0-9e07-49f2-8a37-93ecfdf9b066', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'ETHUSDT', 'price': '979.40', 'qty': '150.00', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '1', 'orderStatus': 'Cancelled', 'cancelType': 'CancelByUser', 'rejectReason': 'EC_NoError', 'avgPrice': '0', 'leavesQty': '0.00', 'leavesValue': '0', 'cumExecQty': '0.00', 'cumExecValue': '0', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.00', 'takeProfit': '0.00', 'stopLoss': '0.00', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '984.70', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1609729569888', 'updatedTime': '1609732045797', 'placeType': ''}, 'id': '0a2ca8a0-9e07-49f2-8a37-93ecfdf9b066', 'clientOrderId': None, 'timestamp': 1609729569888, 'datetime': '2021-01-04T03:06:09.888Z', 'lastTradeTimestamp': 1609732045797, 'symbol': 'ETH/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 979.4, 'stopPrice': None, 'triggerPrice': None, 'amount': 150.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 0.0, 'status': 'canceled', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': '9eb7a71c-ad5b-4bd5-b931-fcc9c21b5f3e', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'ETHUSDT', 'price': '1001.75', 'qty': '150.00', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '1', 'orderStatus': 'Filled', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '1001.750', 'leavesQty': '0.00', 'leavesValue': '0', 'cumExecQty': '150.00', 'cumExecValue': '150262.5', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.00', 'takeProfit': '0.00', 'stopLoss': '0.00', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '1001.80', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1609731616717', 'updatedTime': '1609731637517', 'placeType': ''}, 'id': '9eb7a71c-ad5b-4bd5-b931-fcc9c21b5f3e', 'clientOrderId': None, 'timestamp': 1609731616717, 'datetime': '2021-01-04T03:40:16.717Z', 'lastTradeTimestamp': 1609731637517, 'symbol': 'ETH/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 1001.75, 'stopPrice': None, 'triggerPrice': None, 'amount': 150.0, 'cost': 150262.5, 'average': 1001.75, 'filled': 150.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': '1e76f240-ebac-42d1-951f-7a4115b9509b', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'ETHUSDT', 'price': '1031.80', 'qty': '300.00', 'side': 'Sell', 'isLeverage': '', 'positionIdx': '2', 'orderStatus': 'Cancelled', 'cancelType': 'CancelByUser', 'rejectReason': 'EC_NoError', 'avgPrice': '0', 'leavesQty': '0.00', 'leavesValue': '0', 'cumExecQty': '0.00', 'cumExecValue': '0', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.00', 'takeProfit': '0.00', 'stopLoss': '0.00', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '1025.05', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1609735061190', 'updatedTime': '1609735827101', 'placeType': ''}, 'id': '1e76f240-ebac-42d1-951f-7a4115b9509b', 'clientOrderId': None, 'timestamp': 1609735061190, 'datetime': '2021-01-04T04:37:41.190Z', 'lastTradeTimestamp': 1609735827101, 'symbol': 'ETH/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'sell', 'price': 1031.8, 'stopPrice': None, 'triggerPrice': None, 'amount': 300.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 0.0, 'status': 'canceled', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': 'b9d576bc-2a99-4fb9-9abb-cad216f74315', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'ETHUSDT', 'price': '1043.00', 'qty': '300.00', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '2', 'orderStatus': 'Filled', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '1042.98331', 'leavesQty': '0.00', 'leavesValue': '0', 'cumExecQty': '300.00', 'cumExecValue': '312894.994', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.00', 'takeProfit': '0.00', 'stopLoss': '0.00', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '1043.35', 'reduceOnly': True, 'closeOnTrigger': True, 'createdTime': '1609737449082', 'updatedTime': '1609737450896', 'placeType': ''}, 'id': 'b9d576bc-2a99-4fb9-9abb-cad216f74315', 'clientOrderId': None, 'timestamp': 1609737449082, 'datetime': '2021-01-04T05:17:29.082Z', 'lastTradeTimestamp': 1609737450896, 'symbol': 'ETH/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': True, 'side': 'buy', 'price': 1043.0, 'stopPrice': None, 'triggerPrice': None, 'amount': 300.0, 'cost': 312894.994, 'average': 1042.9833133333334, 'filled': 300.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': 'f5534c8c-8886-4e14-8f84-1f73e5cc68e3', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'ETHUSDT', 'price': '1062.50', 'qty': '300.00', 'side': 'Sell', 'isLeverage': '', 'positionIdx': '1', 'orderStatus': 'Filled', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '1062.50', 'leavesQty': '0.00', 'leavesValue': '0', 'cumExecQty': '300.00', 'cumExecValue': '318750', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.00', 'takeProfit': '0.00', 'stopLoss': '0.00', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '1055.35', 'reduceOnly': True, 'closeOnTrigger': True, 'createdTime': '1609737823074', 'updatedTime': '1609738162607', 'placeType': ''}, 'id': 'f5534c8c-8886-4e14-8f84-1f73e5cc68e3', 'clientOrderId': None, 'timestamp': 1609737823074, 'datetime': '2021-01-04T05:23:43.074Z', 'lastTradeTimestamp': 1609738162607, 'symbol': 'ETH/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': True, 'side': 'sell', 'price': 1062.5, 'stopPrice': None, 'triggerPrice': None, 'amount': 300.0, 'cost': 318750.0, 'average': 1062.5, 'filled': 300.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': '802aea43-e592-4260-a2ad-bd3aa895ef97', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'ETHUSDT', 'price': '1117.00', 'qty': '150.00', 'side': 'Sell', 'isLeverage': '', 'positionIdx': '2', 'orderStatus': 'Filled', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '1117.00', 'leavesQty': '0.00', 'leavesValue': '0', 'cumExecQty': '150.00', 'cumExecValue': '167550', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.00', 'takeProfit': '0.00', 'stopLoss': '0.00', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '1115.00', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1609741358643', 'updatedTime': '1609741360042', 'placeType': ''}, 'id': '802aea43-e592-4260-a2ad-bd3aa895ef97', 'clientOrderId': None, 'timestamp': 1609741358643, 'datetime': '2021-01-04T06:22:38.643Z', 'lastTradeTimestamp': 1609741360042, 'symbol': 'ETH/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'sell', 'price': 1117.0, 'stopPrice': None, 'triggerPrice': None, 'amount': 150.0, 'cost': 167550.0, 'average': 1117.0, 'filled': 150.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': 'bdd2e06d-e012-4619-bb3b-931cf9820023', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'ETHUSDT', 'price': '1103.00', 'qty': '300.00', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '2', 'orderStatus': 'Filled', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '1103.00', 'leavesQty': '0.00', 'leavesValue': '0', 'cumExecQty': '300.00', 'cumExecValue': '330900', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.00', 'takeProfit': '0.00', 'stopLoss': '0.00', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '1113.70', 'reduceOnly': True, 'closeOnTrigger': True, 'createdTime': '1609741417324', 'updatedTime': '1609743454793', 'placeType': ''}, 'id': 'bdd2e06d-e012-4619-bb3b-931cf9820023', 'clientOrderId': None, 'timestamp': 1609741417324, 'datetime': '2021-01-04T06:23:37.324Z', 'lastTradeTimestamp': 1609743454793, 'symbol': 'ETH/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': True, 'side': 'buy', 'price': 1103.0, 'stopPrice': None, 'triggerPrice': None, 'amount': 300.0, 'cost': 330900.0, 'average': 1103.0, 'filled': 300.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': '4f2fac31-6942-4d3e-9058-4cebd69d09ff', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'ETHUSDT', 'price': '1129.00', 'qty': '150.00', 'side': 'Sell', 'isLeverage': '', 'positionIdx': '2', 'orderStatus': 'Filled', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '1129.00', 'leavesQty': '0.00', 'leavesValue': '0', 'cumExecQty': '150.00', 'cumExecValue': '169350', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.00', 'takeProfit': '0.00', 'stopLoss': '0.00', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '1127.50', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1609741514765', 'updatedTime': '1609741567669', 'placeType': ''}, 'id': '4f2fac31-6942-4d3e-9058-4cebd69d09ff', 'clientOrderId': None, 'timestamp': 1609741514765, 'datetime': '2021-01-04T06:25:14.765Z', 'lastTradeTimestamp': 1609741567669, 'symbol': 'ETH/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'sell', 'price': 1129.0, 'stopPrice': None, 'triggerPrice': None, 'amount': 150.0, 'cost': 169350.0, 'average': 1129.0, 'filled': 150.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': 'f6e5e19a-e5be-41d1-9514-4ef3e544f15f', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'ETHUSDT', 'price': '912.00', 'qty': '150.00', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '1', 'orderStatus': 'Cancelled', 'cancelType': 'CancelByUser', 'rejectReason': 'EC_NoError', 'avgPrice': '0', 'leavesQty': '0.00', 'leavesValue': '0', 'cumExecQty': '0.00', 'cumExecValue': '0', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.00', 'takeProfit': '0.00', 'stopLoss': '0.00', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '935.90', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1609753320080', 'updatedTime': '1609753541978', 'placeType': ''}, 'id': 'f6e5e19a-e5be-41d1-9514-4ef3e544f15f', 'clientOrderId': None, 'timestamp': 1609753320080, 'datetime': '2021-01-04T09:42:00.080Z', 'lastTradeTimestamp': 1609753541978, 'symbol': 'ETH/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 912.0, 'stopPrice': None, 'triggerPrice': None, 'amount': 150.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 0.0, 'status': 'canceled', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': '92b51dc0-1cf3-43a6-89e5-5fce8d304ce3', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'SHIB1000USDT', 'price': '0.045270', 'qty': '200000', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '1', 'orderStatus': 'Filled', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '0.045270', 'leavesQty': '0', 'leavesValue': '0', 'cumExecQty': '200000', 'cumExecValue': '9054', 'cumExecFee': '-2.2635', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.000000', 'takeProfit': '0.000000', 'stopLoss': '0.000000', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '0.000000', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1638340273637', 'updatedTime': '1638340286475', 'placeType': ''}, 'id': '92b51dc0-1cf3-43a6-89e5-5fce8d304ce3', 'clientOrderId': None, 'timestamp': 1638340273637, 'datetime': '2021-12-01T06:31:13.637Z', 'lastTradeTimestamp': 1638340286475, 'symbol': 'SHIB1000/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 0.04527, 'stopPrice': None, 'triggerPrice': None, 'amount': 200000.0, 'cost': 9054.0, 'average': 0.04527, 'filled': 200000.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': -2.2635, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': -2.2635, 'currency': 'USDT'}]}, {'info': {'orderId': 'a09a9b50-fe14-44d7-82db-f6aa975ece52', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'SHIB1000USDT', 'price': '0.048000', 'qty': '200000', 'side': 'Sell', 'isLeverage': '', 'positionIdx': '1', 'orderStatus': 'Cancelled', 'cancelType': 'CancelAllBeforeLiq', 'rejectReason': 'EC_PerCancelRequest', 'avgPrice': '0', 'leavesQty': '0', 'leavesValue': '0', 'cumExecQty': '0', 'cumExecValue': '0', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.000000', 'takeProfit': '0.000000', 'stopLoss': '0.000000', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '0.000000', 'reduceOnly': True, 'closeOnTrigger': True, 'createdTime': '1638341761186', 'updatedTime': '1638414601153', 'placeType': ''}, 'id': 'a09a9b50-fe14-44d7-82db-f6aa975ece52', 'clientOrderId': None, 'timestamp': 1638341761186, 'datetime': '2021-12-01T06:56:01.186Z', 'lastTradeTimestamp': 1638414601153, 'symbol': 'SHIB1000/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': True, 'side': 'sell', 'price': 0.048, 'stopPrice': None, 'triggerPrice': None, 'amount': 200000.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 0.0, 'status': 'canceled', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': '5d003ff2-4dc2-4e81-b635-a01e50f1711e', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'SHIB1000USDT', 'price': '0.041235', 'qty': '200000', 'side': 'Sell', 'isLeverage': '', 'positionIdx': '1', 'orderStatus': 'Filled', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '0.040330', 'leavesQty': '0', 'leavesValue': '0', 'cumExecQty': '200000', 'cumExecValue': '8066', 'cumExecFee': '6.0495', 'timeInForce': 'FOK', 'orderType': 'Market', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.041233', 'takeProfit': '0.000000', 'stopLoss': '0.000000', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '0.000000', 'reduceOnly': True, 'closeOnTrigger': True, 'createdTime': '1638414601164', 'updatedTime': '1638414601164', 'placeType': ''}, 'id': '5d003ff2-4dc2-4e81-b635-a01e50f1711e', 'clientOrderId': None, 'timestamp': 1638414601164, 'datetime': '2021-12-02T03:10:01.164Z', 'lastTradeTimestamp': 1638414601164, 'symbol': 'SHIB1000/USDT:USDT', 'type': 'market', 'timeInForce': 'FOK', 'postOnly': False, 'reduceOnly': True, 'side': 'sell', 'price': 0.041235, 'stopPrice': 0.041233, 'triggerPrice': 0.041233, 'amount': 200000.0, 'cost': 8066.0, 'average': 0.04033, 'filled': 200000.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': 6.0495, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 6.0495, 'currency': 'USDT'}]}, {'info': {'orderId': '6dd7b512-5516-4383-85e1-66a31bc6e410', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'BSWUSDT', 'price': '0.1700', 'qty': '100', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '0', 'orderStatus': 'Cancelled', 'cancelType': 'CancelByUser', 'rejectReason': 'EC_PerCancelRequest', 'avgPrice': '0', 'leavesQty': '0', 'leavesValue': '0', 'cumExecQty': '0', 'cumExecValue': '0', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.0000', 'takeProfit': '0.0000', 'stopLoss': '0.0000', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '0.0000', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1681267968520', 'updatedTime': '1681267977944', 'placeType': ''}, 'id': '6dd7b512-5516-4383-85e1-66a31bc6e410', 'clientOrderId': None, 'timestamp': 1681267968520, 'datetime': '2023-04-12T02:52:48.520Z', 'lastTradeTimestamp': 1681267977944, 'symbol': 'BSW/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 0.17, 'stopPrice': None, 'triggerPrice': None, 'amount': 100.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 0.0, 'status': 'canceled', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': 'e72e621c-e09a-4dc8-96a7-6e892879d290', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'BSWUSDT', 'price': '0.1700', 'qty': '100', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '0', 'orderStatus': 'Cancelled', 'cancelType': 'CancelByUser', 'rejectReason': 'EC_PerCancelRequest', 'avgPrice': '0', 'leavesQty': '0', 'leavesValue': '0', 'cumExecQty': '0', 'cumExecValue': '0', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.0000', 'takeProfit': '0.0000', 'stopLoss': '0.0000', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '0.0000', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1681268201148', 'updatedTime': '1681268210717', 'placeType': ''}, 'id': 'e72e621c-e09a-4dc8-96a7-6e892879d290', 'clientOrderId': None, 'timestamp': 1681268201148, 'datetime': '2023-04-12T02:56:41.148Z', 'lastTradeTimestamp': 1681268210717, 'symbol': 'BSW/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 0.17, 'stopPrice': None, 'triggerPrice': None, 'amount': 100.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 0.0, 'status': 'canceled', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': '0c5cd103-df4c-4e44-844f-a7c12d722f7f', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'BSWUSDT', 'price': '0.1600', 'qty': '100', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '0', 'orderStatus': 'Cancelled', 'cancelType': 'CancelByUser', 'rejectReason': 'EC_PerCancelRequest', 'avgPrice': '0', 'leavesQty': '0', 'leavesValue': '0', 'cumExecQty': '0', 'cumExecValue': '0', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.0000', 'takeProfit': '0.0000', 'stopLoss': '0.0000', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '0.0000', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1681280873389', 'updatedTime': '1681282455316', 'placeType': ''}, 'id': '0c5cd103-df4c-4e44-844f-a7c12d722f7f', 'clientOrderId': None, 'timestamp': 1681280873389, 'datetime': '2023-04-12T06:27:53.389Z', 'lastTradeTimestamp': 1681282455316, 'symbol': 'BSW/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 0.16, 'stopPrice': None, 'triggerPrice': None, 'amount': 100.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 0.0, 'status': 'canceled', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': '60264d64-e12d-4d51-9a41-6c9ba9e5dfc8', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'BSWUSDT', 'price': '0.1700', 'qty': '100', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '0', 'orderStatus': 'Cancelled', 'cancelType': 'CancelByUser', 'rejectReason': 'EC_PerCancelRequest', 'avgPrice': '0', 'leavesQty': '0', 'leavesValue': '0', 'cumExecQty': '0', 'cumExecValue': '0', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.0000', 'takeProfit': '0.0000', 'stopLoss': '0.0000', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '0.0000', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1681282771566', 'updatedTime': '1681282857851', 'placeType': ''}, 'id': '60264d64-e12d-4d51-9a41-6c9ba9e5dfc8', 'clientOrderId': None, 'timestamp': 1681282771566, 'datetime': '2023-04-12T06:59:31.566Z', 'lastTradeTimestamp': 1681282857851, 'symbol': 'BSW/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 0.17, 'stopPrice': None, 'triggerPrice': None, 'amount': 100.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 0.0, 'status': 'canceled', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}, {'info': {'orderId': 'b1a18135-5982-4758-ada4-58026d1a2c8a', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'OPUSDT', 'price': '2.1104', 'qty': '1.0', 'side': 'Sell', 'isLeverage': '', 'positionIdx': '0', 'orderStatus': 'Filled', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '2.220720000', 'leavesQty': '0.0', 'leavesValue': '0', 'cumExecQty': '1.0', 'cumExecValue': '2.22072', 'cumExecFee': '0.00133244', 'timeInForce': 'IOC', 'orderType': 'Market', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.0000', 'takeProfit': '0.0000', 'stopLoss': '0.0000', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '0.0000', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1681285869078', 'updatedTime': '1681285869080', 'placeType': ''}, 'id': 'b1a18135-5982-4758-ada4-58026d1a2c8a', 'clientOrderId': None, 'timestamp': 1681285869078, 'datetime': '2023-04-12T07:51:09.078Z', 'lastTradeTimestamp': 1681285869080, 'symbol': 'OP/USDT:USDT', 'type': 'market', 'timeInForce': 'IOC', 'postOnly': False, 'reduceOnly': False, 'side': 'sell', 'price': 2.1104, 'stopPrice': None, 'triggerPrice': None, 'amount': 1.0, 'cost': 2.22072, 'average': 2.22072, 'filled': 1.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': 0.00133244, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.00133244, 'currency': 'USDT'}]}, {'info': {'orderId': 'df153856-c4eb-464d-a6d8-a0c90b71ffd8', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'OPUSDT', 'price': '2.2193', 'qty': '1.0', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '0', 'orderStatus': 'Filled', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '2.21930000', 'leavesQty': '0.0', 'leavesValue': '0', 'cumExecQty': '1.0', 'cumExecValue': '2.2193', 'cumExecFee': '0.00022193', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.0000', 'takeProfit': '0.0000', 'stopLoss': '0.0000', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '0.0000', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1681286128157', 'updatedTime': '1681287714520', 'placeType': ''}, 'id': 'df153856-c4eb-464d-a6d8-a0c90b71ffd8', 'clientOrderId': None, 'timestamp': 1681286128157, 'datetime': '2023-04-12T07:55:28.157Z', 'lastTradeTimestamp': 1681287714520, 'symbol': 'OP/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 2.2193, 'stopPrice': None, 'triggerPrice': None, 'amount': 1.0, 'cost': 2.2193, 'average': 2.2193, 'filled': 1.0, 'remaining': 0.0, 'status': 'closed', 'fee': {'cost': 0.00022193, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.00022193, 'currency': 'USDT'}]}, {'info': {'orderId': 'f8c8e4f8-8080-4c76-b0b7-9137e830f169', 'orderLinkId': '', 'blockTradeId': '', 'symbol': 'OPUSDT', 'price': '2.0000', 'qty': '1.0', 'side': 'Buy', 'isLeverage': '', 'positionIdx': '0', 'orderStatus': 'New', 'cancelType': 'UNKNOWN', 'rejectReason': 'EC_NoError', 'avgPrice': '0', 'leavesQty': '1.0', 'leavesValue': '2', 'cumExecQty': '0.0', 'cumExecValue': '0', 'cumExecFee': '0', 'timeInForce': 'GTC', 'orderType': 'Limit', 'stopOrderType': 'UNKNOWN', 'orderIv': '', 'triggerPrice': '0.0000', 'takeProfit': '0.0000', 'stopLoss': '0.0000', 'tpTriggerBy': 'UNKNOWN', 'slTriggerBy': 'UNKNOWN', 'triggerDirection': '0', 'triggerBy': 'UNKNOWN', 'lastPriceOnCreated': '0.0000', 'reduceOnly': False, 'closeOnTrigger': False, 'createdTime': '1681370337308', 'updatedTime': '1681370337310', 'placeType': ''}, 'id': 'f8c8e4f8-8080-4c76-b0b7-9137e830f169', 'clientOrderId': None, 'timestamp': 1681370337308, 'datetime': '2023-04-13T07:18:57.308Z', 'lastTradeTimestamp': 1681370337310, 'symbol': 'OP/USDT:USDT', 'type': 'limit', 'timeInForce': 'GTC', 'postOnly': False, 'reduceOnly': False, 'side': 'buy', 'price': 2.0, 'stopPrice': None, 'triggerPrice': None, 'amount': 1.0, 'cost': 0.0, 'average': None, 'filled': 0.0, 'remaining': 1.0, 'status': 'open', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}]
        okx:
        okcはfetchOrdersが未対応でcanceled orderが取れない。
        [{'info': {'accFillSz': '0', 'algoClOrdId': '', 'algoId': '', 'avgPx': '', 'cTime': '1681371154245', 'cancelSource': '', 'cancelSourceReason': '', 'category': 'normal', 'ccy': '', 'clOrdId': '', 'fee': '0', 'feeCcy': 'USDT', 'fillPx': '', 'fillSz': '0', 'fillTime': '', 'instId': 'DOT-USDT-SWAP', 'instType': 'SWAP', 'lever': '3', 'ordId': '566646923047145473', 'ordType': 'limit', 'pnl': '0', 'posSide': 'net', 'px': '6', 'quickMgnType': '', 'rebate': '0', 'rebateCcy': 'USDT', 'reduceOnly': 'false', 'side': 'buy', 'slOrdPx': '', 'slTriggerPx': '', 'slTriggerPxType': '', 'source': '', 'state': 'live', 'sz': '1', 'tag': '', 'tdMode': 'cross', 'tgtCcy': '', 'tpOrdPx': '', 'tpTriggerPx': '', 'tpTriggerPxType': '', 'tradeId': '', 'uTime': '1681371154245'}, 'id': '566646923047145473', 'clientOrderId': None, 'timestamp': 1681371154245, 'datetime': '2023-04-13T07:32:34.245Z', 'lastTradeTimestamp': None, 'symbol': 'DOT/USDT:USDT', 'type': 'limit', 'timeInForce': None, 'postOnly': None, 'side': 'buy', 'price': 6.0, 'stopLossPrice': None, 'takeProfitPrice': None, 'stopPrice': None, 'triggerPrice': None, 'average': None, 'cost': 0.0, 'amount': 1.0, 'filled': 0.0, 'remaining': 1.0, 'status': 'open', 'fee': {'cost': 0.0, 'currency': 'USDT'}, 'trades': [], 'reduceOnly': False, 'fees': [{'cost': 0.0, 'currency': 'USDT'}]}]
        '''
        
        orders = None
        if ex_name == 'binance':
            orders = await self.ccxt_exchanges['binance'].fapiPrivateGetAllOrders()
            print(orders)
        elif ex_name == 'okx':
            opens = await self.ccxt_exchanges['okx'].fetchOpenOrders()
            closed = await self.ccxt_exchanges['okx'].fetchClosedOrders()
            return {'open_orders':opens, 'closed_orders':closed}
        else:
            orders = await self.ccxt_exchanges[ex_name].fetch_orders()
        return orders

        

    async def send_order(self, ex_name, symbol, order_type:str, side:str, price=None, amount=None):
        """
        指定されたsymbolに対して、指定されたorder_typeの注文を出し、約定情報を返す関数

        Args:
            symbol (str): 注文するトレードペアのシンボル
            order_type (str): 'limit'または'market'のいずれか。注文タイプを指定する。
            price (float, optional): リミット注文の場合、注文価格を指定する。マーケット注文の場合は不要。
            amount (float, optional): 注文する数量を指定する。リミット注文の場合、base通貨での数量を指定する。
                                    マーケット注文の場合は、base通貨またはquote通貨での数量を指定できる。

        Returns:
            dict: 約定情報を含む辞書。注文が失敗した場合はNoneを返す。
            binance: 
            limit: {'orderId': '4695181725', 'symbol': 'ALICEUSDT', 'status': 'NEW', 'clientOrderId': '3OBMscMBHWcBXmXnzJ7deT', 'price': '1', 'avgPrice': '0.0000', 'origQty': '10', 'executedQty': '0', 'cumQty': '0', 'cumQuote': '0', 'timeInForce': 'GTC', 'type': 'LIMIT', 'reduceOnly': False, 'closePosition': False, 'side': 'BUY', 'positionSide': 'BOTH', 'stopPrice': '0', 'workingType': 'CONTRACT_PRICE', 'priceProtect': False, 'origType': 'LIMIT', 'updateTime': '1681263917931'}
            market: {'orderId': '9446494975', 'symbol': 'TRXUSDT', 'status': 'NEW', 'clientOrderId': 'Y4QrMXGPVAkCTsllqGLXsV', 'price': '0', 'avgPrice': '0.00000', 'origQty': '100', 'executedQty': '0', 'cumQty': '0', 'cumQuote': '0', 'timeInForce': 'GTC', 'type': 'MARKET', 'reduceOnly': False, 'closePosition': False, 'side': 'SELL', 'positionSide': 'BOTH', 'stopPrice': '0', 'workingType': 'CONTRACT_PRICE', 'priceProtect': False, 'origType': 'MARKET', 'updateTime': '1681288077482'}
            bybit:
            limit: {'info': {'orderId': '0c5cd103-df4c-4e44-844f-a7c12d722f7f', 'orderLinkId': ''}, 'id': '0c5cd103-df4c-4e44-844f-a7c12d722f7f', 'clientOrderId': None, 'timestamp': None, 'datetime': None, 'lastTradeTimestamp': None, 'symbol': None, 'type': None, 'timeInForce': None, 'postOnly': None, 'reduceOnly': None, 'side': None, 'price': None, 'stopPrice': None, 'triggerPrice': None, 'amount': None, 'cost': None, 'average': None, 'filled': None, 'remaining': None, 'status': None, 'fee': None, 'trades': [], 'fees': []}
            market: {'info': {'orderId': 'b1a18135-5982-4758-ada4-58026d1a2c8a', 'orderLinkId': ''}, 'id': 'b1a18135-5982-4758-ada4-58026d1a2c8a', 'clientOrderId': None, 'timestamp': None, 'datetime': None, 'lastTradeTimestamp': None, 'symbol': None, 'type': None, 'timeInForce': None, 'postOnly': None, 'reduceOnly': None, 'side': None, 'price': None, 'stopPrice': None, 'triggerPrice': None, 'amount': None, 'cost': None, 'average': None, 'filled': None, 'remaining': None, 'status': None, 'fee': None, 'trades': [], 'fees': []}
            okx:
            limit: {'info': {'clOrdId': 'e847386590ce4dBCd067c185e0d4da43', 'ordId': '566281938647322631', 'sCode': '0', 'sMsg': 'Order placed', 'tag': 'e847386590ce4dBC'}, 'id': '566281938647322631', 'clientOrderId': 'e847386590ce4dBCd067c185e0d4da43', 'timestamp': None, 'datetime': None, 'lastTradeTimestamp': None, 'symbol': 'BSV/USDT:USDT', 'type': 'limit', 'timeInForce': None, 'postOnly': None, 'side': 'sell', 'price': None, 'stopLossPrice': None, 'takeProfitPrice': None, 'stopPrice': None, 'triggerPrice': None, 'average': None, 'cost': None, 'amount': None, 'filled': None, 'remaining': None, 'status': None, 'fee': None, 'trades': [], 'reduceOnly': False, 'fees': []}
            market: {'info': {'clOrdId': 'e847386590ce4dBC6b998cb4b173f5e2', 'ordId': '566286360827858944', 'sCode': '0', 'sMsg': 'Order placed', 'tag': 'e847386590ce4dBC'}, 'id': '566286360827858944', 'clientOrderId': 'e847386590ce4dBC6b998cb4b173f5e2', 'timestamp': None, 'datetime': None, 'lastTradeTimestamp': None, 'symbol': 'DOGE/USDT:USDT', 'type': 'market', 'timeInForce': None, 'postOnly': None, 'side': 'sell', 'price': None, 'stopLossPrice': None, 'takeProfitPrice': None, 'stopPrice': None, 'triggerPrice': None, 'average': None, 'cost': None, 'amount': None, 'filled': None, 'remaining': None, 'status': None, 'fee': None, 'trades': [], 'reduceOnly': False, 'fees': []}
        """
        try:
            order = None
            if order_type == 'limit':
                # 価格と数量を指定して注文を出す
                if ex_name=='binance':
                    order = await self.ccxt_exchanges[ex_name].fapiPrivatePostOrder({'symbol':symbol,'type':'LIMIT','side':side.upper(),'price':price,'quantity':amount, 'timeInForce':'GTC'})
                else:
                    order = await self.ccxt_exchanges[ex_name].create_order(symbol, 'limit', side.lower(), amount, price)
                return order
            elif order_type == 'market':
                # 数量を指定して注文を出す
                if ex_name=='binance':
                    order = await self.ccxt_exchanges[ex_name].fapiPrivatePostOrder({'symbol':symbol,'type':'MARKET','side':side.upper(), 'quantity':amount})
                else:
                    order = await self.ccxt_exchanges[ex_name].create_market_order(symbol, side, amount)
                return order
            else:
                raise ValueError('Invalid order type')
        except ccxt.InsufficientFunds as e:
            # 残高不足の場合はエラーを出す
            print('Insufficient funds:', e)
            CommunicationData.add_message('Error', 'CCXTRestAPI', 'send_order', e)
            return None
        except ccxt.InvalidOrder as e:
            # 注文が不正
            print('Invalid order:', e)
            CommunicationData.add_message('Error', 'CCXTRestAPI', 'send_order', e)
            return None


    async def cancel_order(self, ex_name, symbol, order_id):
        '''
        binance:
        {'orderId': '4695200291', 'symbol': 'ALICEUSDT', 'status': 'CANCELED', 'clientOrderId': 'ZUaqCp5xEBjTSpzJlk1mZC', 'price': '1', 'avgPrice': '0.0000', 'origQty': '10', 'executedQty': '0', 'cumQty': '0', 'cumQuote': '0', 'timeInForce': 'GTC', 'type': 'LIMIT', 'reduceOnly': False, 'closePosition': False, 'side': 'BUY', 'positionSide': 'BOTH', 'stopPrice': '0', 'workingType': 'CONTRACT_PRICE', 'priceProtect': False, 'origType': 'LIMIT', 'updateTime': '1681264592891'}
        bybit:
        {'info': {'orderId': '0c5cd103-df4c-4e44-844f-a7c12d722f7f', 'orderLinkId': ''}, 'id': '0c5cd103-df4c-4e44-844f-a7c12d722f7f', 'clientOrderId': None, 'timestamp': None, 'datetime': None, 'lastTradeTimestamp': None, 'symbol': 'BSW/USDT:USDT', 'type': None, 'timeInForce': None, 'postOnly': None, 'reduceOnly': None, 'side': None, 'price': None, 'stopPrice': None, 'triggerPrice': None, 'amount': None, 'cost': None, 'average': None, 'filled': None, 'remaining': None, 'status': None, 'fee': None, 'trades': [], 'fees': []}
        okx:
        {'info': {'clOrdId': 'e847386590ce4dBCd067c185e0d4da43', 'ordId': '566281938647322631', 'sCode': '0', 'sMsg': ''}, 'id': '566281938647322631', 'clientOrderId': 'e847386590ce4dBCd067c185e0d4da43', 'timestamp': None, 'datetime': None, 'lastTradeTimestamp': None, 'symbol': 'BSV/USDT:USDT', 'type': None, 'timeInForce': None, 'postOnly': None, 'side': None, 'price': None, 'stopLossPrice': None, 'takeProfitPrice': None, 'stopPrice': None, 'triggerPrice': None, 'average': None, 'cost': None, 'amount': None, 'filled': None, 'remaining': None, 'status': None, 'fee': None, 'trades': [], 'reduceOnly': False, 'fees': []}
        '''
        res = None
        try:
            if ex_name == 'binance':
                res = await self.ccxt_exchanges[ex_name].fapiPrivateDeleteOrder({
                    'symbol': symbol,
                    'orderId': order_id,
                })
            else:
                res = await self.ccxt_exchanges[ex_name].cancel_order(order_id, symbol)
        except Exception as e:
            print('Cancel order eror:', e)
            CommunicationData.add_message('Error', 'CCXTRestAPI', 'cancel_order', e)
        return res

    
    async def binance_get_trades(self):
        '''
        [{'symbol': 'TRXUSDT', 'id': '359484450', 'orderId': '9446494975', 'side': 'SELL', 'price': '0.06381', 'qty': '100', 'realizedPnl': '0', 'marginAsset': 'USDT', 'quoteQty': '6.38100', 'commission': '0.00255239', 'commissionAsset': 'USDT', 'time': '1681288077482', 'positionSide': 'BOTH', 'maker': False, 'buyer': False}]
        '''
        res = await self.ccxt_exchanges['binance'].fapiPrivateGetUserTrades()
        return res

    async def get_trades(self, ex_name):
        '''
        okx:
        {'code': '0', 'data': [{'side': 'buy', 'fillSz': '1', 'fillPx': '6.802', 'fee': '-0.003401', 'ordId': '566994268746092548', 'instType': 'SWAP', 'instId': 'DOT-USDT-SWAP', 'clOrdId': '', 'posSide': 'net', 'billId': '566994268754481166', 'tag': '', 'fillTime': '1681453967915', 'execType': 'T', 'tradeId': '151704912', 'feeCcy': 'USDT', 'ts': '1681453967915'}, {'side': 'sell', 'fillSz': '10', 'fillPx': '0.082', 'fee': '-0.00082', 'ordId': '566291942305632275', 'feeRate': '-0.001', 'instType': 'SPOT', 'instId': 'DOGE-USDT', 'clOrdId': '', 'posSide': 'net', 'billId': '566291942314020871', 'tag': '', 'fillTime': '1681286520242', 'execType': 'T', 'tradeId': '169912021', 'feeCcy': 'USDT', 'ts': '1681286520243'}, {'side': 'buy', 'fillSz': '10', 'fillPx': '0.0819', 'fee': '-0.4095', 'ordId': '566290831947534336', 'instType': 'SWAP', 'instId': 'DOGE-USDT-SWAP', 'clOrdId': '', 'posSide': 'net', 'billId': '566290831955922955', 'tag': '', 'fillTime': '1681286255513', 'execType': 'T', 'tradeId': '224720485', 'feeCcy': 'USDT', 'ts': '1681286255513'}, {'side': 'buy', 'fillSz': '10', 'fillPx': '0.08185', 'fee': '-0.008', 'ordId': '566288611784986625', 'feeRate': '-0.0008', 'instType': 'SPOT', 'instId': 'DOGE-USDT', 'clOrdId': '', 'posSide': 'net', 'billId': '566288813291933697', 'tag': '', 'fillTime': '1681285774225', 'execType': 'M', 'tradeId': '169910296', 'feeCcy': 'DOGE', 'ts': '1681285774226'}, {'side': 'sell', 'fillSz': '2', 'fillPx': '0.08185', 'fee': '-0.08185', 'ordId': '566286360827858944', 'instType': 'SWAP', 'instId': 'DOGE-USDT-SWAP', 'clOrdId': 'e847386590ce4dBC6b998cb4b173f5e2', 'posSide': 'net', 'billId': '566286360836247561', 'tag': 'e847386590ce4dBC', 'fillTime': '1681285189514', 'execType': 'T', 'tradeId': '224719298', 'feeCcy': 'USDT', 'ts': '1681285189515'}, {'side': 'sell', 'fillSz': '4', 'fillPx': '0.08186', 'fee': '-0.16372', 'ordId': '566286360827858944', 'instType': 'SWAP', 'instId': 'DOGE-USDT-SWAP', 'clOrdId': 'e847386590ce4dBC6b998cb4b173f5e2', 'posSide': 'net', 'billId': '566286360836247560', 'tag': 'e847386590ce4dBC', 'fillTime': '1681285189514', 'execType': 'T', 'tradeId': '224719297', 'feeCcy': 'USDT', 'ts': '1681285189515'}, {'side': 'sell', 'fillSz': '1', 'fillPx': '0.08186', 'fee': '-0.04093', 'ordId': '566286360827858944', 'instType': 'SWAP', 'instId': 'DOGE-USDT-SWAP', 'clOrdId': 'e847386590ce4dBC6b998cb4b173f5e2', 'posSide': 'net', 'billId': '566286360836247559', 'tag': 'e847386590ce4dBC', 'fillTime': '1681285189514', 'execType': 'T', 'tradeId': '224719296', 'feeCcy': 'USDT', 'ts': '1681285189515'}, {'side': 'sell', 'fillSz': '1', 'fillPx': '0.08186', 'fee': '-0.04093', 'ordId': '566286360827858944', 'instType': 'SWAP', 'instId': 'DOGE-USDT-SWAP', 'clOrdId': 'e847386590ce4dBC6b998cb4b173f5e2', 'posSide': 'net', 'billId': '566286360836247557', 'tag': 'e847386590ce4dBC', 'fillTime': '1681285189514', 'execType': 'T', 'tradeId': '224719295', 'feeCcy': 'USDT', 'ts': '1681285189515'}, {'side': 'sell', 'fillSz': '1', 'fillPx': '0.08186', 'fee': '-0.04093', 'ordId': '566286360827858944', 'instType': 'SWAP', 'instId': 'DOGE-USDT-SWAP', 'clOrdId': 'e847386590ce4dBC6b998cb4b173f5e2', 'posSide': 'net', 'billId': '566286360836247556', 'tag': 'e847386590ce4dBC', 'fillTime': '1681285189514', 'execType': 'T', 'tradeId': '224719294', 'feeCcy': 'USDT', 'ts': '1681285189515'}, {'side': 'sell', 'fillSz': '1', 'fillPx': '0.08186', 'fee': '-0.04093', 'ordId': '566286360827858944', 'instType': 'SWAP', 'instId': 'DOGE-USDT-SWAP', 'clOrdId': 'e847386590ce4dBC6b998cb4b173f5e2', 'posSide': 'net', 'billId': '566286360836247554', 'tag': 'e847386590ce4dBC', 'fillTime': '1681285189514', 'execType': 'T', 'tradeId': '224719293', 'feeCcy': 'USDT', 'ts': '1681285189515'}], 'msg': ''}
        '''
        res = await crp.ccxt_exchanges[ex_name].private_get_trade_fills()
        return res



    def __del__(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        for k in self.ccxt_exchanges:
            loop.run_until_complete(self.ccxt_exchanges[k].close())
        loop.close()




if __name__ == '__main__':
    #9446494975
    crp = CCXTRestApi()
    #order = asyncio.run(crp.send_order('binance', 'TRXUSDT', 'market', 'sell', 0, 100))
    #print(order)
    res = asyncio.run(crp.fetch_account_balance('bybit'))
    df =CCXTRestApiParser.parse_fetch_account_balance_bybit(res)
    #sele = df[df['side'].notnull()]
    #df.to_csv('./data.csv')
    print(df)
    #time.sleep(3)
    #res = asyncio.run(crp.ccxt_exchanges['binance'].fapiPrivateGetBalance())
    #df = pd.DataFrame(res)
    #print(df)
    #pd.DataFrame(res['assets']).to_csv('./bina_asset.csv')
    #pd.DataFrame(res['positions']).to_csv('./bina_posi.csv')
    #df = pd.DataFrame(res['info']['result']['list'])
    #df.to_csv('./data.csv', index=False)
    #l = list(dir(crp.ccxt_exchanges['okx']))
    #pd.DataFrame(l).to_csv('./funcs.csv')
    #order = asyncio.run(crp.fetch_trade('binance', 'TRX/USDT:USDT', '9446494975'))
    #print(order)

    #df.to_csv('./okx.csv')
   