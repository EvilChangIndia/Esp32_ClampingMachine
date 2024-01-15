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
from tabnanny import check
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
gladeFile = "UI_v4.glade"      # Variable gladeFile holding the XML file path 
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

#CAN ID of clamp esp
clamp_ID = 0x7D0      #address of clamp ESP set to 2000

#global variables
pedalPressTime=0.0
debounceTime = 0.5
clampTime = 1   #predal press time for triggering pneumatic clamping in seconds

rotorDirection = 1
pedalRotateDelta = 90
retryCounter = 0	#to keep track of CAN bus retries



#define a class for handling on UI inputs
class UIHandler:
	#onDestroy triggers. can use just one onDestroy 
	def onDestroy(self, *args):
		print("Destroy triggered")
		Gtk.main_quit()
		
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
		print("on button pressed")
		#turn to machine-on page
		if clamp1.turnOn():
			print("Machine ON")
		#check success?
		#switch to un-clamped state page
		notebook.set_current_page(page[clamp1.state])
	
	def onButtonPressOff(self, button):
		print("Off button pressed")
		if clamp1.turnOff():
			print("Machine OFF")
		notebook.set_current_page(page[clamp1.state])
		#write else part
		

	def onButtonPressClamp(self, button):
		print("clamp button pressed")
		if not clamp1.clampEngage(True):
			#failsafe
			print("Clamping failed")
		notebook.set_current_page(page[clamp1.state])
	
	def onButtonPressUnclamp(self, button):
		print("un-clamp button pressed")
		if (clamp1.rotorAngle % 360== clamp1.rotorHome):
			if not clamp1.clampEngage(False):
				#failsafe
				print("Un-Clamping failed")
		else:
			print("Home the rotor, before unclamping!")
			infoBoxClamped.set_text("\nClamp engaged"+"\nRotor at angle"+str(clamp1.rotorAngle)+"\n\nHome the rotor, before unclamping!")
		notebook.set_current_page(page[clamp1.state])

	def onButtonPressCW(self, button):
		print("Roate CW button pressed")
		clamp1.clampRotate(pedalRotateDelta)
		
	def onButtonPressACW(self, button):
		print("Rotate ACW button pressed")
		clamp1.clampRotate(-pedalRotateDelta)
		
	def onButtonPressHome(self, button):
		print("Home button pressed")
		if clamp1.homeRotor():
			print("Homed rotor successfully!")
		else: 
			print("Homing failed")
			#failsafe condition here?

	def onButtonPressCalibrate(self, button):
		print("Calibrate button pressed")
		if clamp1.calibrateRotor():
			print("Calibration successful")
			infoBoxClamped.set_text("\nClamp engaged"+"\nRotor at angle"+str(clamp1.rotorAngle)+"\n\nCalibration Successful")
		else:
			print("Calibration failed")
			#add failsafe?

	def onButtonPressCalibrateClamped(self, button):
		print("Calibrate button pressed")
		if clamp1.calibrateRotor():
			print("Calibration successful")
			infoBoxClamped.set_text("\nClamp engaged"+"\nRotor at angle"+str(clamp1.rotorAngle)+"\n\nCalibration Successful")
		else:
			print("Calibration failed")
			#add failsafe?
		
	def onButtonPressFailSafe(self, button):
		print("Failsafe button pressed")
		clamp1.failSafe()
		notebook.set_current_page(page[clamp1.state])
	
	def onButtonPressContinue(self, button):
		print("Continue button pressed")
		#print("Returning to previous state") if status else print("Failsafe exit failed")#enter failsafe here
		if clamp1.exitFailsafe():
			print("Returned to previous state")
			infoBoxClamped.set_text("\nClamp engaged"+"\nRotor at angle"+str(clamp1.rotorAngle))
		notebook.set_current_page(page[clamp1.state])
	
