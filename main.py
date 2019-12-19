#!/usr/bin/python3

import requests
import sqlite3
from pathlib import Path
import time
import json
from datetime import datetime
import pytz


class TempDevice:
    dbpath = ""
    deviceid = ""
    apikey = ""
    dashurl = ""
    dashurl_template = "https://mdash.net/api/v2/devices/{}?access_token={}"

    def __init__(self, deviceid, apikey):
        self.deviceid = deviceid
        self.apikey = apikey
        self.dashurl = self.dashurl_template.format(self.deviceid, self.apikey)

    def getTemp(self):
        resp = requests.get(self.dashurl)
        data = json.loads(resp.text)
        newAvgTemp = data['shadow']['state']['reported']['avgTemp']
        timestamp = data['shadow']['timestamp']
        return newAvgTemp, timestamp


class Database:
    def writeTemp(self, deviceid, temp):
        pass


def getDevices(credspath):
    credspath = Path(credspath)
    devices = []
    with open(credspath) as creds:
        data = json.loads(creds.read())
        for deviceid, apikey in data.items():
            devices.append(TempDevice(deviceid, apikey))
    return devices


if __name__ == "__main__":
    # List of all temperature monitoring devices
    devices = getDevices("./creds.json")
    while True:
        for device in devices:
            try:
                newAvgTemp, timestamp = device.getTemp()
                timeformat = datetime.fromtimestamp(timestamp).astimezone(
                    pytz.timezone('America/Edmonton')).strftime('%e %b %Y %I:%M:%S%p')
                print("Device: {} Avg Temp: {} Time: {} ({})".format(device.deviceid, newAvgTemp,
                                                                     timestamp, timeformat))
            except Exception as e:
                print(e)
        time.sleep(5)
