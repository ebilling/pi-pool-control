#!/usr/bin/python

class config:
    def __init__(self, filename):
        self._readConfig(filename)

    def add(self, name, value):
        name = name.split('.')
        element = self._config
        for i, word in enumerate(name):
            if word not in element:
                if i == len(name)-1:
                    element[word] = value
                else:
                    element[word] = {}
            element = element[word]

    def get(self, name):
        element = self._config
        names = name.split('.')

        for word in names:
            if word in element:
                element = element[word]
            else:
                return None
        return element

    def _readConfig(self, filename):
        self._config = {}
        f = open(filename, "r")
        for line in f:
            line = line.strip()
            if len(line) == 0 or line[0] == '#':
                continue # Skip comments and blank lines            
            (name,value) = line.split('=')
            self.add(name, value)
        f.close()


if __name__ == "__main__":

    import config

    conf = config.config("poold.conf")
    capacitance = conf.get("capacitance")

    print str(conf._config)
    print(str(capacitance))

