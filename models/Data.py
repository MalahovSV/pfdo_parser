class Data:
    def __init__(self, path):
        with open(path) as f:
            self.login = f.readline()
            self.password = f.readline()
            self.site = f.readline()