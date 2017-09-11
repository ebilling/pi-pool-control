#!/usr/bin/python
import RPi.GPIO as GPIO
import relay
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

sched_pump_start = "00:00"
sched_pump_stop = "02:00"
sched_sweep_start = "00:00"
sched_sweep_stop = "02:00"

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


def stopAll():
    global STOP_TIME
    turnOff([PUMP_GPIO, SWEEP_GPIO])
    STOP_TIME = time.time()
    _setState(STATE_OFF)

def Stopped():
    if state() == STATE_OFF and time.time() - getStopTime() < RUN_TIME:
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
    t = time.time()
    start_time = _getEpoch(start)
    stop_time = _getEpoch(stop)
    log.debug("Schedule: now(%d) start(%d) stop(%d)" % (t, start_time, stop_time))
    if stop_time < start_time:
        stop_time = _getEpoch(stop, True)
    if t < stop_time and t > start_time and start_time > STOP_TIME:
        return True
    return False

def runOnSchedule():
    global sched_pump_start
    global sched_pump_stop
    global sched_sweep_start
    global sched_sweep_stop

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

    if state() in [STATE_SCHEDULED_PUMP, STATE_SCHEDULED_SWEEP]:
        log.info("Stopping scheduled run")
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
    s = conf.get("timer.pump.start")
    if s:
        sched_pump_start = s
    s = conf.get("timer.pump.stop")
    if s:
        sched_pump_stop = s
    s = conf.get("timer.sweep.start")
    if s:
        sched_sweep_start = s
    s = conf.get("timer.sweep.stop")
    if s:
        sched_sweep_stop = s
