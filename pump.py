#!/usr/bin/python
import RPi.GPIO as GPIO
import time

PUMP_GPIO = (17, 27)
SWEEP_GPIO = (22, 23)

START_TIME = None

STATE_OFF = 0
STATE_PUMP = 1
STATE_SWEEP = 2

_state_ = STATE_OFF


# Initialize GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

def state():
    global _state_
    return _state_

def turnOn(gpios):
    global START_TIME
    for gpio in gpios:
        GPIO.output(gpio, True)
    START_TIME = time.time()


def turnOff(gpios):
    global START_TIME
    for gpio in gpios:
        GPIO.output(gpio, False)
    START_TIME = None


def getStartTime():
    global START_TIME    
    return START_TIME


def getStatus(gpios=PUMP_GPIO + SWEEP_GPIO):
    out = list()
    for gpio in gpios:
        out.append(GPIO.input(gpio))
    return out


def startPump():
    global _state_
    turnOff(SWEEP_GPIO)
    turnOn(PUMP_GPIO)
    _state_ = STATE_PUMP

def startSweep():
    global _state_
    turnOn(PUMP_GPIO + SWEEP_GPIO)
    _state_ = STATE_SWEEP

def stopAll():
    global _state_
    turnOff(PUMP_GPIO + SWEEP_GPIO)
    _state_ = STATE_OFF

def setup():
    # Initialize GPIO
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    # Initialize relays
    for gpio in PUMP_GPIO + SWEEP_GPIO:
        GPIO.setup(gpio, GPIO.OUT)
    turnOff(PUMP_GPIO + SWEEP_GPIO)


# Initialize relays
for gpio in PUMP_GPIO + SWEEP_GPIO:
    GPIO.setup(gpio, GPIO.OUT)
turnOff(PUMP_GPIO + SWEEP_GPIO)
