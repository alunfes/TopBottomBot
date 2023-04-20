class ActionData:
    def __init__(self):
        self.actions = []
        
    def add_action(self, action:str, order_id:str, ex_name:str, symbol:str, order_type:str, price:float, qty:float):
        self.actions.append({
            'action': action,
            'order_id': order_id,
            'ex_name': ex_name,
            'symbol': symbol,
            'order_type': order_type,
            'price': price,
            'qty': qty
        })
        
    def get_action(self):
        return self.actions
    

