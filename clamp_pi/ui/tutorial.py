import gi 
import time
gi.require_version('Gtk', '3.0')            # Load the correct namespace and version of GTK
from gi.repository import Gtk               # Include the python bindings for GTK

class Main():                     			        ## Main class ##								
		def __init__(self):                     	# Class constructor calling itself
			gladeFile = "UI_v1.glade"      # Variable gladeFile holding the XML file path 
			self.builder = Gtk.Builder()            # GTK Builder called 
			self.builder.add_from_file(gladeFile)   # GTK Builder passed the XML file path for translation
		
			# This line does the magic of connecting the signals created in the Glade3
			# builder to our defines above. You must have one def for each signal if
			# you use this line to connect the signals.
			self.builder.connect_signals(self)      
		
			# Upload Button widget
			onButton = self.builder.get_object("onButton")  # Get button object from XML file
			#button.connect("clicked", self.printText);       # Connect clicked event/signal with button
			onButton.connect("button-release-event",self.onState);

			# TextBuffer(Not created in glade)
			# Empty text buffer is created
			# With set_text buffer is initialized with text
			Tview 	= self.builder.get_object("statusBox0");   # Text view fetched from glade CSS file
			self.buff = Tview.get_buffer();  				  # Get TextBox object from XML file   
			self.buff.set_text("Device is OFF");
			
			# Main window from glade
			window = self.builder.get_object("offWindow") # Get window object - Window is a widget 
			window.show()                                  # show window 
			window.connect("destroy", Gtk.main_quit)     # This line ensures that the window is closed
														   # when we click on the Close button in the title bar
														   # Destroy event/signal is connected to window widget
														   # Gtk.main_quit is closing the main loop - Same as End or getche()
			#while True:
				#time.sleep(1)
		def onState(self, widget, NULL):	
			#attribute = self.buff.get_text(self.buff.get_start_iter(), self.buff.get_end_iter(), include_hidden_chars=False)
			self.buff.set_text("On Button Pressed");
					


if __name__ == "__main__":
	  main = Main()                                        # Window is created  
	  Gtk.main()                                           # Main loop Like void main() - Waiting for event
