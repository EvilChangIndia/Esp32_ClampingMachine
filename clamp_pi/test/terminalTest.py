

from subprocess import call
call(["sudo" "ip" "link" "set" "can0" "down"])
time.sleep(0.5)
call(["sudo", "ip", "link", "set", "can0", "up", "type", "can", "bitrate", "125000"])
time.sleep(1)
call(["sudo", "ifconfig", "can0", "txqueuelen", "10000"])
time.sleep(0.5)