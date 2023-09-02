# USB Power Switch Pro
#
# https://github.com/8086net/usb-pwr-switch-pro-examples/
#
# Compatible Pico or Pico W
#
# 2023-08-30
#

# Momentary Push Button
# 
# Connect switch between GND and GP13
#

import board
import digitalio
import keypad

# Start with power on (True) or off (False)?

initialState = False

# Setup GPIO pin for Power control

pwrCtrl = digitalio.DigitalInOut(board.GP2)
pwrCtrl.direction = digitalio.Direction.OUTPUT
pwrCtrl.value = initialState

# Setup the Switch using the keypad module.
# See https://learn.adafruit.com/key-pad-matrix-scanning-in-circuitpython/overview for documentation on the keypad module.

keys = keypad.Keys((board.GP13,), value_when_pressed=False, pull=True)

while True:
	# Get any keypad events
	event = keys.events.get()

	# Check if there was an event, if so was it a keypress?
	if event and event.pressed:
		# Button pressed so toggle the power control pin
		pwrCtrl.value = not pwrCtrl.value
