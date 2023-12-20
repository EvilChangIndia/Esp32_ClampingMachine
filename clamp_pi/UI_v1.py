import gi 
import time
gi.require_version('Gtk', '3.0')            # Load the correct namespace and version of GTK
from gi.repository import Gtk               # Include the python bindings for GTK

gladeFile = "UI_v1.glade"      # Variable gladeFile holding the XML file path 
builder = Gtk.Builder()            # GTK Builder called 
builder.add_from_file(gladeFile)   # GTK Builder passed the XML file path for translation

offWindow = builder.get_object("offWindow")
exitWindow = builder.get_object("exitWindow")
onWindow = builder.get_object("onWindow")
clampWindow = builder.get_object("clampWindow")
offWindow.fullscreen()
exitWindow.fullscreen()
onWindow.fullscreen()
clampWindow.fullscreen()

class Handler:
	#onDestroy triggers. can use just one onDestroy also, by removing callback from glade
	#def onDestroy(self, *args):
		#Gtk.main_quit()
		#print("Destroy triggered")
	
	def onDestroyOff(self, *args):
		print("Destroy OFF triggered")
		Gtk.main_quit()
	
	def onDestroyOn(self, *args):
		print("Destroy ON triggered")
		Gtk.main_quit()
		
	
	def onDestroyClamp(self, *args):
		print("Destroy Clamp triggered")
		Gtk.main_quit()
		
	
	def onDestroyExit(self, *args):
		print("Destroy Exit triggered")
		Gtk.main_quit()
		
	
	#button triggers
	def onButtonPressExit(self, button):
		print("Exit button pressed")
		offWindow.hide()
		exitWindow.show()
		#Gtk.main_quit()
		
		
	def onButtonPressPower(self, button):
		print("Power button pressed")
		Gtk.main_quit()
	
	def onButtonPressRestart(self, button):
		print("Restart button pressed")
		Gtk.main_quit()
	
	def onButtonPressBack(self, button):
		print("Back button pressed")
		exitWindow.hide()
		#window = builder.get_object("offWindow")
		print("got object")
		offWindow.show()
	
	def onButtonPressON(self, button):
		print("on button pressed")
		offWindow.hide()
		
		onWindow.show()
	
	def onButtonPressOff(self, button):
		print("off button pressed")
		onWindow.hide()
		#window = builder.get_object("offWindow")
		offWindow.show()
	
	def onButtonPressClamp(self, button):
		print("clamp button pressed")
		onWindow.hide()
		clampWindow.show()
	
	def onButtonPressUnclamp(self, button):
		print("un-clamp button pressed")
		clampWindow.hide()
		onWindow.show()

def main():                     	# Class constructor calling itself
	
	builder.connect_signals(Handler())
	offWindow.show()
	
	Gtk.main()
	

if __name__ == "__main__":
	try:
		main()
	except KeyboardInterrupt:
		print("Execute GPIO-cleanup")
		GPIO.cleanup()
	finally:
		print("Execute GPIO-cleanup")
		GPIO.cleanup()
