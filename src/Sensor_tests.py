import time
import numpy as np
from unitree_sdk2py.core.channel import (
    ChannelSubscriber,
    ChannelFactoryInitialize,
)
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandState_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__HandState_

INVALID_VALUE = 30000
SCALE = 10000.0

hand_id = input("Input hand (L/R): ").strip().upper()
iface = input("Network interface: ").strip()

topic = (
    "rt/lf/dex3/left/state"
    if hand_id == "L"
    else "rt/lf/dex3/right/state"
)

ChannelFactoryInitialize(0, iface)

state = unitree_hg_msg_dds__HandState_()

def cb(msg):
    global state
    state = msg

sub = ChannelSubscriber(topic, HandState_)
sub.Init(cb, 1)

print("\nLeyendo sensores EN TIEMPO REAL (Ctrl+C para salir)\n")

while True:
    time.sleep(0.05)

    if len(state.press_sensor_state) == 0:
        continue

    print("\033[2J\033[H")  # limpia pantalla

    for finger_idx, sensor in enumerate(state.press_sensor_state):
        raw = list(sensor.pressure)
        scaled = [
            0.0 if v == INVALID_VALUE else v / SCALE
            for v in raw
        ]
        print(
            f"ID {finger_idx} | "
            f"Max pressure: {round(max(scaled), 2)}"
        )

