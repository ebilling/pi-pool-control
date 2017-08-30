#!/usr/bin/python
import RPi.GPIO as GPIO
import relay
import time
import log

PUMP_GPIO = relay.RELAY1
SWEEP_GPIO = relay.RELAY2

START_TIME = 0.0
STOP_TIME = 0.0

STATE_OFF = 0
STATE_PUMP = 1
STATE_SWEEP = 2
STATE_SCHEDULED_PUMP = 3
STATE_SCHEDULED_SWEEP = 4
STATE_SOLAR = 5
STATE_SOLAR_MIXING = 6
STATE_DISABLED = 7

RUN_TIME = 7200

_state_ = STATE_OFF

sched_pump_start = "00:00"
sched_pump_stop = "02:00"
sched_sweep_start = "00:00"
sched_sweep_stop = "02:00"

def state():
    global _state_
    return _state_


def turnOn(gpios):
    global START_TIME, _state_
    relay.turnOn(gpios)
    if _state_ == STATE_OFF:
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
    global _state_
    startPump()
    _state_ = STATE_SOLAR


def startSolarMixing():
    global _state_
    startSweep()
    _state_ = STATE_SOLAR_MIXING


def startPump():
    global _state_
    turnOff([SWEEP_GPIO])
    turnOn([PUMP_GPIO])
    _state_ = STATE_PUMP


def startSweep():
    global _state_
    turnOn([PUMP_GPIO, SWEEP_GPIO])
    _state_ = STATE_SWEEP


def stopAll():
    global _state_
    global STOP_TIME
    turnOff([PUMP_GPIO, SWEEP_GPIO])
    STOP_TIME = time.time()
    _state_ = STATE_OFF


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


def startOnSchedule(gpio, start, stop):
    global _state_

    t = time.time()
    start_time = _getEpoch(start)
    stop_time = _getEpoch(stop)
    if stop_time < start_time:
        stop_time = _getEpoch(stop, True)
    if t > start_time and start_time > STOP_TIME and t < stop_time:
        if gpio == SWEEP_GPIO:
            if state() != STATE_SCHEDULED_SWEEP:
                startSweep()
                _state_ = STATE_SCHEDULED_SWEEP
        else:
            if state() != STATE_SCHEDULED_PUMP:
                startPump()
                _state_ = STATE_SCHEDULED_PUMP
        return True

    if t > stop_time and (state() == STATE_SCHEDULED_PUMP or state() == STATE_SCHEDULED_SWEEP):
        log.info("Stopping scheduled run")
        pump.stopAll()
        return False

    if state() != STATE_OFF and getStartTime() < time.time() - RUN_TIME:
        log.info("Time's Up: %f - %f" % (pump.getStartTime(), time.time()))
        pump.stopAll()

    return False


def runOnSchedule():
    if not startOnSchedule(SWEEP_GPIO, sched_sweep_start, sched_sweep_stop):
        startOnSchedule(PUMP_GPIO, sched_pump_start, sched_pump_stop)
    

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
