class Data:
    def __init__(self, path):
        with open(path) as f:
            self.login, self.password, self.site = f.read().split()