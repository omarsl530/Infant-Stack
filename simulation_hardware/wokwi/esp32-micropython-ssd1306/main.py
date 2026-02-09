from machine import Pin, I2C
import ssd1306
import time

print("Booting SSD1306 Demo...")

# ESP32 Pin assignment 
i2c = I2C(0, scl=Pin(22), sda=Pin(21))

print("Scanning I2C bus...")
devices = i2c.scan()
if devices:
    print(f"I2C devices found: {[hex(d) for d in devices]}")
else:
    print("No I2C devices found!")

try:
    oled_width = 128
    oled_height = 64
    oled = ssd1306.SSD1306_I2C(oled_width, oled_height, i2c)

    print("Display initialized. Drawing text...")
    oled.fill(0)
    oled.text('Hello, Wokwi!', 10, 10)
    oled.text('I work!', 10, 30)
    oled.show()
    print("Text displayed.")
except Exception as e:
    print(f"Error initializing display: {e}")

