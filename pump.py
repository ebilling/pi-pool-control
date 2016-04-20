#!/usr/bin/python
import RPi.GPIO as GPIO

PUMP_GPIO = (17, 27)
SWEEP_GPIO = (22, 23)

# Initialize GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

def turnOn(gpios):
    print "Turning on %s" % (str(gpios))
    for gpio in gpios:
        GPIO.output(gpio, True)
    

def turnOff(gpios):
    print "Turning off %s" % (str(gpios))
    for gpio in gpios:
        GPIO.output(gpio, False)


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
