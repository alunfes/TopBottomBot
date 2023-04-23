class ActionData:
    def __init__(self):
        self.actions = []
        
    def add_action(self, action:str, order_id:str, ex_name:str, symbol:str, base_asset:str, quote_asset:str, order_type:str, price:float, qty:float):
        self.actions.append({
            'action': action,
            'order_id': order_id,
            'ex_name': ex_name,
            'symbol': symbol,
            'base_asset':base_asset,
            'quote_asset':quote_asset,
            'order_type': order_type,
            'price': price,
            'qty': qty
        })
        
    def get_action(self):
        return self.actions
    

