#!/usr/bin/python
import RPi.GPIO as GPIO
import time

PUMP_GPIO = (17, 27)
SWEEP_GPIO = (22, 23)

START_TIME = None

# Initialize GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

def turnOn(gpios):
    global START_TIME
    print "Turning on %s" % (str(gpios))
    for gpio in gpios:
        GPIO.output(gpio, True)
    START_TIME = time.time()


def turnOff(gpios):
    global START_TIME
    print "Turning off %s" % (str(gpios))
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
    turnOff(SWEEP_GPIO)
    turnOn(PUMP_GPIO)


def startSweep():
    turnOn(PUMP_GPIO + SWEEP_GPIO)


def stopAll():
    turnOff(PUMP_GPIO + SWEEP_GPIO)


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
