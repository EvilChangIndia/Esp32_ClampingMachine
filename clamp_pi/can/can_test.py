import time
import can

bustype = 'socketcan'
channel = 'can0'
bus = can.interface.Bus(channel=channel, bustype=bustype,bitrate=125000)

#msg = can.Message(arbitration_id=0xc0ffee, data=[0, 1, 3, 1, 4, 1], is_extended_id=False)
try:
	while True:
		a=int(input("enter state: "))
		msg = can.Message(arbitration_id=0x7D0, data=[a, 1, 3, 1, 0, 0], is_extended_id=False)
		bus.send(msg)
		#time.sleep(1)
except KeyboardInterrupt:
	print("\nAsta la' vista bitches! ")

