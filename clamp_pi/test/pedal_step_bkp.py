import RPi.GPIO as GPIO 
import threading
import time
import can
from debounce import ButtonHandler
button_pin = 16
GPIO.setmode(GPIO.BCM)
GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
old_count=0
new_count=0

bustype = 'socketcan'
channel = 'can0'
bus = can.interface.Bus(channel=channel, bustype=bustype,bitrate=125000)

def main():
	global new_count
	button = ButtonHandler(button_pin, GPIO.RISING, button_callback,0.1)
	#message = input("Press enter to quit\n\n") # Run until someone presses enter
	while 1:
		new_count = button.trigger_count

def button_callback(args):    #function run on b utton press
	global trigger_count
	print(f"button pressed!")
	print(new_count)
		
		a=int(input("enter angle: "))
		b=int(a/2)
		a-=b
		msg = can.Message(arbitration_id=0xc0ffee, data=[0, 1, 3, 1, a, b], is_extended_id=False)
		bus.send(msg)
    
if __name__ == "__main__":
	try:
		main()
	finally:
		print("Execute GPIO-cleanup")
		# Cleanup is important when working with interrupts, so the pins not remain blocked. When used by another program.
		GPIO.cleanup()

