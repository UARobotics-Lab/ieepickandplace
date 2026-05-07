import sys
import time
import json
from datetime import datetime

from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelSubscriber
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_, HandState_

# =========================
# CONFIG
# =========================
BRAZOS = list(range(15, 29))
CINTURA = [12, 13, 14]

# =========================
# LECTOR BRAZO
# =========================
class ArmReader:

    def __init__(self):
        self.state = None

    def init(self):
        self.sub = ChannelSubscriber("rt/lowstate", LowState_)
        self.sub.Init(self.cb, 10)

    def cb(self, msg):
        self.state = msg

    def get_positions(self):
        if self.state is None:
            return {}
        return {str(i): self.state.motor_state[i].q for i in BRAZOS + CINTURA}


# =========================
# LECTOR MANO
# =========================
class HandReader:

    def __init__(self):
        self.state = None

    def init(self):
        self.sub = ChannelSubscriber("rt/dex3/left/state", HandState_)
        self.sub.Init(self.cb, 10)

    def cb(self, msg):
        self.state = msg

    def get_positions(self):
        if self.state is None:
            return {}

        pos = {}
        for i, m in enumerate(self.state.motor_state):
            pos[f"mano_izq_{i}"] = m.q

        return pos


# =========================
# FUNCIONES
# =========================
def seleccionar_grasp():

    print("\nTipo de agarre:")
    print("1 → Cilíndrico")
    print("2 → Paralelo")
    print("3 → Precisión")

    op = input("Seleccione: ")

    if op == "1":
        return "cylinder"
    elif op == "2":
        return "parallel"
    elif op == "3":
        return "precision"
    return None


# =========================
# CAPTURAS
# =========================
def capturar_motion(arm, hand):

    input("Mueva el robot y presione Enter...")

    pos = {}
    pos.update(arm.get_positions())
    pos.update(hand.get_positions())

    dur = float(input("Duración (s): "))

    return {
        "nombre": "",
        "posiciones": pos,
        "duracion": dur
    }


def capturar_hand_pose(hand):

    input("Posicione SOLO la mano y presione Enter...")

    raw = hand.get_positions()

    #limpiar 
    pos = {}

    for k, v in raw.items():
        if "mano_izq" in k:
            pos[k] = v

    dur = float(input("Duración (s): "))

    return {
        "nombre": "",
        "posiciones": pos,
        "duracion": dur
    }

def insertar_grasp(contador):

    modo = seleccionar_grasp()

    if modo is None:
        return None

    return {
        "nombre": f"Paso {contador}",
        "posiciones": {
            "accion": "grasp",
            "modo": modo
        },
        "duracion": 0.0
    }


def insertar_release(contador):

    return {
        "nombre": f"Paso {contador}",
        "posiciones": {
            "accion": "release"
        },
        "duracion": 0.0
    }


# =========================
# GUARDAR
# =========================
def guardar(pasos):

    nombre = input("Nombre rutina: ")
    if nombre == "":
        nombre = "rutina"

    for i, p in enumerate(pasos):
        p["nombre"] = f"Paso {i+1}"

    data = {
        "nombre_rutina": nombre,
        "fecha_creacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "numero_pasos": len(pasos),
        "pasos": pasos
    }

    with open(nombre + ".txt", "w") as f:
        json.dump(data, f, indent=2)

    print(f"Guardado como {nombre}.txt ✔")


# =========================
# MAIN
# =========================
def main():

    if len(sys.argv) < 2:
        print("Uso: python3 script.py <iface>")
        sys.exit()

    ChannelFactoryInitialize(0, sys.argv[1])

    arm = ArmReader()
    arm.init()

    hand = HandReader()
    hand.init()

    print("Esperando conexión...")
    time.sleep(2)

    pasos = []
    contador = 1

    while True:

        print("\n--- MENU ---")
        print("1 → Capturar movimiento completo")
        print("2 → Capturar solo mano")
        print("3 → Insertar grasp")
        print("4 → Insertar release")
        print("f → Finalizar")

        op = input("Opción: ")

        if op == "1":
            paso = capturar_motion(arm, hand)
            pasos.append(paso)
            contador += 1

        elif op == "2":
            paso = capturar_hand_pose(hand)
            pasos.append(paso)
            contador += 1

        elif op == "3":
            paso = insertar_grasp(contador)
            if paso:
                pasos.append(paso)
                contador += 1

        elif op == "4":
            pasos.append(insertar_release(contador))
            contador += 1

        elif op == "f":
            break

    guardar(pasos)


if __name__ == "__main__":
    main()