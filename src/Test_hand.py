import time
import math
import threading
import numpy as np

from unitree_sdk2py.core.channel import (
    ChannelPublisher,
    ChannelSubscriber,
    ChannelFactoryInitialize,
)

from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandCmd_, HandState_

# ---------------- STATES ----------------
INIT = 0
ROTATE = 1
GRIP = 2
STOP = 3
PRINT = 4

currentState = INIT

# ---------------- LIMITS ----------------
maxLimits_left  = [1.05,1.05,1.75,0,0,0,0]
minLimits_left  = [-1.05,-0.724,0,-1.57,-1.75,-1.57,-1.75]

maxLimits_right = [1.05,0.742,0,1.57,1.75,1.57,1.75]
minLimits_right = [-1.05,-1.05,-1.75,0,0,0,0]

MOTOR_MAX = 7
SENSOR_MAX = 9

# ---------------- RIS MODE ----------------
def build_mode(motor_id,status=1,timeout=0):
    mode = 0
    mode |= (motor_id & 0x0F)
    mode |= (status & 0x07) << 4
    mode |= (timeout & 0x01) << 7
    return mode

# ---------------- DDS ----------------
hand_id = input("Input hand (L/R): ")

if hand_id == "L":
    isLeft = True
    dds_namespace = "rt/dex3/left/cmd"
    sub_namespace = "rt/lf/dex3/left/state"
else:
    isLeft = False
    dds_namespace = "rt/dex3/right/cmd"
    sub_namespace = "rt/lf/dex3/right/state"

iface = input("Network interface (eth0/enp...): ")

ChannelFactoryInitialize(0,iface)

publisher = ChannelPublisher(dds_namespace, HandCmd_)
subscriber = ChannelSubscriber(sub_namespace, HandState_)

msg = HandCmd_()
state = HandState_()

msg.motor_cmd().resize(MOTOR_MAX)
state.motor_state().resize(MOTOR_MAX)
state.press_sensor_state().resize(SENSOR_MAX)

# ---------------- CALLBACK ----------------
def StateHandler(message):
    global state
    state = message

subscriber.InitChannel(StateHandler,1)
publisher.InitChannel()

# ---------------- USER INPUT ----------------
def userInputThread():
    global currentState
    while True:
        ch=input()
        if ch=="q":
            currentState=STOP
            break
        elif ch=="r":
            currentState=ROTATE
        elif ch=="g":
            currentState=GRIP
        elif ch=="p":
            currentState=PRINT
        elif ch=="s":
            currentState=STOP

threading.Thread(target=userInputThread,daemon=True).start()

# ---------------- ROTATE ----------------
count=1
dir=1

def rotateMotors():

    global count,dir

    maxLimits = maxLimits_left if isLeft else maxLimits_right
    minLimits = minLimits_left if isLeft else minLimits_right

    for i in range(MOTOR_MAX):

        mode=build_mode(i,1,0)

        msg.motor_cmd()[i].mode(mode)
        msg.motor_cmd()[i].tau(0)
        msg.motor_cmd()[i].kp(0.5)
        msg.motor_cmd()[i].kd(0.1)

        mid=(maxLimits[i]+minLimits[i])/2
        amp=(maxLimits[i]-minLimits[i])/2

        q=mid+amp*math.sin(count/20000*math.pi)

        msg.motor_cmd()[i].q(q)

    publisher.Write(msg)

    count+=dir
    if count>=10000: dir=-1
    if count<=-10000: dir=1

    time.sleep(0.002)

# ---------------- GRIP ----------------
def gripHand():

    maxLimits = maxLimits_left if isLeft else maxLimits_right
    minLimits = minLimits_left if isLeft else minLimits_right

    for i in range(MOTOR_MAX):

        mode=build_mode(i,1,0)

        msg.motor_cmd()[i].mode(mode)
        msg.motor_cmd()[i].tau(0)

        mid=(maxLimits[i]+minLimits[i])/2

        msg.motor_cmd()[i].q(mid)
        msg.motor_cmd()[i].dq(0)
        msg.motor_cmd()[i].kp(1.5)
        msg.motor_cmd()[i].kd(0.1)

    publisher.Write(msg)
    time.sleep(1)

# ---------------- STOP ----------------
def stopMotors():

    for i in range(MOTOR_MAX):

        mode=build_mode(i,1,1)

        msg.motor_cmd()[i].mode(mode)
        msg.motor_cmd()[i].tau(0)
        msg.motor_cmd()[i].dq(0)
        msg.motor_cmd()[i].kp(0)
        msg.motor_cmd()[i].kd(0)
        msg.motor_cmd()[i].q(0)

    publisher.Write(msg)
    time.sleep(1)

# ---------------- PRINT ----------------
def printState():

    maxLimits = maxLimits_left if isLeft else maxLimits_right
    minLimits = minLimits_left if isLeft else minLimits_right

    q=[]

    for i in range(MOTOR_MAX):

        val=state.motor_state()[i].q()
        val=(val-minLimits[i])/(maxLimits[i]-minLimits[i])
        val=max(0,min(1,val))
        q.append(val)

    print("Hand:",np.round(q,3))
    time.sleep(0.1)

# ---------------- LOOP ----------------
lastState=None

while True:

    if currentState!=lastState:
        print("State:",currentState)
        lastState=currentState

    if currentState==INIT:
        print("Initializing...")
        currentState=ROTATE

    elif currentState==ROTATE:
        rotateMotors()

    elif currentState==GRIP:
        gripHand()

    elif currentState==STOP:
        stopMotors()

    elif currentState==PRINT:
        printState()
