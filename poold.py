#!/usr/bin/python

import RPi.GPIO as GPIO
import rrdtool as RRD
import temp
import pump
import time
import color
import weather
import sys
import thread
import os
import log
import config
import solar

CONFIG_FILE = '/home/pi/Workspace/pi-pool-control/poold.conf'
conf = config.config(CONFIG_FILE)
_scale = "24h"

FARENHEIT = 0
CELSIUS = 1

GPIODIR = '/sys/class/gpio'
CMDFIFO = '/tmp/poold.fifo'
PIDFILE = '/tmp/poold.pid'
RRD_DIR = '/var/cache/pooldata'
IMAGEDIR = '/tmp/'
POOL_TEMP = '/tmp/pool_temp'

PUMP_RRD = 'pumpstatus'
TEMP_RRD = 'temperature'

ZIP = 0

BUTTON_GPIO = 18
GREEN_LED = 5

def RrdFilename(x):
    return "%s/%s.rrd" % (RRD_DIR, x)


def pushButtonCallback(channel):
    state = pump.state()
    if state == pump.STATE_OFF:
        log.info("ButtonAction: Starting Pump")
        pump.startPump()
    elif state == pump.STATE_PUMP:
        log.info("ButtonAction: Starting Sweep")
        pump.startSweep()
    else:
        log.info("ButtonAction: Stopping all pumps")
        pump.stopAll()


def setupRRD(filename, data_sources, consolidation="AVERAGE"):
    step = 20
    try:
        RRD.info(filename)
    except RRD.error:
        RRD.create( filename,
                    '--start', str(long(time.time())),
                    '--step', str(step),
                    data_sources,
                    'RRA:%s:0.5:1:8640' % (consolidation),
                    'RRA:%s:0.5:3:10080' % (consolidation),
                    'RRA:%s:0.5:180:43830' % (consolidation))


def setupFifo():
    if not os.path.exists(CMDFIFO):
        oldmask = os.umask(0)
        os.mkfifo(CMDFIFO, 0666)
        os.umask(oldmask)

def updateConfig():
    global conf, ZIP, _scale
    conf = config.config(CONFIG_FILE)
    ZIP = int(conf.get('weather.zip'))
    if conf.get('graph.scale') != None:
        _scale = conf.get('graph.scale')
    if conf.get('rrd.directory') != None:
        RRD_DIR = conf.get('rrd.directory')
    if conf.get('pooltemp.location') != None:
        POOL_TEMP = conf.get('pooltemp.location')
    temp.setup(conf)
    pump.setup(conf)
    solar.setup(conf)
    weather.setAppid(conf.get('weather.appid'))

def setup():
    # Initialize GPIO
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GREEN_LED, GPIO.OUT)
    GPIO.output(GREEN_LED, True)

    # Read config
    updateConfig()

    # Initialize Button
    GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(BUTTON_GPIO, GPIO.FALLING,
                          callback=pushButtonCallback,
                          bouncetime=200)

    data_sources = [ 'DS:weather:GAUGE:300:-273:5000',
                     'DS:pool:GAUGE:300:-273:5000',
                     'DS:solar:GAUGE:300:-273:5000',
                     'DS:target:GAUGE:300:-273:5000' ]
    setupRRD(RrdFilename(TEMP_RRD), data_sources)

    data_sources = [ 'DS:pump:GAUGE:300:-1:10',
                     'DS:solar:GAUGE:300:-1:10']
    setupRRD(RrdFilename(PUMP_RRD), data_sources, consolidation="MAX")


def recordTemp(weather, pool, solar, target):
    RRD.update(RrdFilename(TEMP_RRD), "N:%f:%f:%f:%f" % (
        weather, pool, solar, target))
    tempfile = open(POOL_TEMP, 'w+')
    tempfile.write(str(pool))
    tempfile.close()
    

def recordPumpActivity():
    RRD.update(RrdFilename(PUMP_RRD), "N:%d:%d" % (pump.state(), solar.state()))
