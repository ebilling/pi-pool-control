#!/usr/bin/python

import RPi.GPIO as GPIO
import time
import temp
import relay
import pump
import config
import weather
import log

SOLAR_RELAY = relay.RELAY3
WATER_GPIO = 25
ROOF_GPIO = 24
RED_LED = 6

zipcode = 60007
targetTemp = 30.0
_deltaT = 2.0    # Minimum difference between roof and pool, degrees Celsius
_tolerance = 0.5 # +/- temperature tolerance
_maxLag = 86400  # 24 hours
_mixTime = 120   # 2 minutes
_minSolarRadiation = 200.0 # 200 Watts/sq-meter

_lastRunningWaterTemp = 0.0
_lastRunningWaterTime = 0.0

_state_ = 0
__initialized__ = False

def state():
    global _state_
    return _state_


# Between 11PM and 5AM (Coldest Time)
def isNight():
    ts = time.localtime()
    return (ts.tm_hour > 22 or ts.tm_hour < 6)


# Anytime there is enough sun to raise the roof temp
def isDay():
    global zipcode
    solRad = weather.getSolarRadiation(zipcode)
    if solRad >= _minSolarRadiation:
        return True
    return False


def runningWaterTemp():
    global _lastRunningWaterTemp
    return _lastRunningWaterTemp


# Get temp from the cache and update the cache if needed/possible
def waterTemp():
    global _lastRunningWaterTemp
    global _lastRunningWaterTime
    t = temp.getTempC(WATER_GPIO)

    # Pump is running, update the cache
    if pump.state() > pump.STATE_OFF:
        _lastRunningWaterTemp = t
        _lastRunningWaterTime = time.time()

    # If pump isn't running, the temperature is unreliable, start the pump
    if time.time() - _lastRunningWaterTime > _maxLag:
        if not pump.Stopped() and pump.state() == pump.STATE_OFF:
            log.debug("Running pump to get updated temperature")
            pump.startSolar()
    return t


# Returns temperature of the roof
def roofTemp():
    return temp.getTempC(ROOF_GPIO)


# Returns True if the water SHOULD be sent to the panels when the pump is running
def flowThroughCollectors():
    global _state_
    poolTemp = runningWaterTemp()
    roofTempC = roofTemp()

    if _lastRunningWaterTemp == 0.0:
        return False

    #log.debug("pool(%0.1f) roof(%0.1f) target(%0.1f) tol(%0.1f) dT(%0.1f) night(%s) day(%s)" % (
    #    poolTemp, roofTemp(), targetTemp, _tolerance, _deltaT, str(isNight()), str(isDay())))

    # Cooling mode
    if poolTemp > targetTemp + _tolerance and poolTemp > roofTempC + _deltaT and isNight():
        if _state_ == 1:
            return True
        log.info("Cooling - turn on solar panels")
        GPIO.output(RED_LED, True)
        relay.turnOn(SOLAR_RELAY)
        _state_ = 1
        return True

    # Warming mode
    if poolTemp < targetTemp - _tolerance and isDay():
        if _state_ == 1:
            return True
        log.info("Heating - turn on solar panels")
        GPIO.output(RED_LED, True)
        relay.turnOn([SOLAR_RELAY])
        _state_ = 1
        return True

    if _state_ != 0:
        relay.turnOff([SOLAR_RELAY])
        GPIO.output(RED_LED, False)
        log.info("Turning off Solar")
        _state_ = 0

    return False


# Run the pump if we need to warm or cool the water
def runPumpsIfNeeded():
    solar_on = flowThroughCollectors() # Updates temperature cache    
    # pumps aren't running, but the water needs to change
    if solar_on and pump.state() == pump.STATE_OFF and not pump.Stopped():
            log.info("SolarOn, starting pump")
            observation = weather.getCurrentTempC(zipcode)
            if observation < _lastRunningWaterTemp - _deltaT:
                # Run the sweep when it's cool out to keep the deep end warming up too
                pump.startSolarMixing()
            else:
                pump.startSolar()
            return True
    return False


def setup(conf):
    global __initialized__, targetTemp, zipcode, _tolerance, _deltaT
    global _maxLag, _mixTime, _lastRunningWaterTime, _lastRunningWaterTemp

    if conf.get('temp.tolerance') != None:
        _tolerance = float(conf.get('temp.tolerance'))
    if conf.get('temp.minDeltaT') != None:
        _deltaT = float(conf.get('temp.minDeltaT'))
    if conf.get('temp.mixTime') != None:
        _mixTime = float(conf.get('temp.mixTime'))
    if conf.get('temp.maxTempRefresh') != None:
        _maxLag = int(conf.get('temp.maxTempRefresh'))
    if conf.get('temp.target') != None:
        targetTemp = float(conf.get('temp.target'))
    if conf.get('temp.minSolarRadiation') != None:
        _minSolarRadiation = float(conf.get('temp.minSolarRadiation'))
    if conf.get('weather.zip') != None:
        zipcode = int(conf.get('weather.zip'))

    if __initialized__ == True:
        return

    _lastRunningWaterTime = time.time()
    _lastRunningWaterTemp = temp.getTempC(WATER_GPIO)
    GPIO.setup(RED_LED, GPIO.OUT)
    GPIO.output(RED_LED, False)

    __initialized__ = True
