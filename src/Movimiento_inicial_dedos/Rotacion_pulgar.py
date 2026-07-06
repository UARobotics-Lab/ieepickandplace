# ==============================================================
# ROTACION PULGAR
# ==============================================================

import time
import numpy as np

from unitree_sdk2py.core.channel import (
    ChannelPublisher,
    ChannelFactoryInitialize,
)

from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandCmd_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__HandCmd_

# =============================
# CONFIG
# =============================

MOTOR_MAX = 7

maxLimits_left  = [ 1.05,  1.05,  1.75,  0.0,   0.0,   0.0,   0.0 ]
minLimits_left  = [-1.05, -0.724,  0.0, -1.57, -1.75, -1.57, -1.75]

# posición abierta aproximada para dedos
open_ratio = 0.5

# =============================
# DDS
# =============================

iface = input("Network interface: ")

ChannelFactoryInitialize(0, iface)

publisher = ChannelPublisher("rt/dex3/left/cmd", HandCmd_)
publisher.Init()

cmd_msg = unitree_hg_msg_dds__HandCmd_()

# =============================
# UTILIDADES
# =============================

def build_mode(motor_id,status=1,timeout=0):

    mode = 0
    mode |= (motor_id & 0x0F)
    mode |= (status & 0x07) << 4
    mode |= (timeout & 0x01) << 7
    return mode


def send_positions(q):

    for i in range(MOTOR_MAX):

        cmd_msg.motor_cmd[i].mode = build_mode(i,1,0)
        cmd_msg.motor_cmd[i].tau = 0
        cmd_msg.motor_cmd[i].dq = 0
        cmd_msg.motor_cmd[i].kp = 1.5
        cmd_msg.motor_cmd[i].kd = 0.1
        cmd_msg.motor_cmd[i].q = q[i]

    publisher.Write(cmd_msg)


# =============================
# POSICIÓN BASE
# =============================

mid = []

for i in range(MOTOR_MAX):

    if i == 0:
        mid.append(0.0)  # pulgar mirando al frente

    else:
        q = minLimits_left[i] + open_ratio * (maxLimits_left[i] - minLimits_left[i])
        mid.append(q)

print("Moving to initial pose")

send_positions(mid)
time.sleep(2)

# =============================
# ROTACIÓN PULGAR
# =============================

steps = np.linspace(0,1,40)

print("Rotating thumb")

for s in steps:

    q = mid.copy()

    q[0] = minLimits_left[0] + s * (maxLimits_left[0] - minLimits_left[0])

    send_positions(q)

    time.sleep(0.05)

print("Returning thumb")

for s in reversed(steps):

    q = mid.copy()

    q[0] = minLimits_left[0] + s * (maxLimits_left[0] - minLimits_left[0])

    send_positions(q)

    time.sleep(0.05)

print("Moving thumb smoothly to 0")

start = q[0]   # posición actual del pulgar

for s in np.linspace(0,1,40):

    q = mid.copy()

    q[0] = start + s * (0.0 - start)

    send_positions(q)

    time.sleep(0.05)


print("Done.")