#    log.debug("Pumps: pump(%d) solar(%d)" % (pump.state(), solar.state()))


def produceGraph(outfile, title, width, height, args):
    global _scale
    week = 7*24*3600
    scale = "end-%s" % (_scale)
    try:
        RRD.graph(outfile,
                  "--end", "now",
                  "--start", scale,
                  "--imgformat", "PNG",
                  "--title", title,
                  "--width", str(width),
                  "--height", str(height),
                  *args)
    except RRD.error as e:
        log.error("RRDTool Failed with: %s" % (e))

def appendTempLine(args, c, var, title, col, unit=FARENHEIT):
    gdef_fmt = 'DEF:t%d=%s:%s:AVERAGE'
    filename = RrdFilename(TEMP_RRD)
    args.append(gdef_fmt % (c, filename, var))
    line = 't'
    if unit == FARENHEIT:
        cdef_fmt = 'CDEF:f%d=9,5,/,t%d,*,32,+'
        args.append(cdef_fmt % (c, c))
        line = 'f'
    gline_fmt = 'LINE%d:' + line + '%d%s:%s'
    args.append(gline_fmt % (2, c, color.colorStr(col), title))
    return args
    
def produceTempGraph(outfile="temperature.png", title='Temperatures',
                     unit=FARENHEIT, width=700, height=300):
    args = list()
    args.append(["--right-axis-label", "Degrees Farenheit",
                 "--right-axis", "1:0"])
    appendTempLine(args, 1, "weather", "Weather F", 0)
    appendTempLine(args, 2, "pool", "Pool F", 1)
    appendTempLine(args, 3, "solar", "Solar F", 2)
    appendTempLine(args, 4, "target", "Target F", 6)

    produceGraph(outfile, title, width, height, args)


def producePumpGraph(outfile='pumps.png', title='Pump Activity', width=700, height=300):
    args = list()
    gdef_fmt = 'DEF:t%d=%s:%s:MAX'
    gline_fmt = 'LINE%d:t%d%s:%s'

    args.append(gdef_fmt % (1, RrdFilename(PUMP_RRD), 'pump'))
    args.append(gline_fmt % (2, 1, color.colorStr(0), "Pump Status"))
    args.append(gdef_fmt % (2, RrdFilename(PUMP_RRD), 'solar'))
    args.append(gline_fmt % (2, 2, color.colorStr(2), "Solar"))

    produceGraph(outfile, title, width, height, args)


def FifoThread():
    setupFifo()
    while True:
        file = open(CMDFIFO, "r")
        line = file.readline()
        if not line or line == None:
            time.sleep(1)
            continue

        line = line.strip()
        if line == 'PUMP_ON':
            pump.startPump()
        elif line == "SWEEP_ON":
            pump.startSweep()
        elif line == "OFF":
            pump.stopAll()
        else:
            log.error("Don't know what to do with %s" % (line))
        file.close()

def SolarThread():
    while True:
        solar.runPumpsIfNeeded()
        time.sleep(5)


def PumpScheduleThread():
    while True:
        pump.runOnSchedule()
        time.sleep(60)

def main():
    pid = os.fork()
    if pid:
        pidfile = open(PIDFILE, "w+")
        pidfile.write(str(pid))
        pidfile.close()
        os._exit(0)

    outdir = IMAGEDIR
    tempGraph = outdir + 'temps.png'
    pumpGraph = outdir + 'pumps.png'
    
    setup()
    thread.start_new_thread(FifoThread, ())
    thread.start_new_thread(SolarThread, ())
    thread.start_new_thread(PumpScheduleThread, ())

    while True:
        time.sleep(30)
        updateConfig()
        recordTemp(weather.getCurrentTempC(ZIP), solar.waterTemp(),
                   solar.roofTemp(), solar.targetTemp)
        recordPumpActivity()
        produceTempGraph(outfile=tempGraph)
        producePumpGraph(outfile=pumpGraph)

    log.debug("exiting")
    GPIO.cleanup()
    quit()


if __name__ == "__main__":
    main()
