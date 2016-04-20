#!/usr/bin/python
import RPi.GPIO as GPIO
import temperature as temp
import rrdtool as RRD
import pump
import time

SENSORS = temp.getTempSensors()
DATADIR = "/var/cache/pooldata"
FARENHEIT = 0
CELSIUS = 1
GPIODIR = "/sys/class/gpio"

BUTTON_GPIO = 18

def RrdFilename(x):
    return "%s/%s.rrd" % (DATADIR, x)


counter = 0
def pushButtonCallback(channel):
    global counter
    # Need to create callbacks for button push counts
    print "Button Pushed!!!!"
    counter+=1
    print "Status: " + str(pump.getStatus())
    if counter%3 == 1:
        pump.startPump()
    elif counter%3 == 2:
        pump.startSweep()
    else:
        pump.stopAll()
    print "Status: " + str(pump.getStatus())


def setup():
    # Initialize GPIO
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    # Initialize Button
    GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(BUTTON_GPIO, GPIO.FALLING, callback=pushButtonCallback, bouncetime=200)

    data_sources = [ 'DS:celsius:GAUGE:300:-273:5000',
                     'DS:farenheit:GAUGE:300:-500:10000' ]

    for x in SENSORS:
        try:
            RRD.info(RrdFilename(x))
        except RRD.error:
            RRD.create( RrdFilename(x),
                        '--start', str(long(time.time())),
                        '--step', '300',
                        data_sources,
                        'RRA:AVERAGE:0.5:1:1200',
                        'RRA:AVERAGE:0.5:6:2400')

def recordTemp(filename, t):
    RRD.update(filename, "N:%f:%f" % (t, temp.toFarenheit(t)))


def produceGraph(filename, outfile="temperature.png", title=None, unit=FARENHEIT, width=500, height=300):
    gdef = 'DEF:temp=%s:%s:AVERAGE'
    gline = 'LINE1:temp#ff0000:"%s"'
    if unit == FARENHEIT:
        gdef = gdef % (filename, "farenheit")
        gline = gline % ("deg_F")
    elif unit == CELSIUS:
        gdef = gdef % (filename, "celsius")
        gline = gline % ("deg_C")
    else:
        raise ValueError("Unit must be either FARENHEIT(%d) or CELSIUS(%d)" % (FARENHEIT, CELSIUS))

    if title == None:
        title = filename 

    try:
        week = 7*24*3600
        RRD.graph(outfile,
                  "--end", "now",
                  "--start", "end-1w",
                  "--imgformat", "PNG",
                  "--title", title,
                  "--width", str(width),
                  "--height", str(height),
                  gdef,
                  gline)
    except RRD.error as e:
        print "RRDTool Failed with: %s" % (e)


def main():
    global counter
    setup()
    while True:
        for x in SENSORS:
            recordTemp(RrdFilename(x), temp.getTempC(x))
            out = "/var/www/html/%s.png" % (x)
            produceGraph(RrdFilename(x), outfile=out, title="Temperature")
        if pump.getStartTime() and pump.getStartTime() < time.time() - RUN_TIME:
            print "Time's Up: %f - %f" % (pump.getStartTime(), time.time())
            pump.stopAll()
            counter=0 
        time.sleep(60)
    GPIO.cleanup()
    quit()


if __name__ == "__main__":
    main()
