# USB Power Switch Pro
#
# https://github.com/8086net/usb-pwr-switch-pro-examples/
#
# Compatible Pico W
#
# 2023-09-02
# 2023-09-27 Add support for Watchdog timer
#
# WiFi Buttons
#

# This example requires the additional library adafruit_httpserver
# which can be installed using circup
# https://learn.adafruit.com/keep-your-circuitpython-libraries-on-devices-up-to-date-with-circup/
#
# Once CircuitPython is installed plugin your "USB Power Switch Pro (with Pico W onboard)"
# copy the settings.toml and code.py files to the CIRCUITPY drive.
#
# Edit settings.toml to configure your WiFi credentials
# (See https://docs.circuitpython.org/en/latest/docs/environment.html )
#
# Then run the following command to install the required modules.
#
# circup install --auto
#

#
# Connect to the CircuitPython REPL USB Serial Console to view the IP address
# Visit the URL shown in a web browser (on the same WiFi network)
#

import os
import board
import wifi
import time
import microcontroller
import socketpool
from digitalio import DigitalInOut, Direction
from adafruit_httpserver import Server, Request, Response, POST
from watchdog import WatchDogMode

# Set to True to use watchdog timer to reboot on CircuitPython crashes
watchdogTimeout = False

device_name = "USBSwitch"

# Start with power on (True) or off (False)?

initialState = False

if watchdogTimeout:
	wdt = microcontroller.watchdog
	wdt.mode = WatchDogMode.RESET
	wdt.timeout = 8

# Setup GPIO pin for Power control

pwr = DigitalInOut(board.GP2)
pwr.direction = Direction.OUTPUT
pwr.value = initialState

# Setup web server

WiFi_SSID = os.getenv('CIRCUITPY_WIFI_SSID')
WiFi_Password = os.getenv('CIRCUITPY_WIFI_PASSWORD')

# Check WiFi connection details have been setup

if WiFi_SSID == None or WiFi_SSID == "" or WiFi_Password == None or WiFi_Password == "":
	while True:
		print("Waiting for WiFi details to be setup in settings.toml")
		if watchdogTimeout: wdt.feed()
		time.sleep(5)

print("Connecting to WiFi")
try:
	if watchdogTimeout: wdt.feed()
	wifi.radio.connect(WiFi_SSID, WiFi_Password)
except OSError:
	while True:
		print("Unable to connect to WiFi, check details in settings.toml")
		if watchdogTimeout: wdt.feed()
		time.sleep(5)

print("Starting web server")
try:
	if watchdogTimeout: wdt.feed()
	pool = socketpool.SocketPool(wifi.radio)
	server = Server(pool, "/static", debug=True)
	server.start(str(wifi.radio.ipv4_address))
except OSError:
	print("Restarting (Web server setup failed)")
	if watchdogTimeout: wdt.feed()
	time.sleep(5)
	microcontroller.reset()

# Return current status of USB Power Switch

def getState():
	global pwr

	if pwr.value:
		return "On"
	else:
		return "Off"

# Web server calls

@server.route("/")
def base(request: Request):  # pylint: disable=unused-argument
	return Response(request, f"{webpage()}", content_type='text/html')

@server.route("/", POST)
def buttonpress(request: Request):
	global pwr

	raw_text = request.raw_request.decode("utf8")

	if "ON" in raw_text:
		print("Turning on USB Power")
		pwr.value = True

	elif "OFF" in raw_text:
		print("Turning off USB Power")
		pwr.value = False

	else:
		print("Refresh")

	return Response(request, f"{webpage()}", content_type='text/html')

def webpage():
	html = f"""<html>
 <head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{device_name}</title>
 </head>
 <body>
  <h1>{device_name}</h1>
  Power Status: {getState()}<br /><br />
  <form accept-charset="utf-8" method="POST">
   <button class="button" name="pwron" value="ON" type="submit">Power On</button><br /><br />
   <button class="button" name="pwroff" value="OFF" type="submit">Power Off</button><br /><br />
   <button class="button" name="refresh" value="REFRESH" type="submit">Refresh</button><br />
  </form>
 </body>
</html>"""
	return html

# Main loop

print("Waiting for requests from web browser")
while True:
	try:
		if watchdogTimeout: wdt.feed()
		server.poll()
	except OSError:
		print("Restarting (Loop)")
		if watchdogTimeout: wdt.feed()
		time.sleep(5)
		microcontroller.reset()
