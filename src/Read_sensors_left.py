import time
import csv
import numpy as np

from unitree_sdk2py.core.channel import (
    ChannelPublisher,
    ChannelSubscriber,
    ChannelFactoryInitialize,
)

from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandCmd_, HandState_
from unitree_sdk2py.idl.default import (
    unitree_hg_msg_dds__HandCmd_,
    unitree_hg_msg_dds__HandState_,
)

# =====================================
# CONFIG
# =====================================

MOTOR_MAX = 7
INVALID_VALUE = 30000
SCALE = 10000.0

open_ratio = 0.3 # posición inicial (0 abierto, 1 cerrado)

maxLimits_left  = [ 1.05,  1.05,  1.75,  0.0,   0.0,   0.0,   0.0 ]
minLimits_left  = [-1.05, -0.724,  0.0, -1.57, -1.75, -1.57, -1.75]

# dirección cierre mano izquierda
CLOSE_DIR = [0, +1, +1, -1, -1, -1, -1]

# =====================================
# DDS
# =====================================

iface = input("Network interface: ")

ChannelFactoryInitialize(0, iface)

publisher = ChannelPublisher("rt/dex3/left/cmd", HandCmd_)
publisher.Init()

subscriber = ChannelSubscriber("rt/lf/dex3/left/state", HandState_)

cmd_msg = unitree_hg_msg_dds__HandCmd_()
state = unitree_hg_msg_dds__HandState_()

def cb(msg):
    global state
    state = msg

subscriber.Init(cb,1)

# =====================================
# CSV SETUP
# =====================================

csv_file = open("dex3_pressure_dataset.csv", "w", newline="")
writer = csv.writer(csv_file)

header = (
    ["time","step","sensor_id"]
    + [f"joint{i}" for i in range(MOTOR_MAX)]
    + [f"p{i}" for i in range(12)]
)

writer.writerow(header)

print("CSV file created")

# =====================================
# UTILIDADES
# =====================================

current_q = [0]*MOTOR_MAX

def build_mode(motor_id,status=1,timeout=0):

    mode = 0
    mode |= (motor_id & 0x0F)
    mode |= (status & 0x07) << 4
    mode |= (timeout & 0x01) << 7
    return mode


def send_positions(q):

    global current_q
    current_q = q

    for i in range(MOTOR_MAX):

        cmd_msg.motor_cmd[i].mode = build_mode(i,1,0)
        cmd_msg.motor_cmd[i].tau = 0
        cmd_msg.motor_cmd[i].dq = 0
        cmd_msg.motor_cmd[i].kp = 1.5
        cmd_msg.motor_cmd[i].kd = 0.1
        cmd_msg.motor_cmd[i].q = q[i]

    publisher.Write(cmd_msg)


# =====================================
# LECTURA DE SENSORES
# =====================================

def read_and_save(step):

    if len(state.press_sensor_state) == 0:
        return

    for sensor_id, sensor in enumerate(state.press_sensor_state):

        raw = list(sensor.pressure)

        scaled = [
            0 if v == INVALID_VALUE else v / SCALE
            for v in raw
        ]

        writer.writerow(
            [time.time(), step, sensor_id] + current_q + scaled
        )

        matrix = np.array(scaled).reshape(3,4)

        print(f"\nSensor {sensor_id}")
        print(matrix)


# =====================================
# EXPERIMENTO
# =====================================

def grasp_experiment():

    maxL = maxLimits_left
    minL = minLimits_left

    # -------------------------
    # Posición inicial abierta
    # -------------------------

    mid = []

    for i in range(MOTOR_MAX):

        if i == 0:
            mid.append(0.0)  # pulgar no rota

        else:

            if CLOSE_DIR[i] == 1:
                open_pos = minL[i]
                close_pos = maxL[i]
            else:
                open_pos = maxL[i]
                close_pos = minL[i]

            q = open_pos + open_ratio * (close_pos - open_pos)

            mid.append(q)


    print("Moving to initial open pose")

    send_positions(mid)
    time.sleep(2)

# --------------------------------
# calcular targets de cierre
# --------------------------------

    targets = []

    for i in range(MOTOR_MAX):

        if i == 0:
            targets.append(mid[i])  # pulgar no rota

        else:
            if CLOSE_DIR[i] == 1:
                targets.append(maxL[i])
            else:
                targets.append(minL[i])


    steps = np.linspace(0,1,40)

    # --------------------------------
    # CERRAR
    # --------------------------------

    print("Closing hand")

    for s in steps:

        q = []

        for i in range(MOTOR_MAX):

            q.append(mid[i] + s * (targets[i] - mid[i]))

        send_positions(q)

        read_and_save(s)

        time.sleep(0.2)


    # --------------------------------
    # ABRIR
    # --------------------------------

    print("Opening hand")

    for s in steps:

        q = []

        for i in range(MOTOR_MAX):

            q.append(targets[i] + s * (mid[i] - targets[i]))

        send_positions(q)

        read_and_save(1 - s)

        time.sleep(0.2)



    time.sleep(0.2)

    csv_file.close()

    print("\nDataset guardado en dex3_pressure_dataset.csv")


# =====================================
# RUN
# =====================================

input("Press ENTER to start experiment")

grasp_experiment()
