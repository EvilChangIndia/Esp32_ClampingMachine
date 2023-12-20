#The machine states are as follows
#state -1: FailSafe
#state 0: OFF
#state 1: ON
#state 2: Un Clamped
#state 3: Calibration
#state 4: Clamped
#state 5: Angle Update
#state 6: Stepper Run
from subprocess import call
import RPi.GPIO as GPIO 
import threading
import time
import can
from debounce import ButtonHandler
import gi 
gi.require_version('Gtk', '3.0')            # Load the correct namespace and version of GTK
from gi.repository import Gtk               # Include the python bindings for GTK
from gi.repository import GLib              # included for adding things to gtk main loop

#import UI glade file into a GTK.Builder object
gladeFile = "UI_v2.glade"      # Variable gladeFile holding the XML file path 
builder = Gtk.Builder()            # GTK Builder called 
builder.add_from_file(gladeFile)   # GTK Builder passed the XML file path for translation

#define window and notebook onjects and link it to our design using the builder object
notebook=builder.get_object("mainNotebook")
window = builder.get_object("mainWindow")
statusBoxOff = builder.get_object("statusBoxOff").get_buffer()
timeBoxOff = builder.get_object("timeBoxOff").get_buffer()
infoBoxOff = builder.get_object("infoBoxOff").get_buffer()
statusBoxOn = builder.get_object("statusBoxOn").get_buffer()
timeBoxOn = builder.get_object("timeBoxOn").get_buffer()
infoBoxOn = builder.get_object("infoBoxOn").get_buffer()
infoBoxClamped = builder.get_object("infoBoxClamped").get_buffer()

#GPIO pinout
pedalPin = 16

