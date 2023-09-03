# USB Power Switch Pro
#
# https://github.com/8086net/usb-pwr-switch-pro-examples/
#
# Compatible Pico or Pico W
#
# 2023-09-03
#

# Temperature Switch
# 
# Uses Picos internal temperature sensor to switch USB On when set temperature exceeded.
# It then waits for the temperature to drop by "hysteresis" C 
#

import board
import time
import digitalio
import microcontroller

onTemp = 35 # Turn on at "onTemp" degrees C
hysteresis = 2 # Turn off when "hysteresis" degrees C below "onTemp"

# Setup GPIO pin for Power control

pwrCtrl = digitalio.DigitalInOut(board.GP2)
pwrCtrl.direction = digitalio.Direction.OUTPUT

# Setup GPIO pin for Slide Switch

slideSwitch = digitalio.DigitalInOut(board.GP13)
slideSwitch.switch_to_input(pull=digitalio.Pull.UP)

while True:
        temp = microcontroller.cpu.temperature
        print("Current Temp: "+str(temp))
        if pwrCtrl.value == False and temp >= onTemp:
                pwrCtrl.value = True
		print("Power on at: "+str(temp))
        elif pwrCtrl.value == True and temp <= (onTemp - hysteresis):
                pwrCtrl.value = False
		print("Power off at: "+str(temp))
	time.sleep(1)
