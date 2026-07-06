from unitree_sdk2py.core.channel import (
    ChannelSubscriber,
    ChannelFactoryInitialize,
)

from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandState_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__HandState_

hand_id = input("Input hand (L/R): ").strip().upper()
iface = input("Network interface: ").strip()

if hand_id == "L":
    topic = "rt/lf/dex3/left/state"
else:
    topic = "rt/lf/dex3/right/state"

ChannelFactoryInitialize(0, iface)

state = unitree_hg_msg_dds__HandState_()

def cb(msg):
    global state
    state = msg

sub = ChannelSubscriber(topic, HandState_)
sub.Init(cb, 1)

input("\nPresiona ENTER cuando la mano esté enviando datos...\n")

sensor = state.press_sensor_state[0]

print("\nATRIBUTOS DISPONIBLES EN PressSensorState_:\n")
print(dir(sensor))
