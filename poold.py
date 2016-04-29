#!/usr/bin/python
import RPi.GPIO as GPIO
import temperature as temp
import rrdtool as RRD
import pump
import time
import color
import weather
import sys
import thread
import os
import log

RUN_TIME = 60
SENSORS = temp.getTempSensors()
DATADIR = '/var/cache/pooldata'
FARENHEIT = 0
CELSIUS = 1
GPIODIR = '/sys/class/gpio'
CMDFIFO = '/tmp/poold.fifo'
PIDFILE = '/var/run/poold.pid'
WEATHER = 'weather'

BUTTON_GPIO = 18

def RrdFilename(x):
    return "%s/%s.rrd" % (DATADIR, x)


def pushButtonCallback(channel):
    state = pump.state()
    if state == pump.STATE_OFF:
        pump.startPump()
    elif state == pump.STATE_PUMP:
        pump.startSweep()
    else:
        pump.stopAll()

def setupRRD(filename, data_sources):
    try:
        RRD.info(filename)
    except RRD.error:
        RRD.create( filename,
                    '--start', str(long(time.time())),
                    '--step', '300',
                    data_sources,
                    'RRA:AVERAGE:0.5:1:1200',
                    'RRA:AVERAGE:0.5:6:2400')

def setupFifo():
    log.debug("Setting up Fifo")
    if not os.path.exists(CMDFIFO):
        oldmask = os.umask(0)
        os.mkfifo(CMDFIFO, 0666)
        os.umask(oldmask)

def setup():
    # Initialize GPIO
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    # Initialize Button
    GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(BUTTON_GPIO, GPIO.FALLING,
                          callback=pushButtonCallback,
                          bouncetime=200)

    data_sources = [ 'DS:celsius:GAUGE:300:-273:5000',
                     'DS:farenheit:GAUGE:300:-500:10000' ]

    setupRRD(RrdFilename(WEATHER), data_sources)
    for x in SENSORS:
        setupRRD(RrdFilename(x), data_sources)


def recordTemp(filename, t):
    log.debug("%s: N:%f:%f" % (filename, t, temp.toFarenheit(t)))
    RRD.update(filename, "N:%f:%f" % (t, temp.toFarenheit(t)))


def produceGraph(filenames, outfile="temperature.png", title=None,
                 unit=FARENHEIT, width=500, height=300):
    args = list()
    count = 0
    gdef_fmt = 'DEF:t%d=%s:%s:AVERAGE'
    gline_fmt = 'LINE%d:t%d%s:"%s"'
    for filename in filenames:
        if unit == FARENHEIT:
            args.append(gdef_fmt % (count, filename, "farenheit"))
            args.append(gline_fmt % (count+1, count, color.colorStr(count),
                                     "deg_F"))
        elif unit == CELSIUS:
            args.append(gdef_fmt % (count, filename, "celsius"))
            args.append(gline_fmt % (count+1, count, color.colorStr(count),
                                     "deg_C"))
        else:
            raise ValueError("Must be either FARENHEIT or CELSIUS")
        count+=1

    if title == None:
        title = filename 

    try:
        week = 7*24*3600
        log.debug(str(args))
        RRD.graph(outfile,
                  "--end", "now",
                  "--start", "end-1h",
                  "--imgformat", "PNG",
                  "--title", title,
                  "--width", str(width),
                  "--height", str(height),
                  *args)
    except RRD.error as e:
        log.err("RRDTool Failed with: %s" % (e))


def FifoThread():
    setupFifo()
    file = open(CMDFIFO, "r")
    while True:
        line = file.readline().strip()
        if not line:
            time.sleep(1)
        elif line == 'PUMP_ON':
            pump.startPump()
        elif line == "SWEEP_ON":
            pump.startSweep()
        elif line == "OFF":
            pump.stopAll()
        else:
            log.err("Don't know what to do with %s" % (line))
    file.close()


def main():
    pid = os.fork()
    if pid:
        pidfile = open(PIDFILE, "w+")
        pidfile.write(str(pid))
        pidfile.close()
        os._exit(0)

    out = '/var/www/html/temps.png'
    setup()
    files = list()
    files.append(RrdFilename(WEATHER))
    for x in SENSORS:
        files.append(RrdFilename(x))
    thread.start_new_thread(FifoThread, ())

    while True:
        recordTemp(RrdFilename(WEATHER),
                   temp.toCelsius(int(weather.getCurrentObservation(95032)['Temp'])))
        for x in SENSORS:
            recordTemp(RrdFilename(x), temp.getTempC(x))

        #### should I move this to the pump control file?
        if pump.getStartTime() and pump.getStartTime() < time.time() - RUN_TIME:
            log.info("Time's Up: %f - %f" % (pump.getStartTime(), time.time()))
            pump.stopAll()

        produceGraph(files, outfile=out, title="Temperature")
        time.sleep(60)
    GPIO.cleanup()
    quit()


if __name__ == "__main__":
    main()
