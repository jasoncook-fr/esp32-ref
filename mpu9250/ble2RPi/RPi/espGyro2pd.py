#!/usr/bin/env python
import sys, errno
from gpiozero import PWMLED
import OSC
import binascii
import struct
import time
import OSC
import os
from bluepy.btle import *

led = PWMLED(13)

ESP_MAC_ADDR = "a4:cf:12:02:c3:6e"
adc_uuid = UUID(0x2A58)
p = Peripheral()

#-------------- init puredata stuff ------------------
os.system('puredata -nogui -audiodev 3 perky-recv-data.pd &')
print "=============="
print "starting PD!!!"
print "=============="
time.sleep(3)
send_address = '127.0.0.1', 9001
c = OSC.OSCClient()
c.connect(send_address)   # localhost, port 9001
oscmsg = OSC.OSCMessage()
oscmsg.setAddress("/pdRecv") #address name is declared in pd patch
sensorVals = [0,0] #X and Y values from fusioned mpu9250

def sendMsg(goData):
    oscmsg.append(goData)
    c.send(oscmsg)
    #erase the values from our oscmsg function (i.e. refresh)
    for x in range(0, len(goData)):
        oscmsg.remove(goData[x])

while 1:
    try:
        print "attempting to connect to ", ESP_MAC_ADDR
        p.connect(ESP_MAC_ADDR, "public")
        print "SUCCESS"
        ch = p.getCharacteristics(uuid=adc_uuid)[0]

        if (ch.supportsRead()):
            while 1:
                val = binascii.b2a_hex(ch.read())
                val = binascii.unhexlify(val)
                sensorVals[0] = struct.unpack('<hh', val)[0]
                sensorVals[1] = struct.unpack('<hh', val)[1]
                print "Pitch: ", sensorVals[0], "   Roll: ", sensorVals[1]
                sensorVals[0] = (sensorVals[0])*7
                sensorVals[1] = (sensorVals[1])*5
                sendMsg(sensorVals)
                '''
                ledVal = sensorVals[0]
                led.value = ledVal
                '''
    except IOError as e:
        if e.errno == errno.EPIPE:
            print "IO error... ignoring"
            time.sleep(.5)
            p = Peripheral() # re-initialize peripheral
            p.disconnect()
            continue

    except BTLEDisconnectError:
        print "Device disconnected!"
        time.sleep(.5)
        print "connect is false"
        p.disconnect()
        continue

    except BTLEInternalError:
        print "internal error... ignoring"
        time.sleep(.5)
        p.disconnect()
        continue
