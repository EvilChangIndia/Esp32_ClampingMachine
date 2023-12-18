#The machine states are as follows
#state -1: FailSafe
#state 0: OFF
#state 1: ON
#state 2: Un Clamped
#state 3: Calibration
#state 4: Clamped
#state 5: Angle Update
#state 6: Stepper Run
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

rotorHome = 270   #angular offset from encoder to home position

#define a class for handling on UI inputs
class Handler:
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
	
	def onButtonPressRestart(self, button):
		print("Restart button pressed")
		Gtk.main_quit()
	
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
		time.sleep(0.25) #ping slaves here
		print("Machine on. Homing..")
		#move rotor to home
		state = 5
		rotorAngle = rotorHome
		updateDFAngle()
		sendFrame()
		checkClampReply() #waits for acknowledge
		#switch to un-clamped state
		state = 2
		sendFrame()
		time.sleep(clampTime) #change to checkReply()
		#switch ui page
		notebook.set_current_page(2)
	
	def onButtonPressOff(self, button):
		global state
		print("off button pressed")
		state = 0
		sendFrame()
		notebook.set_current_page(1)
		
	def onButtonPressClamp(self, button):
		global state
		global engaged
		print("clamp button pressed")
		#statusBoxClamped.set_text("Machine is ON.\nClamp ENGAGED")
		state = 4
		sendFrame()
		time.sleep(clampTime)
		engaged = 1
		notebook.set_current_page(3)
	
	def onButtonPressUnclamp(self, button):
		global state
		print("un-clamp button pressed")
		if (rotorAngle==rotorHome):
			state = 2
			sendFrame()
			time.sleep(clampTime)
			notebook.set_current_page(2)
			engaged=0
		else:
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
		checkClampReply()
	
	def onButtonPressACW(self, button):
		global state
		global rotorAngle
		print("-90 button pressed")
		state = 5
		rotorAngle= (360 if rotorAngle==0 else rotorAngle-90)
		updateDFAngle()
		sendFrame()
		checkClampReply()
		
	def onButtonPressHome(self, button):
		global state
		global rotorAngle
		print("Home button pressed")
		state = 5
		rotorAngle = rotorHome
		updateDFAngle()
		sendFrame()
		checkClampReply()
	
	def onButtonPressCalibrate(self, button):
		global state
		print("Calibrate button pressed")
		state = 3
		sendFrame()
		#add code to make device wait for feedback
		
	def onButtonPressCalibrateClamped(self, button):
		global state
		print("Calibrate button pressed")
		state = 3
		sendFrame()
		#add code to make device wait for feedback
		
	def onButtonPressFailSafe(self, button):
		global state
		print("Failsafe button pressed")
		state = -1
		sendFrame()
		#add code to make device wait for feedback
		
		notebook.set_current_page(1)   #change to failsafe page
		
def main():
	#set machine state to off
	state=0
	sendFrame()
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
def checkClampReply():
	while True:
		msg=bus.recv()
		if (list(msg.data)[0]==11):
			print("motion completed")
			break
		elif (list(msg.data)[0]==0):
			print("calibration failed.\nCheck endstop and motor functionality")
			#move to failsafe screen here or return something
		time.sleep(0.5)
	return
	
def updateTime():
	timeBoxOn.set_text(time.strftime('%H:%M:%S'))
	timeBoxOff.set_text(time.strftime('%H:%M:%S'))
	statusBoxOn.set_text("Machine is in state "+str(state)+"\nClamp in state "+str(engaged)+"\nRotor at angle"+str(rotorAngle))
	statusBoxOff.set_text("Machine is in state "+str(state)+"\nClamp in state "+str(engaged)+"\nRotor at angle"+str(rotorAngle))
	infoBoxClamped.set_text("Machine is in state "+str(state)+"\nClamp in state "+str(engaged)+"\nRotor at angle"+str(rotorAngle))
	
	
	return True
	
def sendFrame():
	global dataFrame
	global state
	dataFrame[statePos] = state
	msg = can.Message(arbitration_id=clamp_ID, data=dataFrame, is_extended_id=False)
	bus.send(msg)

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
		GLib.timeout_add(200, updateTime)     #adds function to gtk main loop
		main()
	except KeyboardInterrupt:
		print("Execute GPIO-cleanup")
		GPIO.cleanup()
	finally:
		print("Execute GPIO-cleanup")
		GPIO.cleanup()
