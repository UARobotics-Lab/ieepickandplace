# # ==============================================================
# # ABRE Y CIERRA
# # ==============================================================

# import time
# import numpy as np

# from unitree_sdk2py.core.channel import (
#     ChannelPublisher,
#     ChannelFactoryInitialize,
# )

# from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandCmd_
# from unitree_sdk2py.idl.default import unitree_hg_msg_dds__HandCmd_


# # ===============================
# # CONFIG
# # ===============================

# MOTOR_MAX = 7
# MOVE_STEPS = 120
# STEP_DELAY = 0.03

# maxLimits_left  = [ 1.05,  1.05,  1.75,  0.0,   0.0,   0.0,   0.0 ]
# minLimits_left  = [-1.05, -0.724,  0.0, -1.57, -1.75, -1.57, -1.75]

# # Dirección de cierre SOLO IZQUIERDA
# CLOSE_DIR = [0, +1, +1, -1, -1, -1, -1]


# def build_mode(motor_id, status=1, timeout=0):
#     mode = 0
#     mode |= (motor_id & 0x0F)
#     mode |= (status & 0x07) << 4
#     mode |= (timeout & 0x01) << 7
#     return mode


# # ===============================
# # DDS SETUP
# # ===============================

# iface = input("Network interface (eth0/enp...): ").strip()

# ChannelFactoryInitialize(0, iface)

# publisher = ChannelPublisher("rt/dex3/left/cmd", HandCmd_)
# publisher.Init()

# cmd_msg = unitree_hg_msg_dds__HandCmd_()


# # ===============================
# # FUNCIONES AUXILIARES
# # ===============================

# def send_positions(q_values, kp=1.5):

#     for i in range(MOTOR_MAX):
#         cmd_msg.motor_cmd[i].mode = build_mode(i,1,0)
#         cmd_msg.motor_cmd[i].tau  = 0.0
#         cmd_msg.motor_cmd[i].dq   = 0.0
#         cmd_msg.motor_cmd[i].kp   = kp
#         cmd_msg.motor_cmd[i].kd   = 0.1
#         cmd_msg.motor_cmd[i].q    = q_values[i]

#     publisher.Write(cmd_msg)


# def move_smooth(start_q, end_q, steps=MOVE_STEPS):

#     for alpha in np.linspace(0,1,steps):

#         q_interp = [
#             start_q[i] + alpha*(end_q[i]-start_q[i])
#             for i in range(MOTOR_MAX)
#         ]

#         send_positions(q_interp)
#         time.sleep(STEP_DELAY)


# # ===============================
# # RUTINA PRINCIPAL
# # ===============================

# def open_and_close_left():

#     maxL = maxLimits_left
#     minL = minLimits_left

#     print("Going to middle position...")

#     # Posición media
#     mid = [(maxL[i] + minL[i]) / 2.0 for i in range(MOTOR_MAX)]
#     send_positions(mid)
#     time.sleep(1.0)

#     # ===============================
#     # ABRIR TOTALMENTE
#     # ===============================

#     print("Opening slowly...")

#     open_pos = []

#     for i in range(MOTOR_MAX):

#         if i == 0:
#             # mantener rotación neutra
#             open_pos.append(mid[i])
#         else:
#             # abrir en dirección opuesta al cierre
#             range_amp = (maxL[i] - minL[i]) / 2.0
#             open_pos.append(mid[i] - CLOSE_DIR[i] * range_amp)

#     move_smooth(mid, open_pos)
#     time.sleep(2.0)

#     # ===============================
#     # CERRAR TOTALMENTE
#     # ===============================

#     print("Closing slowly...")

#     close_pos = []

#     for i in range(MOTOR_MAX):

#         if i == 0:
#             close_pos.append(mid[i])
#         else:
#             range_amp = (maxL[i] - minL[i]) / 2.0
#             close_pos.append(mid[i] + CLOSE_DIR[i] * range_amp)

#     move_smooth(open_pos, close_pos)
#     time.sleep(2.0)

#     print("Done.")


# # ===============================
# # EJECUCIÓN
# # ===============================

# input("Press ENTER to start open/close routine...")
# open_and_close_left()



# # ==============================================================
# # DEDOS A LA MISMA DIRECCION
# # ==============================================================

# import time
# import numpy as np

# from unitree_sdk2py.core.channel import (
#     ChannelPublisher,
#     ChannelFactoryInitialize,
# )

# from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandCmd_
# from unitree_sdk2py.idl.default import unitree_hg_msg_dds__HandCmd_

# # ===============================
# # CONFIG
# # ===============================

# MOTOR_MAX = 7
# MOVE_STEPS = 150
# STEP_DELAY = 0.02

# maxLimits_left  = [ 1.05,  1.05,  1.75,  0.0,   0.0,   0.0,   0.0 ]
# minLimits_left  = [-1.05, -0.724,  0.0, -1.57, -1.75, -1.57, -1.75]

# def build_mode(motor_id, status=1, timeout=0):
#     mode = 0
#     mode |= (motor_id & 0x0F)
#     mode |= (status & 0x07) << 4
#     mode |= (timeout & 0x01) << 7
#     return mode

# # ===============================
# # DDS
# # ===============================

# iface = input("Network interface: ").strip()

# ChannelFactoryInitialize(0, iface)

# publisher = ChannelPublisher("rt/dex3/left/cmd", HandCmd_)
# publisher.Init()

# cmd_msg = unitree_hg_msg_dds__HandCmd_()

# # ===============================
# # FUNCIONES
# # ===============================

# def send_positions(q_values, kp=1.8):

#     for i in range(MOTOR_MAX):
#         cmd_msg.motor_cmd[i].mode = build_mode(i,1,0)
#         cmd_msg.motor_cmd[i].tau  = 0.0
#         cmd_msg.motor_cmd[i].dq   = 0.0
#         cmd_msg.motor_cmd[i].kp   = kp
#         cmd_msg.motor_cmd[i].kd   = 0.1
#         cmd_msg.motor_cmd[i].q    = q_values[i]

#     publisher.Write(cmd_msg)

# def move_smooth(start_q, end_q):

#     for alpha in np.linspace(0,1,MOVE_STEPS):

#         q_interp = [
#             start_q[i] + alpha*(end_q[i]-start_q[i])
#             for i in range(MOTOR_MAX)
#         ]

#         send_positions(q_interp)
#         time.sleep(STEP_DELAY)

# # ===============================
# # RUTINA
# # ===============================

# def full_open_close():

#     print("Going to neutral...")

#     mid = [(maxLimits_left[i] + minLimits_left[i]) / 2.0 for i in range(MOTOR_MAX)]
#     send_positions(mid)
#     time.sleep(1.0)

#     # =========================
#     # ABRIR COMPLETAMENTE
#     # =========================

#     print("Opening fully...")

#     open_pos = [
#         minLimits_left[i] if i != 0 else mid[i]
#         for i in range(MOTOR_MAX)
#     ]

#     move_smooth(mid, open_pos)
#     time.sleep(2.0)

#     # =========================
#     # CERRAR COMPLETAMENTE
#     # =========================

#     print("Closing fully...")

#     close_pos = [
#         maxLimits_left[i] if i != 0 else mid[i]
#         for i in range(MOTOR_MAX)
#     ]

#     move_smooth(open_pos, close_pos)
#     time.sleep(2.0)

#     print("Done.")

# input("Press ENTER to run full open/close...")
# full_open_close()


# # ==============================================================
# # ROTACION PULGAR
# # ==============================================================

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
