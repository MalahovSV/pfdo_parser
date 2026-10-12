class Data:
    def __init__(self, path):
        with open(path) as f:
            TEMP = f.read().split()
            self.login = TEMP[0]
            self.password = TEMP[1]
            self.site = TEMP[2]