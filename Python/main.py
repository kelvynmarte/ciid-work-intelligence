#!/usr/bin/python

import serial
from thermal_printer import ThermalPrinter
from facesApi import calculateFee
from imageParse import imageParse
from sendStatus import sendStatus
from multiprocessing import Process
import os
import sys
import time
from time import sleep
import termios
orig_settings = termios.tcgetattr(sys.stdin)



is_raspberry_pi = os.uname()[1] == "raspberrypi"

if is_raspberry_pi:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    from button_logic import ButtonTracker
    import picamera
    camera = picamera.PiCamera()
    camera.resolution = (864, 648)
    camera.brightness = 60
    camera.contrast = 45
    camera.rotation = 90
    #camera.hflip = True
    #camera.vflip = True

# Parse Arguments
noPrint = False
arduinoSerial = True
noHttp = False

for eachArg in sys.argv:
    if eachArg == "noprint":
        noPrint = True
    if eachArg == "noserial":
        arduinoSerial = None
    if eachArg == "nohttp":
        noHttp = True

if noHttp:
    def sendStatus(status, delay):
        print status
else:
    from sendStatus import sendStatus

if arduinoSerial is not None:
    if is_raspberry_pi:
        arduinoSerial = serial.Serial('/dev/ttyACM0', 9600)
    else:
        arduinoSerial = serial.Serial('/dev/cu.usbmodem146221', 9600)
    command = arduinoSerial.readline() # wait till arduino is ready

def sendSerialMsg(status):
    if arduinoSerial is not None:
        arduinoSerial.write(status + "\n")

def buttonPressed(pins, time):
    #print("Pressed buttons: ", pins)        

    if is_raspberry_pi:
        pictureFileName = "photo.jpg"
        camera.start_preview()
        sleep(0.5)
        camera.capture(pictureFileName)
        camera.stop_preview()
    else:
        pictureFileName = "photoDummy2.jpg"

    sendStatus("Analysing face...", 0)
    sendSerialMsg('P')

    with open(pictureFileName, mode='rb') as file: # b is important -> binary
        fileContent = file.read()

    fee = calculateFee(fileContent)
    if fee is not None:
        # Messages
        sendStatus("Estimated age " + str(int(round(fee.age))), 0)
        if fee.hasHeadwear:
            sendStatus("Headwear detected", 1)
        if fee.hasMakeup:
            sendStatus("Makeup detected", 1 * 2)
        elif fee.gender == "female":
            sendStatus("No makeup detected", 1 * 2)
        if fee.hasFacialHair:
            sendStatus("Beard detected", 1 * 3)
        if fee.isAggressive:
            sendStatus("Aggressive behavior detected", 1 * 4)
        elif sum(pins) > 1:
            fee.aggressive = 50
            sendStatus("Aggressive behavior detected", 1 * 4)
        if fee.hasBadMood:
            sendStatus("Bad mood detected", 1 * 5)


        # Add aggressive fee if multi press of button happens

        print "Makeup: " + str(fee.makeup)
        print "Pyjama: " + str(fee.pyjama)
        print "Hipster: " + str(fee.hipster)
        print "Youngster: " + str(fee.youngster)
        print "badMood: " + str(fee.badMood)
        print "Aggressive: " + str(fee.aggressive)

        photoData = imageParse(pictureFileName)

        #sendStatus("Printing...")
        if is_raspberry_pi and noPrint == False:
            sendStatus("Printing...", 1 * 6)
            thermal_printer = ThermalPrinter(photoData,384,153)
            thermal_printer.printReceipt(fee.makeup, fee.pyjama, fee.hipster, fee.youngster, fee.badMood, fee.aggressive)
            sendStatus("Done.", 0)
        else:
            sendStatus("Done.", 1 * 6)
    # ERROR Image not recognised
    else:
        sendSerialMsg('E')
        sendStatus("No face detected.", 0)
    #sendStatus("Take your bill.")

if is_raspberry_pi:
    buttonTracker = ButtonTracker(6, 13, 19, buttonPressed)    
else:
    buttonPressed(0,0)

while True:
    time.sleep(0.1)
    x=sys.stdin.read(1)[0]
    print("You pressed", x)

    #if arduinoSerial is not None:
    #    command = arduinoSerial.readline()
    #    print command
