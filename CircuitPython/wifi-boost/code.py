# USB Power Switch Pro
#
# https://github.com/8086net/usb-pwr-switch-pro-examples/
#
# Compatible Pico W
#
# 2023-09-03
# 2023-09-27 Add support for Watchdog timer
#
# WiFi Boost
#
# Connect ON/BOOST switch between GND and GP12
# Connect OFF switch between GND and GP13
# 
#

# This example requires the additional libraries adafruit_httpserver, adafruit_ntp
# which can be installed using circup
# https://learn.adafruit.com/keep-your-circuitpython-libraries-on-devices-up-to-date-with-circup/
#
# Once Python is installed plugin your "USB Power Switch Pro (with Pico W onboard)"
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
# Once running watch over USB Serial and connect a browser to IP address shown
#

import os
import time
import board
import rtc
import wifi
import socketpool
import microcontroller
import adafruit_ntp
from digitalio import DigitalInOut, Direction, Pull
import keypad
from adafruit_httpserver import Server, Request, Response, POST
from watchdog import WatchDogMode

# Set to True to use watchdog timer to reboot on CircuitPython crashes
watchdogTimeout = False

# Number of seconds to turn on for when boost button is pressed
onBoost = 60*30 # 30 minutes

# Start with power on (True) or off (False)?

initialState = False

# https://learn.adafruit.com/key-pad-matrix-scanning-in-circuitpython/keys-one-key-per-pin

# GP12 = power on for "onBoost" seconds
# GP13 = power off

keys = keypad.Keys((board.GP12, board.GP13), value_when_pressed=False, pull=True)

# GPIO Setup
pwr = DigitalInOut(board.GP2)
pwr.direction = Direction.OUTPUT
pwr.value = initialState

offAt = None

WiFi_SSID = os.getenv('CIRCUITPY_WIFI_SSID')
WiFi_Password = os.getenv('CIRCUITPY_WIFI_PASSWORD')
device_name = os.getenv('CIRCUITPY_WEB_INSTANCE_NAME') or "USBSwitch"

# Init Watchdog
if watchdogTimeout:
	wdt = microcontroller.watchdog
	wdt.mode = WatchDogMode.RESET
	wdt.timeout = 8

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

# Update time and setup web server
try:
	if watchdogTimeout: wdt.feed()
	ntp = adafruit_ntp.NTP(pool, tz_offset=0)
	print("Getting time via NTP")
	rtc.RTC().datetime = ntp.datetime
	lastntp = time.time()
except OSError:
	print("Restarting (Initial NTP failed)")
	if watchdogTimeout: wdt.feed()
	time.sleep(5)
	microcontroller.reset()

# Helper functions

# return string of current date/time
def getTime(t):
	if t == None:
		return " - "
	d=time.localtime(t)
	return "%4d-%02d-%02d %02d:%02d:%02d" % (d[0],d[1],d[2],d[3],d[4],d[5])

# Return current status of USB Power Switch

def getState():
	global pwr
	if pwr.value:
		return "On"
	else:
		return "Off"

# Boot ON period by X seconds
def boost(t):
	global offAt, pwr

	pwr.value=True
        
	if offAt == None: # Not currently on 
		offAt = time.time()+t
		print("Schedule off At: ", end="")
	else: # Already on so add t seconds to offAt
		offAt = offAt+t
		print("Schedule now off At: ", end="")
	print(time.localtime(offAt))

# Turn OFF power and reset "offAt"
def turnOff():
	global pwr, offAt
	print("Turning off at: " + getTime(time.time()) )
	pwr.value=False
	offAt = None

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
		turnOff()
	elif "BOOST15" in raw_text:
		boost(15*60)
	elif "BOOST30" in raw_text:
		boost(30*60)
	elif "BOOST45" in raw_text:
		boost(45*60)
	elif "BOOST60" in raw_text:
		boost(60*60)
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
  Power Status: {getState()}<br />
  Power offAt: {getTime(offAt)}<br />
  Time now: {getTime(time.time())}<br /><br />
  <form accept-charset="utf-8" method="POST">
   <button class="button" name="pwron" value="ON" type="submit">Power On</button>
   <button class="button" name="pwroff" value="OFF" type="submit">Power Off</button>
   <button class="button" name="refresh" value="REFRESH" type="submit">Refresh</button>
   <br /><br /><br />
   <button class="button" name="pwrboost" value="BOOST15" type="submit">On +15 min</button>
   <button class="button" name="pwrboost" value="BOOST30" type="submit">On +30 min</button>
   <br /><br /><br />
   <button class="button" name="pwrboost" value="BOOST45" type="submit">On +45 min</button>
   <button class="button" name="pwrboost" value="BOOST60" type="submit">On +1 hr</button>
  </form>
 </body>
</html>"""
	return html

# Main loop

print("Waiting for requests from web browser")
while True:
	if watchdogTimeout: wdt.feed()

	# Once a day try to update the time via NTP

	if lastntp+60*60*24 < time.time():
		print("Updating RTC from NTP")
		print(time.localtime())
		try:
			rtc.RTC().datetime = ntp.datetime
			print(time.localtime())
		except Exception as e:
			print("NTP Update failed")

		# Even if it failed we don't try again until tomorrow
		lastntp=time.time()

	# Check for keypress

	event = keys.events.get()
	if event:
		if event.key_number == 0 and event.pressed: # GP12 pressed
			boost(onBoost)
		if event.key_number == 1 and event.pressed: # GP13 pressed
			turnOff()

	# If "offAt" has been reached turn the power OFF
	if offAt != None and time.time() > offAt:
		turnOff()

	try:
		if watchdogTimeout: wdt.feed()
		server.poll()
	except OSError:
		print("Restarting (Loop)")
		if watchdogTimeout: wdt.feed()
		time.sleep(5)
		microcontroller.reset()