class clamp:
	#CAN dataframe definition
	#dataFrame = [State,status,progress,_,angleA,angleB]
	statePos = 0
	stateAckPos = 1
	progressPos = 2
	angleAPos = 4
	angleBPos = 5
	canRetryLimit = 5
	progressWaitTime = 20
	receiveWaitTime = 5
	rotorHome = 0   #starting/default position of the rotor
	def __init__(self, id):
		self.clampID=id
		self.state = 0
		self.prevState = 0
		self.rotorAngle=0
		self.engaged = 1
		self.dataFrame = [0 ,0 ,0 ,0 ,0 ,0 ]
		self.retryCounter = 0
		self.bustype = 'socketcan'
		self.channel = 'can0'

	def turnOn(self):
		self.prevState = self.state
		print("on button pressed")
		#turn machine on
		self.state = 1
		self.sendFrame()
		if (not self.checkProgress(self.state, self.progressWaitTime)):        #replace with diff wait time
			self.state=self.prevState
			return 0
		
		print("Machine turned ON") 

		#move rotor to home
		self.homeRotor()

		#switch to un-clamped state
		print("Unclamping")
		self.clampEngage(False)
		return 1

	def turnOff(self):
		self.prevState=self.state
		print("Off button pressed")
		self.state = 0
		#notebook.set_current_page(4)#loading page
		self.sendFrame()
		return self.checkProgress(self.state, self.progressWaitTime) #replace with diff wait time

	def startCAN(self):
		print("\nTurning ON CAN bus")
		call(["sudo", "ip", "link", "set", "can0", "up", "type", "can", "bitrate", "125000"])
		time.sleep(1)
		print("configuring can")
		call(["sudo", "ifconfig", "can0", "txqueuelen", "10000"])
		time.sleep(2)
		self.bus = can.interface.Bus(channel=self.channel, bustype=self.bustype,bitrate=125000)
		print("CAN bus started!\n")
		return

	def stopCAN(self):
		print("\nTurning OFF CAN bus..")
		call(["sudo", "ip", "link", "set", "can0", "down"])
		time.sleep(2)
		print("CAN bus turned OFF")
		return
	
	def restartCAN(self):
		self.stopCAN()
		self.startCAN()
		return
	
	def checkReceive(self, sendState, t = receiveWaitTime):
		msg=self.bus.recv(t)
		if msg != None:
			recLen=len(list(msg.data))
			if recLen >=3:
				print("Received:", list(msg.data)[self.stateAckPos])
				if (list(msg.data)[self.stateAckPos]==sendState): #can just look for any message from esp. that proves its acknowledged
					return True
			else:
				print("wrong length reply")
				return self.checkReceive(sendState, t)
		return False	
	
	def checkProgress(self, operation, waitTime = progressWaitTime):
		print("checking progress")
		msg = self.bus.recv(waitTime)
		if (msg!=None): 
			#use match case here
			statusLength = len(list(msg.data))
			print("received progress report of length", str(statusLength))
			if  statusLength < 3:
				print("received wrong acknowledgement: "+ str(status) )
				print("Sending again..")
				self.sendFrame()
				return self.checkProgress(operation)
			status=list(msg.data)[self.progressPos]
			print("received reply: ", status)
			if (status == operation + 10):    #success code of each operation/state is (10 + state)
				print("Operation successful!")
				return 1
			elif (status == 110):
				print("Clamp entered Failsafe")#enter failsafe here
				return 0
			else:
				print("Received wrong acknowledgement: "+ str(status) )
				print("Sending again..")
				self.sendFrame()
				return self.checkProgress(operation)

		else: #add retry counter here and mtrigger failsafe
			print ("timer expired. No progress reported by Clamp.")	#go to failsafe
			print("Sending again..")
			self.sendFrame()
			return self.checkProgress(operation)

	def sendFrame(self):
		a=self.rotorAngle
		b=int(a/2)
		a-=b
		self.dataFrame[self.angleAPos] = a
		self.dataFrame[self.angleBPos] = b
		self.dataFrame[self.statePos] = self.state
		print("Trying to send: state: "+str(self.state) + " Angle:" + str(self.rotorAngle))
		msg = can.Message(arbitration_id = self.clampID, data = self.dataFrame, is_extended_id = False)
		self.bus.send(msg)	
		if self.checkReceive(self.state):
			print("Message received by clamp!")
			self.retryCounter = 0
			return 1
		elif self.retryCounter <= self.canRetryLimit:   #here, implement failsafe detection
			print("Transmission failed.\nRestarting CAN..")
			self.restartCAN()
			print("Retrying transmission")
			retryCounter = retryCounter + 1 
			return self.sendFrame()
		else:
			print("CANbus Retry counter limit exceeded!\n Clamp not reporting progress.")
			#print("Entering Failsafe mode")
			#self.failSafe()
			return 0
	
	def calibrateRotor(self):
		self.prevState = self.state
		print("Calibrate button pressed")
		self.state = 3
		self.sendFrame()
		status = self.checkProgress(self.state, self.progressWaitTime) #replace with diff wait time
		#print("Calibration successful") if status else print("Calibration failed")#enter failsafe here
		self.state = self.prevState
		return status
	
	def homeRotor(self):
		self.prevState = self.state
		self.state = 5
		#notebook.set_current_page(page[state])
		self.rotorAngle = self.rotorHome if self.rotorAngle <=180 else 360
		self.sendFrame()
		status = self.checkProgress(self.state, self.progressWaitTime) #replace with diff wait time
		#print("Homing successful") if status else print("Homing failed")#enter failsafe here
		if status:
			self.rotorAngle=0
			self.sendFrame()
			status = self.checkProgress(self.state, self.progressWaitTime) #replace with diff wait time
		self.state = self.prevState
		return status
		#notebook.set_current_page(page[state])

	def clampRotate(self, delta):
		self.prevState = self.state
		self.state = 5
		#notebook.set_current_page(page[state])
		self.rotorAngle= (self.rotorAngle + delta)
		if self.rotorAngle>360:
			self.rotorAngle= delta 
			print("trimmed down to delta")
		elif self.rotorAngle<0:
			self.rotorAngle= 360 + delta
			print("ramped to 360+delta")
		print("Setting rotor to angle: " + str(self.rotorAngle))
		self.sendFrame()
		status = self.checkProgress(self.state, self.progressWaitTime) #replace with diff wait time
		self.state = self.prevState
		if status:
			print("Motion successful")
			#infoBoxClamped.set_text("\nClamp engaged"+"\nRotor at angle"+str(rotorAngle))
		#notebook.set_current_page(page[state])

	def clampEngage(self, yes):
		self.prevState=self.state
		self.state = 4 if yes else 2
		#notebook.set_current_page(4)#loading page
		status = self.sendFrame()
		if status:
			print("Machine clamped") if yes else print("Machine Un-clamped")
			#infoBoxClamped.set_text("\nClamp engaged\nRotor at angle"+str(rotorAngle))
			#notebook.set_current_page(page[state])
			self.engaged = 1 if yes else 0
			return 1
		self.state = self.prevState
		return 0
		#notebook.set_current_page(page[state])

	def failSafe(self):
		self.prevState=self.state
		self.state = 100
		self.sendFrame()
		status = self.checkProgress(state, self.progressWaitTime) #replace with diff wait time
		print("Entered failsafe") if status else print("Failsafe entry failed")#enter failsafe here
		#failsafeBox.set_text("FAILSAFE MODE ENTERED!!\n\nMachine is in state "+str(state)+"\nClamp and Rotor are disabled"+"\n\nFix the issue and press \"Continue\"")
		#notebook.set_current_page(page[state])   #change to failsafe page
		return

	def exitFailsafe(self):
		print("Exiting Failsafe mode..")
		self.state = self.prevState
		self.sendFrame()
		status = self.checkProgress(self.state, self.progressWaitTime) #replace with diff wait time
		if status:
			return 1
		else:
			self.state = 100
			return 0
		
