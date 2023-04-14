import yaml

class Settings:
    @classmethod
    def initialize(cls):
        cls.exchanges = []
        cls.before_kijun_period = 0
        cls.after_kijun_period = 0
        cls.num_top_bottom_targets = 0
        cls.account_update_freq = 0
        try:
            with open('./ignore/settings.yaml', 'r') as f:
                data = yaml.load(f, Loader=yaml.Loader)
                cls.exchanges = list(data['exchanges'])
                cls.before_kijun_period = int(data['before_kijun_period'])
                cls.after_kijun_period = int(data['after_kijun_period'])
                cls.num_top_bottom_targets = int(data['num_top_bottom_targets'])
                cls.account_update_freq = int(data['account_update_freq'])
        except Exception as e:
            print('Settings.__read_setting.yaml: ', e)
            return None



if __name__ == '__main__':
    Settings.initialize()
    print(Settings.exchanges)