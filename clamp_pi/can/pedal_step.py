import RPi.GPIO as GPIO 
import threading
import time
from debounce import ButtonHandler
button_pin = 16
GPIO.setmode(GPIO.BCM)
GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def main():
    button = ButtonHandler(button_pin, GPIO.RISING, button_callback,0.1)
    message = input("Press enter to quit\n\n") # Run until someone presses enter

def button_callback(args):    #function run on b utton press
    print(f"button pressed!")


if __name__ == "__main__":
    try:
        main()
    finally:
        print("Execute GPIO-cleanup")
        # Cleanup is important when working with interrupts, so the pins not remain blocked. When used by another program.
        GPIO.cleanup()

