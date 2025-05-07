import datetime

class Logger:
    def __init__(self):
        self.messages = []

    def log(self, message, indentation=0):
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        tabs = '\t' * indentation
        msg = f'[{ts}] - {tabs}{message}'
        self.messages.append(msg)
        print(msg)

    def red(self, message, indentation=0):
        self.log(f'❌ {message}', indentation)

    def green(self, message, indentation=0):
        self.log(f'✅ {message}', indentation)

    def yellow(self, message, indentation=0):
        self.log(f'⚠️ {message}', indentation)

    def blue(self, message, indentation=0):
        self.log(f'🔄 {message}', indentation)

    def dump(self, filepath):
        path = filepath

        if not path:
            path = f'./logs/{datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}.log'

        with open(path, 'w+') as f:
            for message in self.messages:
                f.write(f'{message}\n')

logger = Logger()