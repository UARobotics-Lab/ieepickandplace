import time
import math
import numpy as np

from unitree_sdk2py.core.channel import (
    ChannelPublisher,
    ChannelSubscriber,
    ChannelFactoryInitialize,
)

from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandCmd_, HandState_
from unitree_sdk2py.idl.default import (
    unitree_hg_msg_dds__HandCmd_,
    unitree_hg_msg_dds__HandState_
)

# ===============================
# CONFIG
# ===============================

MOTOR_MAX = 7
INVALID_VALUE = 30000
SCALE = 10000.0
PRESSURE_THRESHOLD = 11.0   # Ajustable

maxLimits_left  = [1.05,1.05,1.75,0,0,0,0]
minLimits_left  = [-1.05,-0.724,0,-1.57,-1.75,-1.57,-1.75]

maxLimits_right = [1.05,0.742,0,1.57,1.75,1.57,1.75]
minLimits_right = [-1.05,-1.05,-1.75,0,0,0,0]


def build_mode(motor_id, status=1, timeout=0):
    mode = 0
    mode |= (motor_id & 0x0F)
    mode |= (status & 0x07) << 4
    mode |= (timeout & 0x01) << 7
    return mode


# ===============================
# SELECCIÓN
# ===============================

hand_id = input("Input hand (L/R): ").strip().upper()
iface = input("Network interface: ").strip()

if hand_id == "L":
    isLeft = True
    cmd_topic = "rt/dex3/left/cmd"
    state_topic = "rt/lf/dex3/left/state"
else:
    isLeft = False
    cmd_topic = "rt/dex3/right/cmd"
    state_topic = "rt/lf/dex3/right/state"

ChannelFactoryInitialize(0, iface)

publisher = ChannelPublisher(cmd_topic, HandCmd_)
publisher.Init()

subscriber = ChannelSubscriber(state_topic, HandState_)
state = unitree_hg_msg_dds__HandState_()

def state_cb(msg):
    global state
    state = msg

subscriber.Init(state_cb, 1)

cmd_msg = unitree_hg_msg_dds__HandCmd_()


# ===============================
# FUNCIÓN PRINCIPAL
# ===============================

def rotate_and_grip_with_sensor():

    maxL = maxLimits_left if isLeft else maxLimits_right
    minL = minLimits_left if isLeft else minLimits_right

    if isLeft:
        CLOSE_DIR = [0, +1, +1, -1, -1, -1, -1]
    else:
        CLOSE_DIR = [0, -1, -1, +1, +1, +1, +1]

    # ===== Posición media =====
    for i in range(MOTOR_MAX):
        cmd_msg.motor_cmd[i].mode = build_mode(i,1,0)
        cmd_msg.motor_cmd[i].tau  = 0.0
        cmd_msg.motor_cmd[i].dq   = 0.0
        cmd_msg.motor_cmd[i].kp   = 1.5
        cmd_msg.motor_cmd[i].kd   = 0.1
        cmd_msg.motor_cmd[i].q    = (maxL[i]+minL[i])/2.0

    publisher.Write(cmd_msg)
    time.sleep(1.0)

    # ===== Rotar =====
    rot = 0
    mid_rot = (maxL[rot] + minL[rot]) / 2.0
    range_rot = (maxL[rot] - minL[rot]) / 2.0

    q_rot = mid_rot + 0.6 * range_rot

    for i in range(MOTOR_MAX):
        if i == rot:
            cmd_msg.motor_cmd[i].q = q_rot

    publisher.Write(cmd_msg)
    time.sleep(0.5)

    print("Closing with sensor feedback...")

    # ===== Cierre con sensor =====
    for item in np.linspace(0, 1.0, 60):

        # Leer presión actual
        max_pressure = 0

        if len(state.press_sensor_state) > 0:
            for sensor in state.press_sensor_state:
                raw = list(sensor.pressure)
                scaled = [
                    0.0 if v == INVALID_VALUE else v/SCALE
                    for v in raw
                ]
                max_pressure = max(max_pressure, max(scaled))

        print("Current pressure:", round(max_pressure,2))

        if max_pressure > PRESSURE_THRESHOLD:
            print("Pressure threshold reached.")
            break

        # mover dedos
        for i in range(MOTOR_MAX):

            mid = (maxL[i] + minL[i]) / 2.0
            range_amp = (maxL[i] - minL[i]) / 2.0

            if i == 0:
                q = q_rot
            else:
                q = mid + CLOSE_DIR[i] * item * range_amp

            cmd_msg.motor_cmd[i].q  = q
            cmd_msg.motor_cmd[i].kp = 2.0
            cmd_msg.motor_cmd[i].kd = 0.1

        publisher.Write(cmd_msg)
        time.sleep(0.05)

    print("Holding grip...")

    # Mantener agarre
    for _ in range(200):
        publisher.Write(cmd_msg)
        time.sleep(0.02)


# ===============================
# EJECUCIÓN
# ===============================

input("Press ENTER to start...")
rotate_and_grip_with_sensor()
print("Done.")