GPIO.setmode(GPIO.BCM)
GPIO.setup(pedalPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


#can bus configuration
bustype = 'socketcan'
channel = 'can0'
bus = can.interface.Bus(channel=channel, bustype=bustype,bitrate=125000)
clamp_ID = 0x7D0      #address of clamp set to 2000

#frame defenition
#dataFrame = [State,_,_,_,angleA,angleB]
dataFrame = [0 ,0 ,0 ,0 ,0 ,0 ]
statePos = 0
angleAPos = 4
angleBPos = 5

#global variables
pedalPressTime=0.0
state = 0
prevState = 0
rotorAngle = 0
engaged = 0
clampTime = 1   #time for pneumatic clamping in seconds
operationWaitTime = 30 #half seconds
receiveWaitTime = 5
rotorHome = 270   #angular offset from encoder to home position
#operationAcknowledge={0:10, 1:11}
#define a class for handling on UI inputs
class Handler:
	#onDestroy triggers. can use just one onDestroy 
	def onDestroy(self, *args):
		print("Destroy triggered")
		Gtk.main_quit()
		GPIO.cleanup()
		
	#button triggers
	def onButtonPressExit(self, button):
		print("Exit button pressed")
		notebook.set_current_page(0)
		
		
	def onButtonPressPoweroff(self, button):
		print("Power button pressed")
		Gtk.main_quit()
		GPIO.cleanup()
	
	def onButtonPressRestart(self, button):
		print("Restart button pressed")
		Gtk.main_quit()
		GPIO.cleanup()
	
	def onButtonPressBack(self, button):
		print("Back button pressed")
		notebook.set_current_page(1)
		
	def onButtonPressOn(self, button):
		global state
		global rotorAngle
		global rotorHome
		print("on button pressed")
		#turn machine on
		state = 1
		sendFrame()
		status = checkProgress(state, operationWaitTime) #replace with diff wait time
		print("Machine turned ON") if status else print("Operation failed")#enter failsafe here
		#
		print("Calibrating rotor")
		state=3
		sendFrame()
		status = checkProgress(state, operationWaitTime) #replace with diff wait time
		print("Machine calibrated") if status else print("calibration failed")#enter failsafe here
		#move rotor to home
		print("Homing..")
		state = 5
		rotorAngle = rotorHome
		updateDFAngle()
		sendFrame()
		status = checkProgress(state, operationWaitTime) #replace with diff wait time
		print("Machine home") if status else print("homing failed")#enter failsafe here
		#switch to un-clamped state
		print("Unclamping")
		state = 2
		sendFrame()
		status = checkProgress(state, operationWaitTime) #replace with diff wait time
		print("Machine Unclamped") if status else print("Unclamping failed")#enter failsafe here
		#switch ui page
		notebook.set_current_page(2)
	
	def onButtonPressOff(self, button):
		global state
		print("off button pressed")
		state = 0
		sendFrame()
		status = checkProgress(state, operationWaitTime) #replace with diff wait time
		print("Machine OFF") if status else print("Turning OFF failed")#enter failsafe here
		notebook.set_current_page(1)
		
	def onButtonPressClamp(self, button):
		global state
		global engaged
		print("clamp button pressed")
		#statusBoxClamped.set_text("Machine is ON.\nClamp ENGAGED")
		state = 4
		sendFrame()
		status = checkProgress(state, operationWaitTime) #replace with diff wait time
		print("Machine clamped") if status else print("clamping failed")#enter failsafe here
		engaged = 1
		notebook.set_current_page(3)
	
	def onButtonPressUnclamp(self, button):
		global state
		global engaged
		print("un-clamp button pressed")
		if (rotorAngle==rotorHome):
			state = 2
			sendFrame()
			status = checkProgress(state, operationWaitTime) #replace with diff wait time
			print("Machine Unclamped") if status else print("Unclamping failed")#enter failsafe here
			notebook.set_current_page(2)
			engaged=0
		else:
			#fix this byatch
			print("Home the rotor, before unclamping!")
			infoBoxClamped.set_text("Machine is in state "+str(state)+"\nClamp in state "+str(engaged)+"\nRotor at angle"+str(rotorAngle)+"\n\n\nHome the rotor, before unclamping!")
	
	def onButtonPressCW(self, button):
		global state
		global rotorAngle
		print("+90 button pressed")
		state = 5
		rotorAngle= (0 if rotorAngle==360 else rotorAngle+90)
		updateDFAngle()
		sendFrame()
		status = checkProgress(state, operationWaitTime) #replace with diff wait time
		print("Motion successful") if status else print("motion failed")#enter failsafe here
	
	def onButtonPressACW(self, button):
		global state
		global rotorAngle
		print("-90 button pressed")
		state = 5
		rotorAngle= (360 if rotorAngle==0 else rotorAngle-90)
		updateDFAngle()
		sendFrame()
		status = checkProgress(state, operationWaitTime) #replace with diff wait time
		print("Motion successful") if status else print("motion failed")#enter failsafe here
		
	def onButtonPressHome(self, button):
		global state
		global rotorAngle
		print("Home button pressed")
		state = 5
		rotorAngle = rotorHome
		updateDFAngle()
		sendFrame()
		status = checkProgress(state, operationWaitTime) #replace with diff wait time
		print("Homing successful") if status else print("Homing failed")#enter failsafe here
		
	
	def onButtonPressCalibrate(self, button):
		global state
		print("Calibrate button pressed")
		state = 3
		sendFrame()
		status = checkProgress(state, operationWaitTime) #replace with diff wait time
		print("Calibration successful") if status else print("Calibration failed")#enter failsafe here
		
	def onButtonPressCalibrateClamped(self, button):
		global state
		print("Calibrate button pressed")
		state = 3
		sendFrame()
		status = checkProgress(state, operationWaitTime) #replace with diff wait time
		print("Calibration successful") if status else print("Calibration failed")#enter failsafe here
		
	def onButtonPressFailSafe(self, button):
		global state
		print("Failsafe button pressed")
		state = -1
		sendFrame()
		status = checkProgress(state, operationWaitTime) #replace with diff wait time
		print("Calibration successful") if status else print("Calibration failed")#enter failsafe here
		#add code to make device wait for feedback
		notebook.set_current_page(1)   #change to failsafe page
		
def main():
	global state
	#set machine state to off
	print("Turning machine off")
	state=0
	sendFrame()
	status = checkProgress(0,operationWaitTime)
	print("Machine turned OFF") if status else print("Operation failed")
	#connect the callbacks from glade file widgets
	builder.connect_signals(Handler())
	#set starting page to offPage
	notebook.set_current_page(1)
	#make UI window fullscreen
	window.fullscreen()
	#window.set_size_request (800,480)
	#display the UI
	window.show()
	#statusBoxOff.set_text("Machine is OFF.\nClamp and Rotor DISENGAGED")
	#timeBoxOff=
	#initiate the gtk main loop
	Gtk.main()

#some handy functions

def checkReceive(t = receiveWaitTime):
	msg=bus.recv(t)
	if msg != None:
		if (list(msg.data)[1]==1): #can just look for any message from esp. that proves its acknowledged
			return True
	return False

def restartCAN():
	global bus
	print("turning off can")
	call(["sudo", "ip", "link", "set", "can0", "down"])
	time.sleep(2)
	print("turning on can")
	call(["sudo", "ip", "link", "set", "can0", "up", "type", "can", "bitrate", "125000"])
	time.sleep(1)
	print("configuring can")
	call(["sudo", "ifconfig", "can0", "txqueuelen", "10000"])
	time.sleep(2)
	bus = can.interface.Bus(channel=channel, bustype=bustype,bitrate=125000)
	return

def sendFrame():
	global dataFrame
	global state
	dataFrame[statePos] = state
	msg = can.Message(arbitration_id=clamp_ID, data=dataFrame, is_extended_id=False)
	bus.send(msg)	
	if checkReceive():
		print("send successfully")
		return
	else:   #here, implement failsafe detection
		print("Transmission failed.\nPlease check connections for CAN.\nPress ctr+c to exit\nRestarting CAN..")
		restartCAN()
		print("Retrying transmission")
		sendFrame()
		
def checkProgress(operation, waitTime = operationWaitTime):
	msg = bus.recv(waitTime)
	if (msg!=None): 
		#use match case here
		#
		if (list(msg.data)[2] == operation + 10):    #success code of each operation/state is (10 + state)
			return 1
		elif (list(msg.data)[2]<10):
			return 0
	else:
		print ("timer expired")#go to failsafe
		return 0

def updateTextBoxes():
	global engaged
	timeBoxOn.set_text(time.strftime('%H:%M:%S'))
	timeBoxOff.set_text(time.strftime('%H:%M:%S'))
	statusBoxOn.set_text("Machine is in state "+str(state)+"\nClamp in state "+str(engaged)+"\nRotor at angle"+str(rotorAngle))
	statusBoxOff.set_text("Machine is in state "+str(state)+"\nClamp in state "+str(engaged)+"\nRotor at angle"+str(rotorAngle))
	infoBoxClamped.set_text("Machine is in state "+str(state)+"\nClamp in state "+str(engaged)+"\nRotor at angle"+str(rotorAngle))
	return True
	


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

def off():
	global dataFrame
	global state
	state=0
	#print("Dis-engaging the clamp..")
	#dataFrame[statePos] = 2
	#sendFrame()
	print("Switching off..")
	dataFrame[statePos] = state
	sendFrame()
	
def updateDFAngle():
	global dataFrame
	a=rotorAngle
	b=int(a/2)
	a-=b
	dataFrame[angleAPos] = a
	dataFrame[angleBPos] = b

def updateState():
	global pedalPressTime
	global rotorAngle
	global state
	global engaged
	global dataFrame
	if  pedalPressTime>1.5:
		if engaged==0:
			print("execute clamping")
			engaged=1
			state=4
			sendFrame()
		else:
			print("execute un-clamping")
			engaged=0
			state=2
			sendFrame()
	else:
		if engaged:
			rotorAngle= (0 if rotorAngle==360 else rotorAngle+90)
			print("Setting rotary axis to ",rotorAngle," degree(s)")
			state=5
			updateDFAngle()
			sendFrame()

		else:
			print("currently unclamped!")

if __name__ == "__main__":
	try:
		GLib.timeout_add(200, updateTextBoxes)     #adds function to gtk main loop
		main()
	except KeyboardInterrupt:
		print("Execute GPIO-cleanup")
		GPIO.cleanup()
	finally:
		print("Execute GPIO-cleanup")
		GPIO.cleanup()
