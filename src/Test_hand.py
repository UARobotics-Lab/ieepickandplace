import time
import math
import threading
import numpy as np

from unitree_sdk2py.core.channel import (
    ChannelPublisher,
    ChannelSubscriber,
    ChannelFactoryInitialize,
)

# ===== TIPOS IDL (SOLO PARA DDS) =====
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandCmd_, HandState_

# ===== WRAPPERS DEFAULT (MENSAJES REALES) =====
from unitree_sdk2py.idl.default import (
    unitree_hg_msg_dds__HandCmd_,
    unitree_hg_msg_dds__HandState_,
)

# =========================
# STATES
# =========================
INIT   = 0
ROTATE = 1
GRIP   = 2
STOP   = 3
PRINT  = 4

currentState = INIT

# =========================
# LIMITS
# =========================
maxLimits_left  = [1.05, 1.05, 1.75, 0,    0,    0,    0]
minLimits_left  = [-1.05,-0.724,0,   -1.57,-1.75,-1.57,-1.75]

maxLimits_right = [1.05, 0.742,0,    1.57, 1.75, 1.57, 1.75]
minLimits_right = [-1.05,-1.05,-1.75,0,    0,    0,    0]

MOTOR_MAX = 7

# =========================
# RIS MODE
# =========================
def build_mode(motor_id, status=1, timeout=0):
    mode = 0
    mode |= (motor_id & 0x0F)
    mode |= (status & 0x07) << 4
    mode |= (timeout & 0x01) << 7
    return mode

# =========================
# DDS SETUP
# =========================
hand_id = input("Input hand (L/R): ").strip().upper()

if hand_id == "L":
    isLeft = True
    cmd_namespace   = "rt/dex3/left/cmd"
    state_namespace = "rt/lf/dex3/left/state"
else:
    isLeft = False
    cmd_namespace   = "rt/dex3/right/cmd"
    state_namespace = "rt/lf/dex3/right/state"

iface = input("Network interface (eth0/enp...): ").strip()
ChannelFactoryInitialize(0, iface)

publisher  = ChannelPublisher(cmd_namespace, HandCmd_)
subscriber = ChannelSubscriber(state_namespace, HandState_)

publisher.Init()

# =========================
# HAND CMD (WRAPPER)
# =========================
cmd_msg = unitree_hg_msg_dds__HandCmd_()

# =========================
# HAND STATE (WRAPPER)
# =========================
state = unitree_hg_msg_dds__HandState_()

def StateHandler(message):
    global state
    state = message   # message YA es wrapper

subscriber.Init(StateHandler, 1)

# =========================
# USER INPUT
# =========================
def userInputThread():
    global currentState
    while True:
        ch = input().strip()
        if ch == "q":
            currentState = STOP
            break
        elif ch == "r":
            currentState = ROTATE
        elif ch == "g":
            currentState = GRIP
        elif ch == "p":
            currentState = PRINT
        elif ch == "s":
            currentState = STOP

threading.Thread(target=userInputThread, daemon=True).start()

# =========================
# ROTATE
# =========================
count = 1
direction = 1

def rotateMotors():
    global count, direction

    maxL = maxLimits_left if isLeft else maxLimits_right
    minL = minLimits_left if isLeft else minLimits_right

    for i in range(MOTOR_MAX):
        cmd_msg.motor_cmd[i].mode = build_mode(i, 1, 0)
        cmd_msg.motor_cmd[i].tau  = 0.0
        cmd_msg.motor_cmd[i].kp   = 0.5
        cmd_msg.motor_cmd[i].kd   = 0.1

        mid = (maxL[i] + minL[i]) / 2.0
        amp = (maxL[i] - minL[i]) / 2.0
        cmd_msg.motor_cmd[i].q = mid + amp * math.sin(count / 20000.0 * math.pi)

    publisher.Write(cmd_msg)

    count += direction
    if count >= 10000:  direction = -1
    if count <= -10000: direction =  1

    time.sleep(0.002)

# =========================
# GRIP
# =========================
def gripHand():
    maxL = maxLimits_left if isLeft else maxLimits_right
    minL = minLimits_left if isLeft else minLimits_right

    for i in range(MOTOR_MAX):
        cmd_msg.motor_cmd[i].mode = build_mode(i, 1, 0)
        cmd_msg.motor_cmd[i].tau  = 0.0

        mid = (maxL[i] + minL[i]) / 2.0
        cmd_msg.motor_cmd[i].q  = mid
        cmd_msg.motor_cmd[i].dq = 0.0
        cmd_msg.motor_cmd[i].kp = 1.5
        cmd_msg.motor_cmd[i].kd = 0.1

    publisher.Write(cmd_msg)
    time.sleep(1.0)

# =========================
# STOP
# =========================
def stopMotors():
    for i in range(MOTOR_MAX):
        cmd_msg.motor_cmd[i].mode = build_mode(i, 1, 1)
        cmd_msg.motor_cmd[i].tau  = 0.0
        cmd_msg.motor_cmd[i].dq   = 0.0
        cmd_msg.motor_cmd[i].kp   = 0.0
        cmd_msg.motor_cmd[i].kd   = 0.0
        cmd_msg.motor_cmd[i].q    = 0.0

    publisher.Write(cmd_msg)
    time.sleep(1.0)

# =========================
# PRINT STATE
# =========================
def printState():
    if len(state.motor_state) == 0:
        print("No motor state yet...")
        return

    maxL = maxLimits_left if isLeft else maxLimits_right
    minL = minLimits_left if isLeft else minLimits_right

    q_norm = []
    for i in range(MOTOR_MAX):
        q = state.motor_state[i].q
        qn = (q - minL[i]) / (maxL[i] - minL[i])
        q_norm.append(max(0.0, min(1.0, qn)))

    print("Hand:", np.round(q_norm, 3))
    time.sleep(0.1)

# =========================
# MAIN LOOP
# =========================
lastState = None
print("Commands: r=rotate, g=grip, s=stop, p=print, q=quit")

while True:

    if currentState != lastState:
        print("State:", currentState)
        lastState = currentState

    if currentState == INIT:
        print("Initializing...")
        currentState = STOP

    elif currentState == ROTATE:
        rotateMotors()

    elif currentState == GRIP:
        gripHand()

    elif currentState == STOP:
        stopMotors()

    elif currentState == PRINT:
        printState()