clamp1=clamp(clamp_ID)	

def button_callback(args):    #function run on pedal press
	global pedalPressTime
	count=0
	print(f"Pedal pressed!")
	while (GPIO.input(pedalPin)==1) and (count<(clampTime*100)):
		count+=1
		time.sleep(0.01)
	pedalPressTime = count*0.01
	print("for ", pedalPressTime, " seconds")
	time.sleep(debounceTime)
	#pedalUpdateState()

def pedalUpdateState():
	
	global pedalPressTime
	global rotorDirection
	#if  (pedalPressTime == clampTime)  and (rotorAngle == rotorHome):
	if  (pedalPressTime == clampTime):
		print("pedal triggered")
		if clamp1.state==2:
			print("Clamping..")
			clamp1.clampEngage(True)
		elif clamp1.state==4:
			print("Homing before unclamping..")
			clamp1.homeRotor()
			print("Un-clamping..")
			clamp1.clampEngage(False)
		pedalPressTime=0
		
	elif pedalPressTime>0:
		print("pedal triggered")
		if clamp1.state==4:
			if clamp1.rotorAngle == 0 or clamp1.rotorAngle == 360:
				rotorDirection = rotorDirection * -1
				print("Limit reached. Switching Direction..")
			print("Rotating clamp")
			clamp1.clampRotate(pedalRotateDelta * rotorDirection)
		else:
			print("currently unclamped!")
		pedalPressTime=0
	return True

def updateTextBoxes():
	timeBoxOn.set_text(time.strftime('%H:%M:%S'))
	timeBoxOff.set_text(time.strftime('%H:%M:%S'))
	statusBoxOn.set_text("Machine is in state "+stateName[clamp1.state]+"\nRotor at angle"+str(clamp1.rotorAngle))
	statusBoxOff.set_text("Machine is in state "+stateName[clamp1.state]+"\nRotor at angle"+str(clamp1.rotorAngle))
	#infoBoxClamped.set_text("Machine is in state "+str(state)+"\nClamp in state "+str(engaged)+"\nRotor at angle"+str(rotorAngle))
	loadingBox.set_text(activity[clamp1.state]+"\n\nPlease wait..")
	return True
	
def main():
	
	clamp1.restartCAN()
	#set machine state to off
	print("Turning machine off")
	status = clamp1.turnOff()
	print("Machine switched to OFF state") if status else print("Operation failed")
	#connect the callbacks from glade file widgets
	builder.connect_signals(UIHandler())
	#set starting page to offPage
	notebook.set_current_page(clamp1.state)
	#make UI window fullscreen
	window.fullscreen()
	#display the UI
	window.show()
	#start the button handler thread for pedal press
	pedal = ButtonHandler(pedalPin, GPIO.RISING, button_callback,0.1)
	#initiate the gtk main loop
	Gtk.main()

if __name__ == "__main__":
	try:
		GLib.timeout_add(200, updateTextBoxes)     #adds function to gtk main loop
		GLib.timeout_add(200, pedalUpdateState)
		main()
	except KeyboardInterrupt:
		print("Execute GPIO-cleanup")
		GPIO.cleanup()
	finally:
		print("Execute GPIO-cleanup")
		GPIO.cleanup()
