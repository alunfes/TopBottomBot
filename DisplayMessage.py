import threading


class DisplayMessage:
    lock = threading.Lock()

    @classmethod
    def display_message(cls, class_name, func_name, message_type, messages:list):
        '''
        message type=[message, error]
        '''
        with cls.lock:
            separator = '-' if message_type == 'message' else '*'
            print(separator*40)
            print(class_name+'.'+func_name)
            for message in messages:
                print(message)
            print(separator*40)
        

if __name__ == '__main__':
    DisplayMessage.display_message('class', 'func', 'error', ['Order not found', "{'order':123}"])