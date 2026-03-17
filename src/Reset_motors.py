import time
import sys

from unitree_sdk2py.core.channel import (
    ChannelPublisher,
    ChannelFactoryInitialize,
)

from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandCmd_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__HandCmd_

MOTOR_MAX = 7

# límites de la mano izquierda
maxLimits_left  = [ 1.05,  1.05,  1.75,  0.0,   0.0,   0.0,   0.0 ]
minLimits_left  = [-1.05, -0.724,  0.0, -1.57, -1.75, -1.57, -1.75]

CLOSE_DIR = [0, +1, +1, -1, -1, -1, -1]


def build_mode(motor_id, status=1, timeout=0):

    mode = 0
    mode |= (motor_id & 0x0F)
    mode |= (status & 0x07) << 4
    mode |= (timeout & 0x01) << 7

    return mode


def send_cmd(publisher, cmd_msg):

    publisher.Write(cmd_msg)
    time.sleep(0.02)


def reset_hand(interface):

    print("Initializing DDS on", interface)

    ChannelFactoryInitialize(0, interface)

    publisher = ChannelPublisher("rt/dex3/left/cmd", HandCmd_)
    publisher.Init()

    cmd_msg = unitree_hg_msg_dds__HandCmd_()

    # =========================
    # 1 DESHABILITAR MOTORES
    # =========================

    print("Disabling motors")

    for i in range(MOTOR_MAX):

        cmd_msg.motor_cmd[i].mode = build_mode(i,0,0)
        cmd_msg.motor_cmd[i].tau = 0
        cmd_msg.motor_cmd[i].dq = 0
        cmd_msg.motor_cmd[i].kp = 0
        cmd_msg.motor_cmd[i].kd = 0
        cmd_msg.motor_cmd[i].q = 0

    for _ in range(10):
        send_cmd(publisher, cmd_msg)

    time.sleep(1)

    # =========================
    # 2 REHABILITAR
    # =========================

    print("Re-enabling motors")

    for i in range(MOTOR_MAX):
        cmd_msg.motor_cmd[i].mode = build_mode(i,1,0)

    for _ in range(10):
        send_cmd(publisher, cmd_msg)

    time.sleep(0.5)

    # =========================
    # 3 ENVIAR POSICIÓN ABIERTA
    # =========================

    print("Sending open pose")

    open_pos = []

    for i in range(MOTOR_MAX):

        if i == 0:
            open_pos.append(0.0)
        else:
            if CLOSE_DIR[i] == 1:
                open_pos.append(minLimits_left[i])
            else:
                open_pos.append(maxLimits_left[i])

    for _ in range(50):

        for i in range(MOTOR_MAX):

            cmd_msg.motor_cmd[i].mode = build_mode(i,1,0)
            cmd_msg.motor_cmd[i].tau = 0
            cmd_msg.motor_cmd[i].dq = 0
            cmd_msg.motor_cmd[i].kp = 0.8
            cmd_msg.motor_cmd[i].kd = 0.1
            cmd_msg.motor_cmd[i].q = open_pos[i]

        send_cmd(publisher, cmd_msg)

    print("Reset finished")
    print("Hand should move to open position")


# =========================
# MAIN
# =========================

if __name__ == "__main__":

    if len(sys.argv) < 2:

        print("Usage:")
        print("python3 reset_dex3_hand.py <interface>")
        print("Example: python3 reset_dex3_hand.py enp2s0")
        sys.exit()

    iface = sys.argv[1]

    reset_hand(iface)
