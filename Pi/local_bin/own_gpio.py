#!/usr/bin/python
# This script is created to be able to run it as root,
# which is required to control the GPIO pins.
import sys
import argparse
import RPi.GPIO as GPIO ## Import GPIO library
import time


# Gets the distance in cm using the ultrasonic sensor.
# Returns 0 if an invalid value is measured.
def getUsSensorDistance(UsPinTrig, UsPinEcho):

  GPIO.setup(UsPinTrig, GPIO.OUT)          # Set trigger pin as GPIO out
  GPIO.setup(UsPinEcho, GPIO.IN)           # Set echo pin as GPIO in
  GPIO.output(UsPinTrig, False)            # Set UsPinTrig as LOW
  GPIO.output(UsPinTrig, True)             # Set UsPinTrig as HIGH
  time.sleep(0.00001)                      # Delay of 0.00001 seconds
  GPIO.output(UsPinTrig, False)            # Set UsPinTrig as LOW

  # Use waitTime as a guard to make sure this loop ends.
  waitTime = 0
  startTime = time.time()
  while GPIO.input(UsPinEcho)==0 and waitTime < 0.001:  # waitTime should be around 0.0004
      pulse_start = time.time()            # Saves the last known time of LOW pulse
      waitTime = pulse_start - startTime
  if waitTime == 0 or waitTime >= 0.001:
      return 0
  
  # Use waitTime as a guard to make sure this loop ends.
  waitTime = 0
  startTime = time.time()
  while GPIO.input(UsPinEcho)==1 and waitTime < 0.02: # At 3.5 meter waitTime is about 0.02
      pulse_end = time.time()              # Saves the last known time of HIGH pulse
      waitTime = pulse_end - startTime
  if waitTime == 0 or waitTime >= 0.02:
      return 0

  pulse_duration = pulse_end - pulse_start # Get pulse duration to a variable

  distance = pulse_duration * 17150        # Multiply pulse duration by 17150 to get distance in cm
  distance = round(distance, 2)            # Round to two decimal points
  # Check if the measured distance makes sense, alse return 0.
  if distance < 3.0 or distance > 300.0:
      distance = 0
  return distance


# Switch off GPIO warnings to prevent the 'RuntimeWarning: This channel is already in use' warning.
# This warning occurs when multiple GPIO scripts are running and also when one GPIO script is called
# multiple times. Because this script runs multiple times we disable the warning.
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM) # Use board pin numbering
# Handle arguments.
parser = argparse.ArgumentParser()
parser.add_argument('--loudspeaker', choices = ['on','off'])
parser.add_argument('--us_sensor', choices = ['1','2','3','4'])
args = parser.parse_args()

# Loudspeaker GPIO pin to switch loudspeaker on or off.
GPIO.setup(4, GPIO.OUT) # Setup GPIO Pin 4 to OUT.
if args.loudspeaker == 'on':
    GPIO.output(4,True) # Turn on loudspeaker.
elif args.loudspeaker == 'off':
    GPIO.output(4,False) # Turn off loudspeaker.
elif args.us_sensor == '1':
    # Assign pins of ultrasonic sensor #1
    US_PIN_TRIG = 12
    US_PIN_ECHO = 6
    distance = getUsSensorDistance(US_PIN_TRIG, US_PIN_ECHO)
    print distance





