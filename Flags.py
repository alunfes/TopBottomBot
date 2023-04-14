class Flags:
    @classmethod
    def initialize(cls):
        cls._system_flg = True

    @classmethod
    def get_system_flag(cls):
        return cls._system_flg

    @classmethod
    def set_system_flag(cls, value):
        cls._system_flg = value

    system_flag = property(get_system_flag, set_system_flag)
    