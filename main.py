#!/usr/bin/python3

import requests
import sqlite3
from pathlib import Path
import time
import json
from datetime import datetime
import pytz
import smtplib
import gmailoauth


# Represents a single ESP32/8266, each with unique deviceid and apikey
class TempDevice:
    deviceid = ""
    apikey = ""
    dashurl = ""
    dashurl_template = "https://mdash.net/api/v2/devices/{}?access_token={}"
    lasttemp = 0.00
    lasttime = 0

    def __init__(self, deviceid, apikey):
        self.deviceid = deviceid
        self.apikey = apikey
        self.dashurl = self.dashurl_template.format(self.deviceid, self.apikey)

    def getTemp(self):
        resp = requests.get(self.dashurl)
        data = json.loads(resp.text)
        newAvgTemp = data['shadow']['state']['reported']['avgTemp']
        timestamp = data['shadow']['timestamp']
        self.lasttemp = newAvgTemp
        self.lasttime = timestamp
        return newAvgTemp, timestamp


# Used for logging temperature data
# TODO: Implement database
class Database:
    def __init__(self):
        pass

    def writeTemp(self, deviceid, temp):
        pass


# Sends a text via email to emails
class Notifier:
    emails = []
    server = ""

    def __init__(self, emails):
        self.emails = emails

    def warning(self, device):
        timef = datetime.fromtimestamp(device.lasttime).astimezone(
            pytz.timezone('America/Edmonton')).strftime('%e %b %Y %I:%M:%S%p')
        for email in self.emails:
            sender = ""
            subject = "Temperature warning"
            msgHtml = "WARNING: Low temperature ({}) detected from {} at {}\n" \
                      "Another warning will be sent periodically".format(device.lasttemp,
                                                                         device.deviceid,
                                                                         timef)
            msgPlain = msgHtml
            print(msgHtml)
            gmailoauth.SendMessage(sender, email, subject, msgHtml, msgPlain)

    def notify(self):
        for email in self.emails:
            sender = ""
            subject = "Temperature normal"
            msgHtml = "Temperature levels have returned to normal."
            msgPlain = msgHtml
            print(msgHtml)
            gmailoauth.SendMessage(sender, email, subject, msgHtml, msgPlain)


# Gets devices from a json dictionary formatted as deviceid: apikey
def getDevices(credspath):
    credspath = Path(credspath)
    devices = []
    with open(credspath) as creds:
        data = json.loads(creds.read())
        for deviceid, apikey in data.items():
            devices.append(TempDevice(deviceid, apikey))
    return devices


# Gets email addresses to send notifications to
def getEmails(emailspath):
    emailspath = Path(emailspath)
    emails = []
    with open(emailspath) as emails:
        return json.loads(emails.read())


if __name__ == "__main__":
    # List of all temperature monitoring devices
    devices = getDevices("./tempcreds.json")
    # Email notifier
    n = Notifier(getEmails("./emails.json"))
    timezone = 'America/Edmonton'
    # Temperature to trigger a warning in degrees celsius
    tempthreshold = 30.0
    # Polling delay in seconds
    sleeptime = 5
    # Time to wait before sending another warning in seconds
    warning_timeout = 300
    # Is there currently a temperature warning
    warning = False
    # Time when warning ends
    warning_timestamp = 0
    while True:

        # Iterate through each device and poll for new temperatures
        # TODO: Make warning system work with multiple devices
        for device in devices:
            try:
                newAvgTemp, timestamp = device.getTemp()
                timeformat = datetime.fromtimestamp(timestamp).astimezone(
                    pytz.timezone(timezone)).strftime('%e %b %Y %I:%M:%S%p')
                print("{}:\t\tAvg Temp: {}\t\tTime: {} ({})".format(device.deviceid, newAvgTemp,
                                                                    timestamp, timeformat))
                # If the new temp is lower than the threshold
                if not warning and newAvgTemp <= tempthreshold:
                    # Email user and set up warning state
                    n.warning(device)
                    warning_timestamp = timestamp + warning_timeout
                    warning = True
                # Periodically check to warn again if temp is low
                elif warning and datetime.now().timestamp() > warning_timestamp and newAvgTemp <= tempthreshold:
                    n.warning(device)
                    # Wait another x seconds before warning again
                    warning_timestamp = timestamp + warning_timeout
                # If there is a temperature warning issued, wait until after warning time is up to check if it's warm
                elif warning and datetime.now().timestamp() > warning_timestamp and newAvgTemp > tempthreshold:
                    # Dismiss warning and notify things are normal
                    warning = False
                    n.notify()
            except Exception as e:
                print(e)
        time.sleep(sleeptime)
