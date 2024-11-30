# USB Power Switch ProM
#
# https://github.com/8086net/usb-pwr-switch-pro-examples/
#
# Compatible Pico W
#
# MQTT USB Switch with power monitoring
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
# circup install --auto

import board
import busio
import wifi
import ssl
import socketpool
import os
import digitalio
import time
import json
import microcontroller
import adafruit_ina219
import adafruit_minimqtt.adafruit_minimqtt as MQTT

# Get options from config file
MQTT_TOPIC_SENSOR = os.getenv("MQTT_TOPIC_SENSOR") or "tele/UNKNOWN/SENSOR"
MQTT_TOPIC_POWER  = os.getenv("MQTT_TOPIC_POWER") or "cmnd/UNKNOWN/POWER"

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
	print(f"Connected to MQTT broker")
	client.subscribe(MQTT_TOPIC_POWER)

def mqtt_disconnect(client, userdata, rc):
	print(f"Disconnected from MQTT broker resetting.")
	time.sleep(5)
	return #microcontroller.reset()

# Handle restarting everything without actually restarting
# Don't restart unless we have to otherwise power will be switched off
def start():
	print("START")
	# Connect to Wifi
	try:
		print("Connecting to WiFi")
		wifi.radio.connect(
		    os.getenv("CIRCUITPY_WIFI_SSID"), os.getenv("CIRCUITPY_WIFI_PASSWORD")
		)
	except:
		print("Unable to connect WiFi")
		time.sleep(5)
		return #microcontroller.reset()

	print(f"Connected to {os.getenv('CIRCUITPY_WIFI_SSID')}")
	print(f"My IP address: {wifi.radio.ipv4_address}")

	# Create a socket pool
	pool = socketpool.SocketPool(wifi.radio)

	# Set up a MiniMQTT Client
	mqtt_client = MQTT.MQTT(
		broker=os.getenv("MQTT_BROKER"),
		port=os.getenv("MQTT_PORT"),
		username=os.getenv("MQTT_USERNAME"),
		password=os.getenv("MQTT_PASSWORD"),
		socket_pool=pool,
		ssl_context=ssl.create_default_context(),
	)

	mqtt_client.on_message = mqtt_message
	mqtt_client.on_connect = mqtt_connected
	mqtt_client.on_disconnect = mqtt_disconnect

	while not mqtt_client.is_connected():
		print(f"Attempting to connect to {mqtt_client.broker}")
		try:
			mqtt_client.connect()
		except Exception as exp:
			print(exp)
			print("Unable to connect MQTT")
			time.sleep(5)
			return #microcontroller.reset()

	while True:
		try:
			mA = sensor.current
			v = sensor.bus_voltage
			W = sensor.power
		except:
			print("Unable to communicate with INA219")
			time.sleep(5)
			return #microcontroller.reset()

		# Shouldn't be any voltag/current/power if it's turned off
		if not pwrCtrl.value:
			v = 0
			mA = 0
			W = 0
	
		print("V: {:.3f} // mA: {:.3f} // W: {:.3f}".format(v, mA, W) )

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

		print("Publishing to %s" % MQTT_TOPIC_SENSOR)
		try:
			mqtt_client.publish(MQTT_TOPIC_SENSOR, json.dumps(output))
		except:
			print("MQTT Publish error, restarting")
			time.sleep(5)
			return #microcontroller.reset()

		# Wait before sending data again
		print("Waiting for next poll")
		wait_until = time.time()+interval
		while time.time()<wait_until:
			mqtt_client.loop(timeout=1)
			time.sleep(1)


while True:
	try:
		start()
	except Exception as e:
		print("Exception: "+e)
