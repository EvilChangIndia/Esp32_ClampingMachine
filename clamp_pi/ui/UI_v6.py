#The machine states are as follows
#state 100: FailSafe
#state 0: OFF
#state 1: ON
#state 2: Un Clamped
#state 3: Calibration
#state 4: Clamped
#state 5: Angle Update
#state 6: Stepper Run

from subprocess import call
from xml.sax.handler import property_declaration_handler
import RPi.GPIO as GPIO 
import threading
import time
import can
from debounce import ButtonHandler
import gi 
gi.require_version('Gtk', '3.0')            # Load the correct namespace and version of GTK
from gi.repository import Gtk               # Include the python bindings for GTK
from gi.repository import GLib              # included for adding things to gtk main loop


#GPIO pinout
pedalPin = 16

GPIO.setmode(GPIO.BCM)
GPIO.setup(pedalPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

#import UI glade file into a GTK.Builder object
gladeFile = "UI_v3.glade"      # Variable gladeFile holding the XML file path 
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
failsafeBox = builder.get_object("failsafeBox").get_buffer()
loadingBox = builder.get_object("loadingBox").get_buffer()

#define pages {state:corresponding page number}
page={100:5, 0:1, 1:4, 2:2, 3:4, 4:3, 5:4 }
#actions
activity={100:"Entering Failsafe", 0:"Turning the machine OFF...", 1:"Turning the machine ON...", 2:"Un-Clamping...", 3:"Calibrating the rotor", 4:"Clamping...", 5:"Rotor in motion..."}
#state names 
stateName={0:"OFF", 1:"ON", 2:"Un-Clamped", 3:"Calibrating", 4:"Clamped", 5:"Angle Update", 6:"Stepper Run", 100:"FailSafe"}


#CAN bus configuration
bustype = 'socketcan'
channel = 'can0'
bus = can.interface.Bus(channel=channel, bustype=bustype,bitrate=125000)
clamp_ID = 0x7D0      #address of clamp ESP set to 2000
canRetryLimit = 5

#CAN dataframe definition
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
pedalRotateDelta = -45
engaged = 0
clampTime = 1   #predal press time for triggering pneumatic clamping in seconds
operationWaitTime = 30 #half seconds
receiveWaitTime = 5
rotorHome = 270   #angular offset from encoder to home position
retryCounter = 0	#to keep track of CAN bus retries



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
		notebook.set_current_page(page[0])
		
	def onButtonPressOn(self, button):
		global state
		global rotorAngle
		global prevState
		prevState=state
		print("on button pressed")
		#turn machine on
		state = 1
		notebook.set_current_page(page[state]) 
		sendFrame()
		status = checkProgress(state, operationWaitTime) #replace with diff wait time
		if status:
			print("Machine turned ON") 
		else:
			return
		
		#move rotor to home
		print("Homing..")
		state = 5
		#notebook.set_current_page(page[state])
		rotorAngle = rotorHome
		updateDFAngle()
		sendFrame()
		status = checkProgress(state, operationWaitTime) #replace with diff wait time
		if status:
			print("Machine home")  
		else:
			return
		
		#switch to un-clamped state
		print("Unclamping")
		state = 2
		#notebook.set_current_page(4)#loading page
		sendFrame()
		status = checkProgress(state, operationWaitTime) #replace with diff wait time
		if status:
			print("Machine Unclamped")  
			notebook.set_current_page(page[state])
	
	def onButtonPressOff(self, button):
		global state
		global prevState
		prevState=state
		print("Off button pressed")
		state = 0
		#notebook.set_current_page(4)#loading page
		sendFrame()
		status = checkProgress(state, operationWaitTime) #replace with diff wait time
		if status:
			print("Machine OFF")
			notebook.set_current_page(page[state])
		

	def onButtonPressClamp(self, button):
		print("clamp button pressed")
		clampEngage(True)
	
	def onButtonPressUnclamp(self, button):
		print("un-clamp button pressed")
		if (rotorAngle==rotorHome):
			clampEngage(False)
		else:
			#fix this byatch
			print("Home the rotor, before unclamping!")
			infoBoxClamped.set_text("\nClamp engaged"+"\nRotor at angle"+str(rotorAngle)+"\n\nHome the rotor, before unclamping!")
			#maybe display on failsafe page

	def onButtonPressCW(self, button):
		print("+90 button pressed")
		clampRotate(90)
		
	def onButtonPressACW(self, button):
		print("+90 button pressed")
		clampRotate(-90)
	
		
	def onButtonPressHome(self, button):
		global state
		global rotorAngle
		global prevState
		prevState = state
		print("Home button pressed")
		state = 5
		notebook.set_current_page(page[state])
		rotorAngle = rotorHome
		updateDFAngle()
		sendFrame()
		status = checkProgress(state, operationWaitTime) #replace with diff wait time
		#print("Homing successful") if status else print("Homing failed")#enter failsafe here
		state = prevState
		if status:
			print("Motion successful")
			infoBoxClamped.set_text("\nClamp engaged"+"\nRotor at angle"+str(rotorAngle))
			notebook.set_current_page(page[state])

	def onButtonPressCalibrate(self, button):
		global state
		global prevState
		prevState=state
		print("Calibrate button pressed")
		state = 3
		sendFrame()
		status = checkProgress(state, operationWaitTime) #replace with diff wait time
		#print("Calibration successful") if status else print("Calibration failed")#enter failsafe here
		state = prevState
		if status:
			print("Calibration successful")
			infoBoxClamped.set_text("\nClamp engaged"+"\nRotor at angle"+str(rotorAngle)+"\n\nCalibration Successful")
			notebook.set_current_page(page[state])

	def onButtonPressCalibrateClamped(self, button):
		global state
		global prevState
		prevState=state
		print("Calibrate button pressed")
		state = 3
		sendFrame()
		status = checkProgress(state, operationWaitTime) #replace with diff wait time
		#print("Calibration successful") if status else print("Calibration failed")#enter failsafe here
		state = prevState
		if status:
			print("Calibration successful")
			infoBoxClamped.set_text("\nClamp engaged"+"\nRotor at angle"+str(rotorAngle)+"\n\nCalibration Successful")
			notebook.set_current_page(page[state])
		
	def onButtonPressFailSafe(self, button):
		failSafe()
	
	def onButtonPressContinue(self, button):
		global state
		print("Exiting Failsafe mode..")
		state=prevState
		sendFrame()
		status = checkProgress(state, operationWaitTime) #replace with diff wait time
		#print("Returning to previous state") if status else print("Failsafe exit failed")#enter failsafe here
		if status:
			print("Returned to previous state")
			infoBoxClamped.set_text("\nClamp engaged"+"\nRotor at angle"+str(rotorAngle))
			notebook.set_current_page(page[state])

clampHandler = Handler()		

def main():
	global state
	restartCAN()
	#set machine state to off
	print("Turning machine off")
	state=0
	sendFrame()
	status = checkProgress(0,operationWaitTime)
	print("Machine turned OFF") if status else print("Operation failed")
	#connect the callbacks from glade file widgets
	builder.connect_signals(clampHandler)
	#set starting page to offPage
	notebook.set_current_page(1)
	#make UI window fullscreen
	window.fullscreen()
	#display the UI
	window.show()
	#start the button handler thread for pedal press
	pedal = ButtonHandler(pedalPin, GPIO.RISING, button_callback,0.1)
	#initiate the gtk main loop
	Gtk.main()

def button_callback(args):    #function run on pedal press
	global pedalPressTime
	count=0
	print(f"button pressed!")
	while (GPIO.input(pedalPin)==1) and (count<(clampTime*100)):
		count+=1
		time.sleep(0.01)
	pedalPressTime = count*0.01
	print("for ", pedalPressTime, " seconds")
	pedalUpdateState()

def pedalUpdateState():
	global pedalPressTime
	global state
	if  (pedalPressTime == clampTime)  and (rotorAngle == rotorHome):
		if state==2:
			print("execute clamping")
			clampEngage(True)
		elif state==4:
			print("execute un-clamping")
			clampEngage(False)
	else:
		if state==4:
			clampRotate(pedalRotateDelta)
		else:
			print("currently unclamped!")

#some handy functions. make into a class?
			
def clampRotate(delta):
	global state
	global rotorAngle
	global prevState
	prevState = state
	state = 5
	notebook.set_current_page(page[state])
	rotorAngle= (360 if rotorAngle==0 else (rotorAngle+delta))
	updateDFAngle()
	sendFrame()
	status = checkProgress(state, operationWaitTime) #replace with diff wait time
	state = prevState
	if status:
		print("Motion successful")
		infoBoxClamped.set_text("\nClamp engaged"+"\nRotor at angle"+str(rotorAngle))
	notebook.set_current_page(page[state])

def failSafe():
	global state
	global prevState
	prevState=state
	state = 100
	sendFrame()
	status = checkProgress(state, operationWaitTime) #replace with diff wait time
	print("Entered failsafe") if status else print("Failsafe entry failed")#enter failsafe here
	failsafeBox.set_text("FAILSAFE MODE ENTERED!!\n\nMachine is in state "+str(state)+"\nClamp and Rotor are disabled"+"\n\nFix the issue and press \"Continue\"")
	notebook.set_current_page(page[state])   #change to failsafe page

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
	global retryCounter
	dataFrame[statePos] = state
	msg = can.Message(arbitration_id=clamp_ID, data=dataFrame, is_extended_id=False)
	bus.send(msg)	
	if checkReceive():
		print("send successfully")
		retryCounter = 0
		return
	elif retryCounter <= canRetryLimit:   #here, implement failsafe detection
		print("Transmission failed.\nRestarting CAN..")
		restartCAN()
		print("Retrying transmission")
		sendFrame()
		retryCounter = retryCounter + 1 
	else:
		print("CANbus Retry counter exceeded!\n Clamp not found.\nPress ctr+c to exit")
		print("Entering Failsafe mode")
		failSafe()
		
def checkProgress(operation, waitTime = operationWaitTime):
	msg = bus.recv(waitTime)
	global state
	if (msg!=None): 
		#use match case here
		#
		print("received reply", list(msg.data)[2])
		if (list(msg.data)[2] == operation + 10):    #success code of each operation/state is (10 + state)
			return 1
		elif (list(msg.data)[2]<10):
			print("Failed" + activity[operation])#enter failsafe here
			state = prevState
			notebook.set_current_page(page[state])
			failSafe()
			return 0
		else:
			print("received wrong acknowledgement: ", list(msg.data)[2] )
			print("waiting for another acknowledgement...")
			checkProgress(operation,waitTime)	#wait for another acknowledge signal
	else:
		print ("timer expired")	#go to failsafe
		state = prevState
		notebook.set_current_page(page[state])
		failSafe()
		return 0

def updateTextBoxes():
	global engaged
	timeBoxOn.set_text(time.strftime('%H:%M:%S'))
	timeBoxOff.set_text(time.strftime('%H:%M:%S'))
	statusBoxOn.set_text("Machine is in state "+stateName[state]+"\nClamp in state "+str(engaged)+"\nRotor at angle"+str(rotorAngle))
	statusBoxOff.set_text("Machine is in state "+stateName[state]+"\nClamp in state "+str(engaged)+"\nRotor at angle"+str(rotorAngle))
	#infoBoxClamped.set_text("Machine is in state "+str(state)+"\nClamp in state "+str(engaged)+"\nRotor at angle"+str(rotorAngle))
	
	loadingBox.set_text(activity[state]+"\n\nPlease wait..")
	return True
	

def clampEngage(yes):
	global state
	global engaged
	global prevState
	prevState=state
	state = 4 if yes else 2
	notebook.set_current_page(4)#loading page
	sendFrame()
	status = checkProgress(state, operationWaitTime) #replace with diff wait time
	#print("Machine clamped") if status else print("clamping failed")#enter failsafe here
	if status:
		print("Machine clamped") if yes else print("Machine Un-clamped")
		infoBoxClamped.set_text("\nClamp engaged\nRotor at angle"+str(rotorAngle))
		notebook.set_current_page(page[state])
		engaged = 1 if yes else 0
		return
	state = prevState
	notebook.set_current_page(page[state])

def updateDFAngle():
	global dataFrame
	a=rotorAngle
	b=int(a/2)
	a-=b
	dataFrame[angleAPos] = a
	dataFrame[angleBPos] = b

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
