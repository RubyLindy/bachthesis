class StartError(Exception):
    pass

class text:
    def __init__(self, value=''):
        self.value = value

class number:
    def __init__(self, value=0):
        self.value = value
