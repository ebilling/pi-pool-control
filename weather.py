#!/usr/bin/python

import json
import httplib

# API Documentation: http://www.ncdc.noaa.gov/cdo-web/webservices/v2

NCDC_TOKEN = "MwtRFtJDlxGLsnBtnNcTbiuoabkNVHhT"

header = {"token": NCDC_TOKEN}
conn = httplib.HTTPConnection("www.ncdc.noaa.gov")


def get(request):
    conn.request("GET", request, None, header)
    response = conn.getresponse()
    data = response.read()
    return data


def getAll(request):
    print "test"


def getResults(data):
    jsonData = json.loads(data)
    keys = list()
    out = {}
    keys = jsonData["results"][0].keys()
    appendResults(keys, out, jsonData)
    return (keys, out)


def appendResults(keys, results, jsonData):
    for x in jsonData["results"]:
        row = list()
        for key in keys:
            row.append(x[key])
        results[x["id"]] = row    


def getTypes():
    typeQuery = "/cdo-web/api/v2/datatypes?locationid=ZIP:95032&limit=1000"
    data = get(typeQuery)
    return getResults(data)

def getLocationsByZip():
    limit = 1000
    offset=0
    locationQuery = "/cdo-web/api/v2/locations?locationcategoryid=ZIP&" +\
                    "limit=%d&sortfield=id&sortorder=asc&offset=%d"
    data = get(locationQuery % (limit, offset))
    (keys, results) = getResults(data)
    while True:
        offset += limit
        data = get(locationQuery % (limit, offset))
        appendResults(keys, results, data)
        if len(data["results"]) < 1000:
            break
    return (keys, results)


def getDataCategories():
    dataCategoriesQuery = "/cdo-web/api/v2/datacategories?limit=1000" 
    data = get(dataCategoriesQuery)
    return getResults(data)


def getDataSets():
    dataSetsQuery = "/cdo-web/api/v2/datasets?limit=1000" 
    print "URL: ", dataSetsQuery
    data = get(dataSetsQuery)
    return getResults(data)


def getData(datasetid, zip):
    dataQuery = "/cdo-web/api/v2/data?datasetid=%s&locationid=ZIP:%s&units=metric&limit=1000"
    data = get(dataQuery)
    return data


print "DataTypes:"
(keys, data) = getTypes()
print keys
for x, y in data.items():
    print x, ": ", y




conn.close()
