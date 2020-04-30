### MPU9250 and ESP32 sporting OLED screen (heltec)
All files included here are to be uploaded directly to the ESP32. There is no ``boot.py``. So be sure to add one yourself.<br />
All files are necessary to support the funcioning of ``main.py``<br />
A pushbutton with pull-up resistor on pin 38 is required for calibrating the IMU at startup.<br />
All supporting files are lifted from public repositories [micropython-mpu9x50](https://github.com/micropython-IMU/micropython-mpu9x50) and [micropython-fusion](https://github.com/micropython-IMU/micropython-fusion)<br />
I did all I could to modify things to work for me. I find that even with the fusion support it still has some drift, specifically on the Z axe.
