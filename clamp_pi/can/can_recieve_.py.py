import time
import can

bustype = 'socketcan'
channel = 'can0'
bus = can.interface.Bus(channel=channel, bustype=bustype,bitrate=125000)

#msg = can.Message(arbitration_id=0xc0ffee, data=[0, 1, 3, 1, 4, 1], is_extended_id=False)
try:
	while True:
		#a=int(input("enter state: "))
		msg=bus.recv()
		print(msg.data)
		print(list(msg.data)[0])
		#time.sleep(1)
except KeyboardInterrupt:
	print("\nAsta la' vista bitches! ")

