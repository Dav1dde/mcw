import configparser


class ConfigFile(configparser.ConfigParser):
    def __init__(self, path, *args, **kwargs):
        configparser.ConfigParser.__init__(self, *args, **kwargs)

        self.path = path

        self.server = None
        self.webpanel = None
        self.backup = None

        self.read()

    def read(self):
        with open(self.path) as f:
            self.read_file(f)

        self.server = self['server']
        self.webpanel = self['webpanel']
        self.backup = self['backup']

    def write(self):
        with open(self.path, 'w') as f:
            self.write(f)

