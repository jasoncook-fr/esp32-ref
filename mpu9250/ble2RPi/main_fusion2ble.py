import machine
import uasyncio as asyncio
import gc
from mpu9250 import MPU9250
from fusion_async import Fusion # Using async version
import ssd1306
import bluetooth
import struct
from micropython import const
from ble_advertising import advertising_payload
import time

switch = machine.Pin(38, machine.Pin.IN)
i2c = machine.I2C(scl=machine.Pin(22), sda=machine.Pin(21))
imu = MPU9250(i2c)
imuVals = [0, 0, 0]
# Activation OLED
i2cOLED = machine.I2C(scl=machine.Pin(15), sda=machine.Pin(4))
reset_oled = machine.Pin(16, machine.Pin.OUT)
reset_oled.value(0)
time.sleep(.05)
reset_oled.value(1)
oled = ssd1306.SSD1306_I2C(128, 64, i2cOLED)  # 128 x 64 pixels

################## Blutetooth Preparations ######################
_IRQ_CENTRAL_CONNECT = const(1 << 0)
_IRQ_CENTRAL_DISCONNECT = const(1 << 1)
# org.bluetooth.service.environmental_sensing
_ENV_SENSE_UUID = bluetooth.UUID(0x181A)
# org.bluetooth.characteristic.analog
_ANALOG_CHAR = (
    bluetooth.UUID(0x2A58),
    bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY,
)
_ENV_SENSE_SERVICE = (
    _ENV_SENSE_UUID,
    (_ANALOG_CHAR,),
)
# org.bluetooth.characteristic.gap.appearance.xml
_ADV_APPEARANCE_UNKNOWN = const(0) # maybe change in the future

class BLEadc:
    def __init__(self, ble, name="mpy-adc"):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(handler=self._irq)
        ((self._handle,),) = self._ble.gatts_register_services((_ENV_SENSE_SERVICE,))
        self._connections = set()
        self._payload = advertising_payload(
            name=name, services=[_ENV_SENSE_UUID], appearance=_ADV_APPEARANCE_UNKNOWN
        )
        self._advertise()

    def _irq(self, event, data):
        # Track connections so we can send notifications.
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _, = data
            self._connections.add(conn_handle)
        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _, = data
            self._connections.remove(conn_handle)
            # Start advertising again to allow a new connection.
            self._advertise()

    def set_adcVal(self, adcVal, notify=False):
        # Write the local value, ready for a central to read.
        self._ble.gatts_write(self._handle, struct.pack("<hh", int(adcVal[0]), int(adcVal[1])))
        if notify:
            for conn_handle in self._connections:
                # Notify connected centrals to issue a read.
                self._ble.gatts_notify(conn_handle, self._handle)

    def _advertise(self, interval_us=500000):
        self._ble.gap_advertise(interval_us, adv_data=self._payload)


# User coro returns data and determines update rate.
async def read_coro():
    await asyncio.sleep_ms(20)  # Plenty of time for mag to be ready
    return imu.accel.xyz, imu.gyro.xyz, imu.mag.xyz

fuse = Fusion(read_coro)

async def mem_manage():         # Necessary for long term stability
    while True:
        await asyncio.sleep_ms(100)
        gc.collect()
        gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())

async def pollData():
    ble = bluetooth.BLE()
    adc = BLEadc(ble)
    t = 25
    i = 0

    while True:
        imuVals[0] = fuse.heading + 180
        imuVals[1] = fuse.roll + 180
        imuVals[2] = fuse.pitch + 180
        oled.fill(0)
        oled.text("{:5s}{:5s} {:5s}".format("Yaw","Pitch","Roll"), 1, 20)
        oled.text("{:4.0f} {:4.0f} {:4.0f}".format(imuVals[0], imuVals[1], imuVals[2]), 1, 40)
        oled.show()
        i = (i + 1) % 10
        adc.set_adcVal(imuVals, notify=i == 0)
        await asyncio.sleep_ms(500)

async def lcd_task():
    print('Running test...')
    if switch.value() == 1:
        oled.fill(0)
        oled.text("Calibrate. Push", 1, 20)
        oled.text("switch when done", 1, 40)
        oled.show()
        await asyncio.sleep_ms(100)  # Let LCD coro run
        await fuse.calibrate(lambda : not switch.value())
        print(fuse.magbias)
    await fuse.start()  # Start the update task
    loop = asyncio.get_event_loop()
    loop.create_task(pollData())
    
loop = asyncio.get_event_loop()
loop.create_task(mem_manage())
loop.create_task(lcd_task())
loop.run_forever()
