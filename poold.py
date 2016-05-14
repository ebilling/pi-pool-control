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

RUN_TIME = 1800
SENSORS = temp.getTempSensors()
DATADIR = '/var/cache/pooldata'
PUMP_RRD = 'pumpstatus'
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


def setupRRD(filename, data_sources, step=60,
             consolidation="AVERAGE"):
    try:
        RRD.info(filename)
    except RRD.error:
        RRD.create( filename,
                    '--start', str(long(time.time())),
                    '--step', str(step),
                    data_sources,
                    'RRA:%s:0.5:1:10080' % (consolidation),
                    'RRA:%s:0.5:60:43830' % (consolidation))


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

    data_sources = [ 'DS:pump:GAUGE:300:-1:2',
                     'DS:sweep:GAUGE:300:-1:2' ]
    setupRRD(RrdFilename(PUMP_RRD), data_sources, consolidation="MAX")


def recordTemp(filename, t):
    log.debug("%s: N:%f:%f" % (filename, t, temp.toFarenheit(t)))
    RRD.update(filename, "N:%f:%f" % (t, temp.toFarenheit(t)))


def recordPumpActivity(filename):
    p = 0
    s = 0
    if pump.state() == pump.STATE_SWEEP:
        p = 1
        s = 1
    elif pump.state() == pump.STATE_PUMP:
        p = 1
    log.debug("%s: N:%d:%d" % (filename, p, s))
    RRD.update(filename, "N:%d:%d" % (p, s))


def produceGraph(outfile, title, width, height, args):
    week = 7*24*3600
    log.debug(str(args))
    try:
        RRD.graph(outfile,
                  "--end", "now",
                  "--start", "end-16h",
                  "--imgformat", "PNG",
                  "--title", title,
                  "--width", str(width),
                  "--height", str(height),
                  *args)
    except RRD.error as e:
        log.error("RRDTool Failed with: %s" % (e))


def produceTempGraph(filenames, outfile="temperature.png", title='Temperatures',
                 unit=FARENHEIT, width=700, height=300):
    args = list()
    count = 0
    gdef_fmt = 'DEF:t%d=%s:%s:AVERAGE'
    gline_fmt = 'LINE%d:t%d%s:%s'
    for filename in filenames:
        filename = RrdFilename(filename)
        if unit == FARENHEIT:
            args.append(gdef_fmt % (count, filename, "farenheit"))
            args.append(gline_fmt % (count+1, count, color.colorStr(count),
                                     filename + " F"))
        elif unit == CELSIUS:
            args.append(gdef_fmt % (count, filename, "celsius"))
            args.append(gline_fmt % (count+1, count, color.colorStr(count),
                                     filename + " C"))
        else:
            raise ValueError("Must be either FARENHEIT or CELSIUS")
        count+=1

    if title == None:
        title = filename 

    produceGraph(outfile, title, width, height, args)


def producePumpGraph(outfile='pumps.png', title='Pump Activity', width=700, height=300):
    args = list()
    gdef_fmt = 'DEF:t%d=%s:%s:MAX'
    gline_fmt = 'LINE%d:t%d%s:%s'

    args.append(gdef_fmt % (1, RrdFilename(PUMP_RRD), 'pump'))
    args.append(gline_fmt % (1, 1, color.colorStr(0), "Main Pump"))
    args.append(gdef_fmt % (2, RrdFilename(PUMP_RRD), 'sweep'))
    args.append(gline_fmt % (2, 2, color.colorStr(1), "Sweep Pump"))

    produceGraph(outfile, title, width, height, args)


def FifoThread():
    setupFifo()
    count = 0;
    while True:
        file = open(CMDFIFO, "r")
        for x in range(0, 10):
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
                log.error("Don't know what to do with %s" % (line))
        file.close()


def main():
    pid = os.fork()
    if pid:
        pidfile = open(PIDFILE, "w+")
        pidfile.write(str(pid))
        pidfile.close()
        os._exit(0)

    outdir = '/var/www/html/'
    tempGraph = outdir + 'temps.png'
    pumpGraph = outdir + 'pumps.png'

    setup()
    files = list()
    files.append(WEATHER)
    for x in SENSORS:
        files.append(x)
    thread.start_new_thread(FifoThread, ())

    while True:
        recordTemp(RrdFilename(WEATHER),
                   temp.toCelsius(int(weather.getCurrentObservation(95032)['Temp'])))
        for x in SENSORS:
            recordTemp(RrdFilename(x), temp.getTempC(x))

        recordPumpActivity(RrdFilename(PUMP_RRD))

        #### should I move this to the pump control file?
        if pump.getStartTime() and pump.getStartTime() < time.time() - RUN_TIME:
            log.info("Time's Up: %f - %f" % (pump.getStartTime(), time.time()))
            pump.stopAll()

        produceTempGraph(files, outfile=tempGraph)
        producePumpGraph(outfile=pumpGraph)
        time.sleep(10)

    GPIO.cleanup()
    quit()


if __name__ == "__main__":
    main()
