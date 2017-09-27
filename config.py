#!/usr/bin/python

import json
import log

class config:
    def __init__(self, filename):
        self._readConfig(filename)

    def get(self, name):
        element = self._config
        names = name.split('.')
        for word in names:
            if word in element:
                element = element[word]
            else:
                return None
        if isinstance(element, dict):
            return element
        return str(element)

    def _readConfig(self, filename):
        self._config = {}
        f = open(filename, "r")
        self._config = json.load(f)
        f.close()


if __name__ == "__main__":

    import config

    conf = config.config("config.json")
    capacitance = conf.get("capacitance.gpio.24")

    print "Whole Config:\n" + str(conf._config)

    print "\n\nCapacitance:\n" + capacitance

