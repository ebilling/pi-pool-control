#!/usr/bin/env python

import RPi.GPIO as GPIO
from collections import deque
import math
import time
import log
import config
import thread
import threading

TIMEOUT = 1.0   # 1s
DRAINTIME = 0.2 # 200ms
ATTEMPTS = 5

TTL = 60.0 # 1 minutes

locks = {}
cap = {}
past = {}
_test = {} # testing values

def setup(conf):
   global cap
   global _test
   cap = conf.get("capacitance.gpio")
   testvalues = conf.get("temp.testvalue")
   if testvalues != None:
      _test = {}
      for key in testvalues.keys():
         _test[int(key)] = float(testvalues[key])

def average(x):
   if x == 0 or len(x) == 0:
      return 0
   return float(sum(x))/float(len(x))

def variance(x):
   avg = average(x)
   var = 0.0
   for n in x:
      var = var + (avg - n) ** 2
   if len(x) > 0:
      return var/len(x)
   return 0.0

def stddev(x):
   return variance(x) ** 0.5

def median(x):
   if len(x) > 2:
      return sorted(x)[len(x)/2]
   return average(x)

def cleanData(gpio, x):
   global past
   old = None

   if gpio in past:
      old = past[gpio][0]
      old.extendleft(x)
   else:
      old = deque(x, 100)

   stdd = stddev(list(old))
   med = median(x)
   n = list()

   for i in x:
      if abs(i - med) < stdd:
         n.append(i)

   if len(n) > 0:
      val = average(n)
      past[gpio] = (old, val, time.time())
   else:
      log.error("No valid temp data for gpio(%d) orig(%s) cleaned(%s)" % (gpio, str(x), str(n)))

   return past[gpio][1]

def _getDischargeTime(gpio):
   global locks
   _sleepTime = 0.0002
   _minTime = 3000.0
   _maxTime = 500000.0
   values = list()

   if gpio not in locks:
      locks[gpio] = threading.Lock()

   lock = locks[gpio]

   for i in range(0, ATTEMPTS):
      lock.acquire()
      #drain the capacitor
      GPIO.setmode(GPIO.BCM)
      GPIO.setup(gpio, GPIO.OUT)
      GPIO.output(gpio, GPIO.LOW)
      time.sleep(DRAINTIME)

      # Go into input mode
      GPIO.setup(gpio, GPIO.IN)

      # Count loops until voltage across capacitor reads high on GPIO
      start = time.time()
      timeout = start + TIMEOUT
      while True:
         time.sleep(_sleepTime)
         end = time.time()
         if (GPIO.input(gpio) != GPIO.LOW) or (end > timeout) or end > timeout:
            break

      tm = (end - start) * 1000000.0
      if end < timeout:
         if tm > _minTime and tm < _maxTime:
            values.append(tm)
         else:
            log.info("Temperature fetch was outside acceptable range for gpio(%d) time(%0.2f ms) temp(%0.1f C)" % (
               gpio, tm/1000.0, _getTemp(_getOhms(tm,gpio))))
      else:
         log.info("Temperature fetch timed out for gpio(%d)" % (gpio))
      lock.release()

   return cleanData(gpio, values)


def _getOhms(usec, gpio=0):
   c_uF = 10.0
   if gpio !=0 and str(gpio) in cap:
      c_uF = float(cap[str(gpio)])
   # total discharge not required to count as input, takes half as long as expected
   return 2*usec/c_uF

def _getTemp(r):
   a = 79463.85
   b = 0.1453676
   c = 2.517178E-15
   d = -132.2399
   if r <= 0:
      return 0
   return d + (a - d)/(1 + (r/c) ** b)

# Reads the value of the resistive temperature probe on the given GPIO
def getTempC(gpio):
   global past
   global _test

   #DEBUGGING CODE
   if gpio in _test:
      log.debug("Using Test value for temperature on GPIO %d" % (gpio))
      return _test[gpio]

   try:
      if gpio in past:
         if past[gpio][2] + TTL > time.time():
            return _getTemp(_getOhms(past[gpio][1],gpio))  # Cached value
      t = _getDischargeTime(gpio)
      return _getTemp(_getOhms(t, gpio))
   except Exception as e:
      log.trace("Could not read temperature: gpio(%d) exception(%s)" % (gpio, str(e)))

   return 0.0


# Converts a temperature in Celsius to Farenheit
def toFarenheit(celsius):
    return  (float(celsius) * 9.0 / 5.0) + 32.0


# Converts a temperature in Farenheit to Celsius
def toCelsius(farenheit):
    return (float(farenheit) - 32.0) * 5.0 / 9.0

# ./temp.py [gpio]
if __name__ == "__main__":

   import sys
   import time
   import temp
   import math

   RUN_TIME = 20
   CAP_GPIO = 25 # 24,25

   setup(config.config("config.json"))
   
   if len(sys.argv) > 1:
      cap_gpio = int(sys.argv[1])
   else:
      cap_gpio = CAP_GPIO


   print "10kOhm: %0.2f" % (toFarenheit(_getTemp(10000)))
   for i in range(0,100):
      t = getTempC(cap_gpio)
      print("%0.1fC, %0.1fF" % (t, toFarenheit(t)))
   
   
