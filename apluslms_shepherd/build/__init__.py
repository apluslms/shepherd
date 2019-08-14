class TaskResult(object):
    def __init__(self, output, error, code):
        self.output = output
        self.error = error
        self.code = code

    def __str__(self):
        return "output:{}, error message:{}, code:{}".format(self.output, self.error, self.code)
