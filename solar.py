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
WATER_GPIO = 24
ROOF_GPIO = 25
RED_LED = 6

targetTemp = 29.5
zipcode = 60007

_lastRunningWaterTemp = 0.0
_lastRunningWaterTime = 0.0

_maxLag = 25200  # 7 hours
_mixTime = 180.0 # 3 minutes
_deltaT = 4.0    # 5 degrees Celsius
_tolerance = 1.25 # +/- temperature tolerance
_state_ = 0
__initialized__ = False


# Between 11PM and 5AM (Coldest Time)
def isNight():
    ts = time.localtime()
    return (ts.tm_hour > 22 or ts.tm_hour < 6)

# Between 10AM and 4PM (Peak Sun)
def isDay():
    ts = time.localtime()
    return (ts.tm_hour < 17 and ts.tm_hour > 9)

def state():
    global _state_
    return _state_


# Get temp from the cache and update the cache if needed/possible
def waterTemp():
    global _lastRunningWaterTemp
    global _lastRunningWaterTime

    # Pump is running, update the cache, stop the pump if needed
    if pump.state() != pump.STATE_OFF and time.time() - pump.getStartTime() > _mixTime:
        _lastRunningWaterTemp = temp.getTempC(WATER_GPIO)
        _lastRunningWaterTime = time.time()
    # If pump isn't running, the temperature is unreliable, start the pump
    if time.time() - _lastRunningWaterTime > _maxLag:
        if pump.state() == pump.STATE_OFF:
            pump.startSolar()
    return _lastRunningWaterTemp

# Returns temperature of the roof
def roofTemp():
    return temp.getTempC(ROOF_GPIO)


# Returns True if the water SHOULD be sent to the panels when the pump is running
def flowThroughCollectors():
    global _state_
    poolTemp = waterTemp()
    roofTempC = roofTemp()

    if _lastRunningWaterTemp == 0.0:
        return False
    
#    log.debug("pool(%0.1f) roof(%0.1f) target(%0.1f) tol(%0.1f) dT(%0.1f) night(%s) day(%s)" % (
#        poolTemp, roofTemp(), targetTemp, _tolerance, _deltaT, str(isNight()), str(isDay())))
    # Cooling mode
    if poolTemp > targetTemp + _tolerance and poolTemp > roofTempC + _deltaT and isNight():
        if _state_ == 1:
            return True
        GPIO.output(RED_LED, True)
        relay.turnOn(SOLAR_RELAY)
        log.info("Cooling - turn on solar panels")
        _state_ = 1
        return True

    # Warming mode
    if poolTemp < targetTemp - _tolerance and poolTemp < roofTempC - _deltaT and isDay():
        if _state_ == 1:
            return True
        GPIO.output(RED_LED, True)
        relay.turnOn([SOLAR_RELAY])
        log.info("Heating - turn on solar panels")
        _state_ = 1
        return True

    relay.turnOff([SOLAR_RELAY])
    GPIO.output(RED_LED, False)
    _state_ = 0 
    return False


# Run the pump if we need to warm or cool the water
def runPumpsIfNeeded():
    solar_on = flowThroughCollectors() # Updates temperature cache
    if solar_on:
        # pumps aren't running, but the water needs to change
        if pump.state() == pump.STATE_OFF:
            log.info("SolarOn, starting pump")
            observation = weather.getCurrentTempC(zipcode)
            if observation < _lastRunningWaterTemp - _deltaT:
                # Run the sweep when it's cool out to keep the deep end warming up too
                pump.startSolarMixing()
            else:
                pump.startSolar()

    # Turn off the pumps when not needed, if started for solar
    elif pump.state() == pump.STATE_SOLAR or pump.state() == pump.STATE_SOLAR_MIXING:
        if time.time() - pump.getStartTime() > _mixTime:
            log.info("SolarOff, stopping pump")
            pump.stopAll()
    return

def setup(conf):
    global __initialized__
    global targetTemp
    global zipcode

    targetTemp = float(conf.get('temp.target'))
    zipcode = int(conf.get('weather.zip'))

    if __initialized__ == True:
        return
    GPIO.setup(RED_LED, GPIO.OUT)
    GPIO.output(RED_LED, False)
    __initialized__ = True
