import RPi.GPIO as GPIO 
import threading
import time
import can
from debounce import ButtonHandler
GPIO.setmode(GPIO.BCM)

#GPIO pinout
pedalPin = 16

GPIO.setup(pedalPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


#can bus configuration
bustype = 'socketcan'
channel = 'can0'
bus = can.interface.Bus(channel=channel, bustype=bustype,bitrate=125000)

#frame defenition
#dataFrame = [State,_,_,_,angleA,angleB]
dataFrame = [0 ,0 ,0 ,0 ,0 ,0 ]
statePos = 0
angleAPos = 4
angleBPos = 5

#global variables
pedalPressTime=0.0
state = 0
rotaryAngle = 0
engaged = 0


def main():
	global pedalPressTime
	global dataFrame
	global state
	inp=input("Press enter to turn on the machine")
	state=1
	dataFrame[statePos] = state
	sendFrame()
	button = ButtonHandler(pedalPin, GPIO.RISING, button_callback,0.1)
	while True:
		inp= int(input("At any point,\n-Enter state number to force switch\n"))
		state = inp
		
		if state==0:
			print("Dis-engaging the clamp..")
			dataFrame[statePos] = 2
			sendFrame()
			print("Switching off..")
			dataFrame[statePos] = state
			sendFrame()
			break
		dataFrame[statePos] = state
		sendFrame()
		
def button_callback(args):    #function run on pedal press
	global pedalPressTime
	count=0
	print(f"button pressed!")
	while GPIO.input(pedalPin)==1:
		count+=1
		time.sleep(0.01)
	pedalPressTime = count*0.01
	print("for ", pedalPressTime, " seconds")
	updateState()

def updateAngle(angle=0):
	global dataFrame
	global angleAPos
	global angleBPos
	a=angle
	b=int(a/2)
	a-=b
	dataFrame[angleAPos] = a
	dataFrame[angleBPos] = b

def sendFrame():
	global dataFrame
	msg = can.Message(arbitration_id=0xc0ffee, data=dataFrame, is_extended_id=False)
	bus.send(msg)
	

def updateState():
	global pedalPressTime
	global rotaryAngle
	global state
	global engaged
	global dataFrame
	if  pedalPressTime>1.5:
		if engaged==0:
			print("execute clamping")
			engaged=1
			state=4
			dataFrame[statePos] = state
			sendFrame()
		else:
			print("execute un-clamping")
			engaged=0
			state=2
			dataFrame[statePos] = state
			sendFrame()
	else:
		if engaged:
			rotaryAngle= (0 if rotaryAngle==360 else rotaryAngle+45)
			print("Setting rotary axis to ",rotaryAngle," degree(s)")
			state=5
			dataFrame[statePos] = state
			updateAngle(rotaryAngle)
			sendFrame()

		else:
			print("currently unclamped!")



if __name__ == "__main__":
	try:
		main()
	except KeyboardInterrupt:
		print("Execute GPIO-cleanup")
		GPIO.cleanup()
	finally:
		print("Execute GPIO-cleanup")
		GPIO.cleanup()

