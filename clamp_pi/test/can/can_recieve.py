import time
import can

bustype = 'socketcan'
channel = 'can0'
bus = can.interface.Bus(channel=channel, bustype=bustype,bitrate=125000)

#msg = can.Message(arbitration_id=0xc0ffee, data=[0, 1, 3, 1, 4, 1], is_extended_id=False)
try:
	#while True:
		a=0
		b=0
		state=int(input("enter state:"))
		if state==5:
			a=int(input("enter angle: "))
			b=int(a/2)
			a-=b
		msg = can.Message(arbitration_id=0x7D0, data=[state, 1, 3, 1, a, b], is_extended_id=False)
		try:
			bus.send(msg,timeout=5)
		except can.CanError:
			print("message not send")
		#time.sleep(1)
except KeyboardInterrupt:
	print("\nAsta la' vista bitches! ")

