#!/usr/bin/python

import RPi.GPIO as GPIO
import time
import log

# GPIO associated with Relay 1-4
RELAY1 = 17
RELAY2 = 27
RELAY3 = 22
RELAY4 = 23

DEBUG = False

RELAYS = [RELAY1, RELAY2, RELAY3, RELAY4]
__initialized__ = False

def turnOn(gpios):
    log.trace("TurnOn(%s):\t" % (str(gpios)))
    for gpio in gpios:
        if DEBUG:
            break
        GPIO.output(gpio, False)


def turnOff(gpios):
    log.trace("TurnOff(%s):\t" % (str(gpios)))
    for gpio in gpios:
        if DEBUG:
            break
        GPIO.output(gpio, True)
    START_TIME = None


def getStatus(gpios):
    out = list()
    for gpio in gpios:
        out.append(GPIO.input(gpio))
    return out


def setup():
    global __initialized__
    if __initialized__:
        return
    
    # Initialize relays
    for gpio in RELAYS:
        GPIO.setup(gpio, GPIO.OUT)
    log.info("Running relay.setup()")
    turnOff(RELAYS)
    __initialized__ = True
