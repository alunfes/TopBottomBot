import threading


class CommunicationData:
    lock = threading.Lock()

    @classmethod
    def initialize(cls):
        with cls.lock:
            cls.messages = ['Communication is working properly.']

    @classmethod
    def get_message(cls):
        with cls.lock:
            if len(cls.messages) > 0:
                msg = cls.messages[0]
                del cls.messages[0]
                return msg
            else:
                return None

    @classmethod
    def add_message(cls, msg_type, class_name, func_name, msg):
        with cls.lock:
            cls.messages.append(msg_type+':'+'\n'+ class_name + '.'+func_name+':'+'\n'+msg)