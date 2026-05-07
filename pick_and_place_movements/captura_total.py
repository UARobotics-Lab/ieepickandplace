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
# LECTOR MANOS
# =========================
class HandsReader:

    def __init__(self):
        self.left = None
        self.right = None

    def init(self):
        self.subL = ChannelSubscriber("rt/dex3/left/state", HandState_)
        self.subL.Init(self.cb_left, 10)

        self.subR = ChannelSubscriber("rt/dex3/right/state", HandState_)
        self.subR.Init(self.cb_right, 10)

    def cb_left(self, msg):
        self.left = msg

    def cb_right(self, msg):
        self.right = msg

    def get_positions(self):

        pos = {}

        if self.left:
            for i, m in enumerate(self.left.motor_state):
                pos[f"mano_izq_{i}"] = m.q

        if self.right:
            for i, m in enumerate(self.right.motor_state):
                pos[f"mano_der_{i}"] = m.q

        return pos


# =========================
# CAPTURAS
# =========================
def capturar_completo(arm, hands):

    input("\nMueva TODO (brazos + manos) y presione Enter...")

    pos = {}
    pos.update(arm.get_positions())
    pos.update(hands.get_positions())

    dur = float(input("Duración (s): "))

    return {
        "nombre": "",
        "posiciones": pos,
        "duracion": dur
    }


def capturar_solo_manos(hands):

    input("\nPosicione SOLO las manos y presione Enter...")

    pos = hands.get_positions()

    dur = float(input("Duración (s): "))

    return {
        "nombre": "",
        "posiciones": pos,
        "duracion": dur
    }


# =========================
# ACCIONES
# =========================
def insertar_grasp(contador):

    print("\nTipo de grasp:")
    print("1 → Cilindro")
    print("2 → Paralelo")
    print("3 → Precisión")

    op = input("Seleccione: ")

    modos = {
        "1": "cylinder",
        "2": "parallel",
        "3": "precision"
    }

    if op not in modos:
        print("Opción inválida")
        return None

    return {
        "nombre": f"Paso {contador}",
        "posiciones": {
            "accion": "grasp",
            "modo": modos[op],
            "condicion": "any_hand"
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

    nombre = input("\nNombre rutina: ")
    if nombre == "":
        nombre = "rutina_bimanual"

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

    print(f"\n✔ Guardado como {nombre}.txt")


# =========================
# MAIN
# =========================
def main():

    if len(sys.argv) < 2:
        print("Uso: python3 captura_bimanual_full.py <iface>")
        sys.exit()

    ChannelFactoryInitialize(0, sys.argv[1])

    arm = ArmReader()
    arm.init()

    hands = HandsReader()
    hands.init()

    print("Esperando conexión...")
    time.sleep(2)

    pasos = []
    contador = 1

    while True:

        print("\n--- MENU ---")
        print("1 → Capturar movimiento completo")
        print("2 → Capturar SOLO manos")
        print("3 → Insertar grasp")
        print("4 → Insertar release")
        print("f → Finalizar")

        op = input("Opción: ")

        if op == "1":
            pasos.append(capturar_completo(arm, hands))
            contador += 1

        elif op == "2":
            pasos.append(capturar_solo_manos(hands))
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

    if pasos:
        guardar(pasos)
    else:
        print("No se capturaron pasos.")


if __name__ == "__main__":
    main()