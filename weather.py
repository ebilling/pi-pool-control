#!/usr/bin/python

import json
import httplib
import time
import requests

# Current Weather API
# API discussion: http://stackoverflow.com/questions/2502340/noaa-web-service-for-current-weather
# API: http://forecast.weather.gov/MapClick.php?lat=38.4247341&lon=-86.9624086&FcstType=json
# Zipcode LAT/LNG: https://gist.github.com/erichurst/7882666

zips = None

MAX_AGE = 1800
cache = {}

def getZipData():
    global zips
    zips={}
    f = open('zip2latlng.csv', 'r')
    f.readline() # Header
    line = f.readline() # first line
    while line:
        line = line.strip().split(',')
        zips[int(line[0])] = (float(line[1]), float(line[2]))
        line = f.readline() # next line
    f.close()


def getLatLngByZip(zipcode):
    global zips
    return zips[zipcode]


def getWeatherByZip(zipcode):
    global cache
    global zips
    if not zips:
        getZipData()
    if zipcode in cache and cache[zipcode][0] < time.time() - MAX_AGE:
        return cache[zipcode][1]
    (lat, lng) = zips[zipcode]
    typeQuery = "http://forecast.weather.gov/MapClick.php?lat=%f&lon=%f&FcstType=json" % (lat, lng)
    r = requests.get(typeQuery)
    if r.status_code >= 200 and r.status_code < 300:
        data = json.loads(r.text)
        cache[zipcode] = (time.time(), data)
        return data
    return None


def getConditionsByZip(zipcode):
    data = getWeatherByZip(zipcode)
    weather = data['data']['weather'][0]
    temperature = int(data['data']['temperature'][0])
    return (int(temperature), weather)


def main():
    print "Weather(%d: %s)" % getConditionsByZip(95032)


if __name__ == "__main__":
    main()


