import RPi.GPIO as GPIO 
import threading
import time
import can
from debounce import ButtonHandler
buttonPin = 16

GPIO.setmode(GPIO.BCM)
GPIO.setup(buttonPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
triggerCount=0
pressTime=0.0

bustype = 'socketcan'
channel = 'can0'
bus = can.interface.Bus(channel=channel, bustype=bustype,bitrate=125000)

def main():
	global triggerCount
	global pressTime
	button = ButtonHandler(button_pin, GPIO.RISING, button_callback,0.1)
	message = input("Press enter to quit\n\n") # Run until someone presses enter
		
def button_callback(args):    #function run on button press
	global trigger_count
	global pressTime
	count=0
	print(f"button pressed!")
	while GPIO.input(button_pin)==1:
		count+=1
		time.sleep(0.01)
	print("for ", (count*0.01), " seconds")
	    
if __name__ == "__main__":
	try:
		main()
	except KeyboardInterrupt:
		print("Execute GPIO-cleanup")
		GPIO.cleanup()
	finally:
		print("Execute GPIO-cleanup")
		GPIO.cleanup()

