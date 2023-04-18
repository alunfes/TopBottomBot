import pandas as pd
import threading


class AccountData:
    lock = threading.Lock()

    @classmethod
    def initialize(cls):
        cls.total_cash = 15000
        cls.cash = {}
        #init holding
        cls.holding_ex_name = []
        cls.holding_symbol = []
        cls.holding_side = []
        cls.holding_price = []
        cls.holding_qty = []
        cls.holding_timestamp = []
        cls.holding_period = []
        cls.holding_unrealized_pnl_usd = []
        cls.holding_unrealized_pnl_ratio = []
        cls.holding_liquidation_price = []
        cls.holding_margin_ratio = []
        #init order
        cls.order_ex_name = []
        cls.order_id = []
        cls.order_symbol = []
        cls.order_side = []
        cls.order_type = []
        cls.order_price = []
        cls.order_avg_price = []
        cls.order_status = []
        cls.order_original_qty = []
        cls.order_executed_qty = []
        cls.order_fee = []
        cls.order_fee_currency = []
        cls.order_ts = []
        #fee
        cls.total_fees = {} #ex_name-symbol, total_fee (取引が発生する度にUSDTベースでのfeeを加算する)
        cls.total_fee = 0
        #performance
        cls.num_trade = 0
        cls.num_win = 0
        cls.total_realized_pnl = 0
        cls.total_unrealized_pnl = 0
        cls.realized_pnls = {} #ex_name-symbol, realized_pnl (positionと反対方向の約定が発生する度にUSDTベースでのrealized pnlを保有銘柄毎に加算する、)
        #log
        cls.total_pnl_log = []
        cls.trades_df = [] #[{ex_name, symbol, entry_price, entry_qty, entry_timestamp, exit_price, exit_timestamp, realzied_pnl}]

        
    
    @classmethod
    def get_holding_df(cls):
        with cls.lock:
            return pd.DataFrame({
                'ex_name':cls.holding_ex_name, 
                'symbol':cls.holding_symbol, 
                'side':cls.hodling_side, 
                'price':cls.holding_price, 
                'qty':cls.holding_qty, 
                'timestamp':cls.holding_timestamp, 
                'period':cls.holding_period, 
                'unrealized_pnl_usd':cls.holding_unrealized_pnl_usd, 
                'unrealized_pnl_ratio':cls.holding_unrealized_pnl_ratio,
                'liquidation_price': cls.holding_liquidation_price,
                'margin_ratio': cls.holding_margin_ratio
                })
    
    @classmethod
    def get_order_df(cls):
        with cls.lock:
            return pd.DataFrame({
                'ex_name': cls.order_ex_name, 
                'id': cls.order_id, 
                'symbol': cls.order_symbol, 
                'side': cls.order_side, 
                'type': cls.order_type, 
                'price': cls.order_price, 
                'avg_price': cls.order_avg_price,
                'status': cls.order_status, 
                'original_qty': cls.order_original_qty, 
                'executed_qty': cls.order_executed_qty,
                'fee': cls.order_fee,
                'fee_currency': cls.order_fee_currency,
                'ts': cls.order_ts
            })
    
    @classmethod
    def add_order(cls, ex_name, id, symbol, side, type, price, avg_price, status, original_qty, executed_qty, fee, fee_currency, timestamp):
        with cls.lock:
            cls.order_ex_name.append(ex_name)
            cls.order_id.append(id)
            cls.order_symbol.append(symbol)
            cls.order_side.append(side)
            cls.order_type.append(type)
            cls.order_price.append(price)
            cls.order_avg_price.append(avg_price)
            cls.order_status.append(status)
            cls.order_original_qty.append(original_qty)
            cls.order_executed_qty.append(executed_qty)
            cls.order_fee.append(fee)
            cls.order_fee_currency.append(fee_currency)
            cls.order_ts.append(timestamp)
    
    @classmethod
    def add_holding(cls, ex_name, symbol, side, price, qty, timestamp, period, unrealized_pnl_usd, unrealized_pnl_ratio, liquidation_price, margin_ratio):
        with cls.lock:
            cls.holding_ex_name.append(ex_name)
            cls.holding_symbol.append(symbol)
            cls.holding_side.append(side)
            cls.holding_price.append(price)
            cls.holding_qty.append(qty)
            cls.holding_timestamp.append(timestamp)
            cls.holding_period.append(period)
            cls.holding_unrealized_pnl_usd.append(unrealized_pnl_usd)
            cls.holding_unrealized_pnl_ratio.append(unrealized_pnl_ratio)
            cls.holding_liquidation_price.append(liquidation_price)
            cls.holding_margin_ratio.append(margin_ratio)

    @classmethod
    def remove_order(cls, order_id):
        with cls.lock:
            try:
                idx = cls.order_id.index(order_id)
                cls.order_ex_name.pop(idx)
                cls.order_id.pop(idx)
                cls.order_symbol.pop(idx)
                cls.order_side.pop(idx)
                cls.order_type.pop(idx)
                cls.order_price.pop(idx)
                cls.order_avg_price.pop(idx)
                cls.order_status.pop(idx)
                cls.order_original_qty.pop(idx)
                cls.order_executed_qty.pop(idx)
                cls.order_fee.pop(idx)
                cls.order_fee_currency.pop(idx)
                cls.order_ts.pop(idx)
            except ValueError:
                print(f"Order ID {order_id} not found.")

    @classmethod
    def remove_holding(cls, symbol):
        with cls.lock:
            try:
                idx = cls.holding_symbol.index(symbol)
                cls.holding_ex_name.pop(idx)
                cls.holding_symbol.pop(idx)
                cls.holding_side.pop(idx)
                cls.holding_price.pop(idx)
                cls.holding_qty.pop(idx)
                cls.holding_timestamp.pop(idx)
                cls.holding_period.pop(idx)
                cls.holding_unrealized_pnl_usd.pop(idx)
                cls.holding_unrealized_pnl_ratio.pop(idx)
                cls.holding_liquidation_price.pop(idx)
                cls.holding_margin_ratio.pop(idx)
            except ValueError:
                print(f"Holding for symbol {symbol} not found.")

    @classmethod
    def update_order(cls, order_id, ex_name=None, symbol=None, side=None, type=None, price=None, avg_price=None, status=None, original_qty=None, executed_qty=None, fee=None, fee_currency=None):
        with cls.lock:
            try:
                idx = cls.order_id.index(order_id)
                if ex_name is not None:
                    cls.order_ex_name[idx] = ex_name
                if symbol is not None:
                    cls.order_symbol[idx] = symbol
                if side is not None:
                    cls.order_side[idx] = side
                if type is not None:
                    cls.order_type[idx] = type
                if price is not None:
                    cls.order_price[idx] = price
                if avg_price is not None:
                    cls.order_avg_price[idx] = avg_price
                if status is not None:
                    cls.order_status[idx] = status
                if original_qty is not None:
                    cls.order_original_qty[idx] = original_qty
                if executed_qty is not None:
                    cls.order_executed_qty[idx] = executed_qty
                if fee is not None:
                    cls.order_fee[idx] = fee
                if fee_currency is not None:
                    cls.order_fee_currency[idx] = fee_currency
            except ValueError:
                print(f"Order ID {order_id} not found.")

    @classmethod
    def update_holding(cls, symbol, ex_name=None, side=None, price=None, qty=None, timestamp=None, period=None, unrealized_pnl_usd=None, unrealized_pnl_ratio=None, liquidation_price=None, margin_ratio=None):
        with cls.lock:
            try:
                idx = cls.holding_symbol.index(symbol)
                if ex_name is not None:
                    cls.holding_ex_name[idx] = ex_name
                if side is not None:
                    cls.holding_side[idx] = side
                if price is not None:
                    cls.holding_price[idx] = price
                if qty is not None:
                    cls.holding_qty[idx] = qty
                if timestamp is not None:
                    cls.holding_timestamp[idx] = timestamp
                if period is not None:
                    cls.holding_period[idx] = period
                if unrealized_pnl_usd is not None:
                    cls.holding_unrealized_pnl_usd[idx] = unrealized_pnl_usd
                if unrealized_pnl_ratio is not None:
                    cls.holding_unrealized_pnl_ratio[idx] = unrealized_pnl_ratio
                if liquidation_price is not None:
                    cls.holding_liquidation_price[idx] = liquidation_price
                if margin_ratio is not None:
                    cls.holding_margin_ratio[idx] = margin_ratio
            except ValueError:
                print(f"Holding for symbol {symbol} not found.")

    @classmethod
    def get_total_cash(cls):
        with cls.lock:
            return cls.total_cash
        
    @classmethod
    def set_total_cash(cls, cash):
        with cls.lock:
            cls.total_cash = cash

    @classmethod
    def get_num_trade(cls):
        with cls.lock:
            return cls.num_trade

    @classmethod
    def set_num_trade(cls, value):
        with cls.lock:
            cls.num_trade = value

    @classmethod
    def get_num_win(cls):
        with cls.lock:
            return cls.num_win

    @classmethod
    def set_num_win(cls, value):
        with cls.lock:
            cls.num_win = value

    @classmethod
    def get_total_realized_pnl(cls):
        with cls.lock:
            return cls.total_realized_pnl

    @classmethod
    def set_total_realized_pnl(cls, value):
        with cls.lock:
            cls.total_realized_pnl = value

    @classmethod
    def get_total_unrealized_pnl(cls):
        with cls.lock:
            return cls.total_unrealized_pnl

    @classmethod
    def set_total_unrealized_pnl(cls, value):
        with cls.lock:
            cls.total_unrealized_pnl = value

    @classmethod
    def get_total_fees(cls, ex_name, symbol):
        with cls.lock:
            key = ex_name+'-'+symbol
            if key in cls.total_fees:
                return cls.total_fees[ex_name+'-'+symbol]
            else:
                return None

    @classmethod
    def set_total_fees(cls, ex_name, symbol, fee):
        with cls.lock:
            cls.total_fees[ex_name+'-'+symbol] = fee

    @classmethod
    def get_total_fee(cls):
        with cls.lock:
            return cls.total_fee

    @classmethod
    def set_total_fee(cls, value):
        with cls.lock:
            cls.total_fee = value

    @classmethod
    def get_total_pnl_log(cls):
        with cls.lock:
            return cls.total_pnl_log

    @classmethod
    def set_total_pnl_log(cls, value):
        with cls.lock:
            cls.total_pnl_log = value
    
    @classmethod
    def get_realized_pnls(cls, ex_name, symbol):
        with cls.lock:
            key = ex_name+'-'+symbol
            if key in cls.realized_pnls:
                return cls.realized_pnls[ex_name+'-'+symbol]
            else:
                return None
    
    @classmethod
    def set_realized_pnls(cls, ex_name, symbol, pnl):
        with cls.lock:
            cls.realized_pnls[ex_name+'-'+symbol] = pnl

    @classmethod
    def get_trades_df(cls):
        with cls.lock:
            return cls.trades_df

    @classmethod
    def set_trades_df(cls, value):
        with cls.lock:
            cls.trades_df = value

        




    