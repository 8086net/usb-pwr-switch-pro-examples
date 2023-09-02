# USB Power Switch Pro
#
# https://github.com/8086net/usb-pwr-switch-pro-examples/
#
# Compatible Pico or Pico W
#
# 2023-08-30
#

# Simple slide button
# 
# Connect a slide or toggle switch between GND and GP13
#

import board
import digitalio

# Setup GPIO pin for Power control

pwrCtrl = digitalio.DigitalInOut(board.GP2)
pwrCtrl.direction = digitalio.Direction.OUTPUT

# Setup GPIO pin for Slide Switch

slideSwitch = digitalio.DigitalInOut(board.GP13)
slideSwitch.switch_to_input(pull=digitalio.Pull.UP)

while True:
	if slideSwitch.value:
		pwrCtrl.value = False
	else:
		pwrCtrl.value = True
