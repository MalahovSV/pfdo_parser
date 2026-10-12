from models.Data import Data

register_data = None

def authorization():
    register_data = Data("./data")
    print(f'log: {register_data.login}\npass: {register_data.password}\nsite: {register_data.site}')

if __name__ == '__main__':
    authorization()
