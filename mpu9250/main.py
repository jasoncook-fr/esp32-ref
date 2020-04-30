from machine import Pin
import machine
import uasyncio as asyncio
import gc
from mpu9250 import MPU9250
from fusion_async import Fusion # Using async version
import ssd1306
import time

switch = Pin(38, Pin.IN)
i2c = machine.I2C(scl=machine.Pin(22), sda=machine.Pin(21))
imu = MPU9250(i2c)

# Activation OLED
i2cOLED = machine.I2C(scl=machine.Pin(15), sda=machine.Pin(4))
reset_oled = machine.Pin(16, machine.Pin.OUT)
reset_oled.value(0)
time.sleep(.05)
reset_oled.value(1)
oled = ssd1306.SSD1306_I2C(128, 64, i2cOLED)  # 128 x 64 pixels

# User coro returns data and determines update rate.
# For 9DOF sensors returns three 3-tuples (x, y, z) for accel, gyro and mag
# For 6DOF sensors two 3-tuples (x, y, z) for accel and gyro
async def read_coro():
    #imu.mag_trigger()
    await asyncio.sleep_ms(20)  # Plenty of time for mag to be ready
    return imu.accel.xyz, imu.gyro.xyz, imu.mag.xyz

fuse = Fusion(read_coro)

async def mem_manage():         # Necessary for long term stability
    while True:
        await asyncio.sleep_ms(100)
        gc.collect()
        gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())

async def display():
    while True:
        oled.fill(0)
        oled.text("{:5s}{:5s} {:5s}".format("Yaw","Pitch","Roll"), 1, 20)
        myHeading = fuse.heading + 180
        myPitch = fuse.pitch + 180
        myRoll = fuse.roll + 180
        oled.text("{:4.0f} {:4.0f} {:4.0f}".format(myHeading, myPitch, myRoll), 1, 40)
        oled.show()
        
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
    loop.create_task(display())

loop = asyncio.get_event_loop()
loop.create_task(mem_manage())
loop.create_task(lcd_task())
loop.run_forever()