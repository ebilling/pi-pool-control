#!/usr/bin/python
import RPi.GPIO as GPIO
import relay
import solar
import time
import log

PUMP_GPIO = relay.RELAY1
SWEEP_GPIO = relay.RELAY2

START_TIME = 0.0
STOP_TIME = 0.0

STATE_DISABLED = -1
STATE_OFF = 0
STATE_PUMP = 1
STATE_SWEEP = 2
STATE_SCHEDULED_PUMP = 3
STATE_SCHEDULED_SWEEP = 4
STATE_SOLAR = 5
STATE_SOLAR_MIXING = 6

RUN_TIME = 7200
PUMP_STATUS = '/tmp/pump_status'

_state_ = STATE_OFF

sched_pump_start = None
sched_pump_stop = None
sched_sweep_start = None
sched_sweep_stop = None

def state():
    global _state_
    return _state_


def _setState(state):
    global _state_
    _state_ = state
    tempfile = open(PUMP_STATUS, 'w+')
    tempfile.write(str(_state_))
    tempfile.close()


def setStatePath(path):
    global PUMP_STATUS
    PUMP_STATUS = path

def turnOn(gpios):
    global START_TIME
    relay.turnOn(gpios)
    if state() == STATE_OFF:
        START_TIME = time.time()


def turnOff(gpios):
    relay.turnOff(gpios)


def getStartTime():
    global START_TIME
    return START_TIME


def getStopTime():
    global STOP_TIME    
    return STOP_TIME


def getStatus(gpios=(PUMP_GPIO, SWEEP_GPIO)):
    return relay.getStatus(gpios)


def startSolar():
    startPump()
    _setState(STATE_SOLAR)


def startSolarMixing():
    startSweep()
    _setState(STATE_SOLAR_MIXING)


def startPump():
    turnOff([SWEEP_GPIO])
    turnOn([PUMP_GPIO])
    _setState(STATE_PUMP)


def startSweep():
    turnOn([PUMP_GPIO, SWEEP_GPIO])
    _setState(STATE_SWEEP)


def stopAll(manual=False):
    global STOP_TIME
    turnOff([PUMP_GPIO, SWEEP_GPIO])
    if manual:
        STOP_TIME = time.time()
    _setState(STATE_OFF)

def Stopped():
    global RUN_TIME, STOP_TIME
    if state() == STATE_OFF and time.time() - STOP_TIME < RUN_TIME:
        return True
    return False

def _getsched(hour, minute, push=False):
    l = time.localtime()
    if push and l.tm_hour > hour: # only true tomorrow
        l = time.localtime(time.time() + 86400)
    s = "%d %d %d %d" % (l.tm_year, l.tm_yday, hour, minute)
    return time.strptime(s, "%Y %j %H %M")
    
#converts "HH:MM" to epoch time float
def _getEpoch(time_str, push=False):
    (hour, minute) = time_str.split(':')
    local = _getsched(int(hour), int(minute), push)
    return time.mktime(local)

def _inZone(start, stop):
    if start == None or stop == None:
        return False

    t = time.time()    
    start_time = _getEpoch(start)
    stop_time = _getEpoch(stop)
    if stop_time < start_time:
        stop_time = _getEpoch(stop, True)

    log.debug("inZone(%d, %d)" % (start_time, stop_time))
    
    if t < stop_time and t > start_time and start_time > STOP_TIME:
        return True
    return False

#TODO: change this to run at times for durations, only if they haven't run that long already that day.
def runOnSchedule():
    global sched_pump_start
    global sched_pump_stop
    global sched_sweep_start
    global sched_sweep_stop

    relay.logStatus()

    log.debug("pool(%s, %s) sweep(%s, %s)" % (
        sched_pump_start, sched_pump_stop,
        sched_sweep_start, sched_sweep_stop))
    
    if _inZone(sched_sweep_start, sched_sweep_stop):
        if state() != STATE_SCHEDULED_SWEEP:
            startSweep()
            _setState(STATE_SCHEDULED_SWEEP)
        return True

    if _inZone(sched_pump_start, sched_pump_stop):
        if state() != STATE_SCHEDULED_PUMP:
            startPump()
            _setState(STATE_SCHEDULED_PUMP)
            return True

    if solar.runPumpsIfNeeded():
        return False
    
    if state() in [STATE_SCHEDULED_PUMP, STATE_SCHEDULED_SWEEP]:
        log.info("Stopping scheduled run")
        stopAll()
        return False

    if state() in [STATE_SOLAR, STATE_SOLAR_MIXING]:
        log.info("Stopping pumps for solar heating")
        stopAll()
        return False
    
    if state() != STATE_OFF and getStartTime() < time.time() - RUN_TIME:
        log.info("Stopping manual run")
        stopAll()

    return False


def setup(conf):
    global sched_pump_start
    global sched_pump_stop
    global sched_sweep_start
    global sched_sweep_stop

    # Initialize relays
    relay.setup()
    sched_pump_start = conf.get("timer.pump.start")
    sched_pump_stop = conf.get("timer.pump.stop")
    sched_sweep_start = conf.get("timer.sweep.start")
    sched_sweep_stop = conf.get("timer.sweep.stop")
