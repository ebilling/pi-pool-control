#!/usr/bin/python

import cgi
import cgitb
import rrdtool as RRD
import time

cgitb.enable()

STATUS_FILE = "/var/cache/pooldata/pumpstatus.rrd"
CMDFIFO = "/tmp/poold.fifo"

P_STAT = False
S_STAT = False

form = cgi.FieldStorage()

def sendSignal(value):
    with open(CMDFIFO, "a") as f:
        f.write(value + '\n')
        f.close()

result = RRD.fetch(STATUS_FILE, 'MAX',
                   '-r', '60',
                   '-s', str(long(time.time())-300),
                   '-e', str(long(time.time())))
# TODO: Read the rrd file and use it to set the status

datalen = len(result[2]) - 1
while datalen > 0:
    value = result[2][datalen]
    if value[0] == None:
        datalen-=1
        continue
    if value[1] > 0:
        S_STAT = True
    elif value[0] > 0:
        P_STAT = True
    break

if 'PumpOn' in form:
    sendSignal('PUMP_ON')
    P_STAT = True
    

if 'SweepOn' in form:
    sendSignal('SWEEP_ON')
    S_STAT = True

if 'AllPumpsOff' in form:
    sendSignal('OFF')
    P_STAT = S_STAT = False


print "Content-Type: text/html"     # HTML is following
print "Refresh: 10; url=/?"
print                               # blank line, end of headers

print '<html><body>'
print '<FORM ACTION=/>'

if not P_STAT:
    print '<INPUT type=submit name=PumpOn value=PumpOn> '

if not S_STAT:
    print '<INPUT type=submit name=SweepOn value=SweepOn> '

if P_STAT or S_STAT:
    print '<INPUT type=submit name=AllPumpsOff value=AllPumpsOff>'

print '</FORM>'
print '<IMG src=pumps.png><br><IMG SRC=temps.png>'
print '</body></html>'
