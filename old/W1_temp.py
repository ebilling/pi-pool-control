#!/usr/bin/python
import os
import re
import sys

DIRECTORY = "/sys/bus/w1/devices"
FILE = "w1_slave"
reg = "[0-9a-g]{2}-[0-9a-g]{12}"

# For a given W1 device, returns the temperature
# throws a ValueError if the device doesn't contain a temperature
def getTempC(device):
    f = open(DIRECTORY + "/" + device + "/" + FILE, "r")
    f.readline()
    # open each one and look for second line containing t=xxxxxx
    temp = f.readline().rstrip().split('t=')
    f.close()
    if len(temp) != 2:
        raise ValueError("Could not find a temperature in " + temp)
    return float(temp[1])/1000.0


# Converts a temperature in Celsius to Farenheit
def toFarenheit(celsius):
    return  (celsius * 9 / 5) + 32


# Converts a temperature in Farenheit to Celsius
def toCelsius(farenheit):
    return (farenheit - 32) * 5 / 9


# Returns a list of all W1 devices on the system
def getW1Devices():
    w1dirs = list()

    # look through /sys/bus/w1/device for devices that look like XX-XXXXXXXXXXXX
    # and contain a file called w1_slave
    dirs = os.listdir(DIRECTORY)
    for x in dirs:
        if re.match(reg, x) and os.path.isfile(DIRECTORY + "/" + x + "/" + FILE):
            w1dirs.append(x)
    return w1dirs


# Detects temperature probes, and returns a list of device ids
def getTempSensors():
    sensors = list()
    for device in getW1Devices():
        try:
            if -50.0 < getTempC(device):
                sensors.append(device)
        except ValueError as e:
	    continue	
    return sensors


def main():
    for x in getTempSensors():
        celsius=getTempC(x)
        print "%s: %0.2fC, %0.2fF" % (x, celsius, toFarenheit(celsius))
    quit()


if __name__ == "__main__":
    main()


