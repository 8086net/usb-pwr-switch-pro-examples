# USB Power Switch ProM
#
# https://github.com/8086net/usb-pwr-switch-pro-examples/
#
# Compatible Pico W
#
# MQTT USB Power Switch with power monitoring
#

# This example requires the additional libraries adafruit_bus_device, adafruit_minimqtt, adafruit_register, adafruit_connection_manager, adafruit_ina219, adafruit_tricks
# which can be installed using circup
# https://learn.adafruit.com/keep-your-circuitpython-libraries-on-devices-up-to-date-with-circup/
#
# Once CircuitPython is installed plugin your "USB Power Switch ProM or BJ Power Switch Pro (with Pico W onboard)"
# copy the settings.toml and code.py files to the CIRCUITPY drive.
#
# Edit settings.toml to configure your WiFi credentials, MQTT server settings, etc.
# (See https://docs.circuitpython.org/en/latest/docs/environment.html )
#
# Then run the following command to install the required modules.
#
# circup [--path x:] install --auto

import board
import busio
import wifi
import adafruit_connection_manager
import os
import digitalio
import time
import json
import random
import microcontroller
import supervisor
import adafruit_ina219
import adafruit_minimqtt.adafruit_minimqtt as MQTT
#import adafruit_logging as logging

# Get options from config file
MQTT_TOPIC_SENSOR = os.getenv("MQTT_TOPIC_SENSOR") or "tele/UNKNOWN/SENSOR"
MQTT_TOPIC_POWER  = os.getenv("MQTT_TOPIC_POWER") or "cmnd/UNKNOWN/POWER"

# Stop auto restart on file change (prevents toggling power unexpectedly)
supervisor.runtime.autoreload=False

# Setup GPIO pin for Power control
pwrCtrl = digitalio.DigitalInOut(board.GP2)
pwrCtrl.direction = digitalio.Direction.OUTPUT

pwrCtrl.value=True # Default to power turned on

interval = os.getenv("MQTT_SENSOR_INTERVAL") or 60

i2c = busio.I2C(board.GP1, board.GP0)

sensor = adafruit_ina219.INA219(i2c)

# Expects 20mOhm resistor
sensor.set_calibration_16V_5A()
sensor.bus_voltage_range = adafruit_ina219.BusVoltageRange.RANGE_32V

# Average out the current/voltage readings
sensor.bus_adc_resolution=adafruit_ina219.ADCResolution.ADCRES_12BIT_128S
sensor.shunt_adc_resolution=adafruit_ina219.ADCResolution.ADCRES_12BIT_128S

output = {}

# MQTT helper functions
def mqtt_message(client, topic, message):
	print(f"New message on topic {topic}: {message}")
	if message == "ON":
		pwrCtrl.value=True
	if message == "OFF":
		pwrCtrl.value=False

def mqtt_connected(client, userdata, flags, rc):
	print("Connected to MQTT broker")
	client.subscribe(MQTT_TOPIC_POWER)

def mqtt_disconnect(client, userdata, rc):
	print("Disconnected from MQTT broker restarting.")
	time.sleep(5)
	return

# Handles restarting everything without actually restarting
# Don't restart unless we have to otherwise power will be switched off
def start():
	print("Starting")

	# Connect to Wifi
	try:
		print("Connecting to WiFi")
		wifi.radio.enabled=False
		wifi.radio.enabled=True
		wifi.radio.connect(
		    os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD")
		)
	except Exception as e:
		print("Unable to connect WiFi")
		print(e)
		time.sleep(5)
		return

	print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}")
	print(f"My IP address: {wifi.radio.ipv4_address}")

	# Check if the gateway is pingable (ping is IPv4 only)
	gw = wifi.radio.ipv4_gateway
	if gw != None:
		print(f"Checking gateway {gw} responds to ping: ", end="")
		time.sleep(0.5)
		ping = wifi.radio.ping(gw)
		if ping == None:
			print("No.")
			return
		else:
			print(f"Yes: {ping} seconds.")

	adafruit_connection_manager.connection_manager_close_all(release_references=True)

	# Set up a MiniMQTT Client
	mqtt_client = MQTT.MQTT(
		broker=os.getenv("MQTT_BROKER"),
		port=os.getenv("MQTT_PORT"),
		username=os.getenv("MQTT_USERNAME"),
		password=os.getenv("MQTT_PASSWORD"),
		socket_pool=adafruit_connection_manager.get_radio_socketpool(wifi.radio),
		ssl_context=adafruit_connection_manager.get_radio_ssl_context(wifi.radio),
	)
#	mqtt_client.logger = logging.getLogger()
#	mqtt_client.logger.setLevel(logging.DEBUG)
	mqtt_client.on_message = mqtt_message
	mqtt_client.on_connect = mqtt_connected
	mqtt_client.on_disconnect = mqtt_disconnect

	while not mqtt_client.is_connected():
		print(f"Attempting to connect to {mqtt_client.broker}")
		try:
			mqtt_client.connect()
		except Exception as e:
			print(e)
			print("Unable to connect MQTT")
			time.sleep(5)
			return
	while True:
		try:
			mA = sensor.current
			v = sensor.bus_voltage
			W = sensor.power
		except:
			print("Unable to communicate with INA219")
			time.sleep(5)
			return

		# Can't be any real usage if the output is turned off
		if pwrCtrl.value == False:
			v = 0
			mA = 0
			W = 0

		print(f"V: {v:.3f} // mA: {mA:.3f} // W: {W:.3f}")

		if sensor.overflow:
			print("ERROR: overflow")

		output = {
				'ENERGY': {
					"Voltage": v,
					"Current": mA/1000,
					"Power" : W,
					"Factor": 1,
					"ApparentPower": W,
					"ReactivePower": W,
					"Total": 0,
				},
				'DEVICE': {
					'MAC': [hex(i) for i in wifi.radio.mac_address],
					'IP': str(wifi.radio.ipv4_address),
				}
			}

		print(f"Publishing to {MQTT_TOPIC_SENSOR}")
		try:
			mqtt_client.publish(MQTT_TOPIC_SENSOR, json.dumps(output))
		except:
			print("MQTT Publish error, restarting")
			time.sleep(5)
			return

		# Wait before sending data again
		print("Waiting for next poll")
		wait_until = time.time()+interval
		while time.time()<wait_until:
			mqtt_client.loop(timeout=1)
			time.sleep(1)

while True:
	# Sleep up to "interval" seconds to prevent everything reconnecting at once after power outage/broker restart
	r = random.randint(1,interval)
	print(f"Waiting {r} seconds before [re]start.")
	time.sleep( r )
	try:
		start()
	except Exception as e:
		print("Exception")
		print(e)
