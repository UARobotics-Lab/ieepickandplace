import time
import numpy as np

from unitree_sdk2py.core.channel import (
    ChannelSubscriber,
    ChannelFactoryInitialize,
)

from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandState_

# =========================
# CONFIG
# =========================
SENSOR_MAX = 9        # ajusta si luego ves otro número
INVALID_VALUE = 30000
SCALE = 10000.0

# =========================
# DDS SETUP
# =========================
hand_id = input("Input hand (L/R): ")

if hand_id.upper() == "L":
    sub_namespace = "rt/lf/dex3/left/state"
else:
    sub_namespace = "rt/lf/dex3/right/state"

iface = input("Network interface (eth0/enp...): ")

ChannelFactoryInitialize(0, iface)

subscriber = ChannelSubscriber(sub_namespace, HandState_)

state = HandState_()

# =========================
# CALLBACK
# =========================
def StateHandler(message):
    global state
    state = message

subscriber.InitChannel(StateHandler, 1)

print("\nEsperando datos de sensores...\n")

# =========================
# FUNCION DE LECTURA
# =========================
def read_pressure():

    try:
        sensor_count = len(state.press_sensor_state())
    except:
        print("No hay datos aún...")
        return

    print("\n==============================")

    for finger in range(sensor_count):

        sensor = state.press_sensor_state()[finger]

        try:
            raw = sensor.data()
            temp = sensor.temp()
            sid  = sensor.id()
        except:
            print(f"Finger {finger}: estructura inesperada")
            continue

        scaled = []

        for v in raw:

            if v == INVALID_VALUE:
                scaled.append(0)
            else:
                scaled.append(v / SCALE)

        print(f"\nFinger ID: {sid}")
        print("Temp:", temp)
        print("Raw:", raw)
        print("Scaled:", np.round(scaled,2))
        print("Max pressure:", np.round(max(scaled),2))

# =========================
# LOOP
# =========================
print("Comandos:")
print("  p  -> leer sensores")
print("  q  -> salir")

while True:

    cmd = input()

    if cmd == "p":
        read_pressure()

    elif cmd == "q":
        break
