#!/usr/bin/python

import json
import httplib
import time
import requests
import zipcodes

# Current Weather API
# API discussion: http://stackoverflow.com/questions/2502340/noaa-web-service-for-current-weather
# API: http://forecast.weather.gov/MapClick.php?lat=38.4247341&lon=-86.9624086&FcstType=json
# Zipcode LAT/LNG: https://gist.github.com/erichurst/7882666


MAX_AGE = 1800
cache = {}
zips = zipcodes.latlngByZip()

def getLatLngByZip(zipcode):
    global zips
    return zips[zipcode]


def getWeatherByZip(zipcode):
    global cache
    global zips
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


def getCurrentObservation(zipcode):
    data = getWeatherByZip(zipcode)
    return data['currentobservation']


def getForecastByZip(zipcode):
    data = getWeatherByZip(zipcode)['data']
    print "temperatureLen: ", len(data['temperature'])
    print "weatherLen: ", len(data['weather'])
    return data


def printDict(d):
    for key in sorted(d.keys()):
        print "\t", key, ": ", d[key]


def main():
    print "Weather:"
    printDict(getForecastByZip(95032))
    print
    print "FullReport:"
    printDict(getCurrentObservation(95032))


if __name__ == "__main__":
    main()


