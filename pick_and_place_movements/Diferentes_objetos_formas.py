import sys
import time
import csv

from unitree_sdk2py.core.channel import ChannelPublisher, ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandCmd_, HandState_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__HandCmd_

# =========================
# CONFIG
# =========================
MOTOR_MAX = 7
INVALID_VALUE = 30000
SCALE = 10000.0

KP = 1.2
KD = 0.05
HOLD_KP = 0.6

STEP_DELAY = 0.05
PRESSURE_THRESHOLD = 12.0  # escala (0–10)

maxLimits = [1.05, 1.05, 1.75, 0.0, 0.0, 0.0, 0.0]
minLimits = [-1.05, -0.724, 0.0, -1.57, -1.75, -1.57, -1.75]

CLOSE_DIR = [0, +1, +1, -1, -1, -1, -1]

# =========================
def build_mode(motor_id, status=1, timeout=0):
    return (motor_id & 0x0F) | ((status & 0x07) << 4) | ((timeout & 0x01) << 7)

# =========================
class DexHand:

    def __init__(self):

        self.pub = ChannelPublisher("rt/dex3/left/cmd", HandCmd_)
        self.pub.Init()

        self.sub = ChannelSubscriber("rt/lf/dex3/left/state", HandState_)
        self.sub.Init(self.cb, 1)

        self.msg = unitree_hg_msg_dds__HandCmd_()
        self.state = None

        self.q = [0]*MOTOR_MAX

        # CSV
        self.csv_file = open("dex3_dataset.csv", "w", newline="")
        self.writer = csv.writer(self.csv_file)

        header = (
            ["time","pressure"]
            + [f"joint{i}" for i in range(MOTOR_MAX)]
            + [f"motor_temp{i}" for i in range(MOTOR_MAX)]
            + ["sensor_id"]
            + [f"p{i}" for i in range(12)]
        )
        self.writer.writerow(header)

    def cb(self, msg):
        self.state = msg

    def wait_state(self):
        print("Esperando estado...")
        while self.state is None:
            time.sleep(0.01)
        print("OK ✔")

        self.q = [m.q for m in self.state.motor_state]

    def send(self):
        for i in range(MOTOR_MAX):
            self.msg.motor_cmd[i].mode = build_mode(i,1,0)
            self.msg.motor_cmd[i].kp = KP
            self.msg.motor_cmd[i].kd = KD
            self.msg.motor_cmd[i].q = float(self.q[i])
            self.msg.motor_cmd[i].dq = 0
            self.msg.motor_cmd[i].tau = 0

        self.pub.Write(self.msg)

    # =========================
    # PRESION ESCALADA
    # =========================
    def get_pressure(self):

        max_pressure = 0

        for sensor in self.state.press_sensor_state:
            values = [
                0 if v == INVALID_VALUE else v / SCALE
                for v in sensor.pressure
            ]
            max_pressure = max(max_pressure, max(values))

        return max_pressure

    # =========================
    # LOG
    # =========================
    def log(self, pressure):

        motor_temps = [
            float(self.state.motor_state[i].temperature[0])
            for i in range(MOTOR_MAX)
        ]

        for sensor_id, sensor in enumerate(self.state.press_sensor_state):

            scaled = [
                0 if v == INVALID_VALUE else v / SCALE
                for v in sensor.pressure
            ]

            self.writer.writerow(
                [time.time(), pressure]
                + self.q
                + motor_temps
                + [sensor_id]
                + scaled
            )

    # =========================
    # ABRIR
    # =========================
    def open_hand(self):

        print("Abriendo mano...")

        open_pos = []

        for i in range(MOTOR_MAX):
            if i == 0:
                open_pos.append(0.0)
            else:
                open_pos.append(minLimits[i] if CLOSE_DIR[i] == 1 else maxLimits[i])

        for _ in range(100):
            for i in range(MOTOR_MAX):
                self.q[i] += (open_pos[i] - self.q[i]) * 0.1

            self.send()
            time.sleep(0.03)

        print("Mano abierta ✔")

    # =========================
    # AGARRE CILINDRICO
    # =========================
    def grasp_cylinder(self):

        print("Grasp cilindrico...")

        targets = []

        for i in range(MOTOR_MAX):
            if i == 0:
                targets.append(self.q[i])
            else:
                targets.append(maxLimits[i] if CLOSE_DIR[i] == 1 else minLimits[i])

        while True:

            pressure = self.get_pressure()
            print(f"[Cylinder] Pressure: {pressure:.3f}")

            if pressure > PRESSURE_THRESHOLD:
                print("Contacto detectado ✔")
                for i in range(MOTOR_MAX):
                    self.msg.motor_cmd[i].kp = HOLD_KP
                break

            for i in range(1, MOTOR_MAX):
                self.q[i] += (targets[i] - self.q[i]) * 0.02

            self.send()
            self.log(pressure)

            time.sleep(STEP_DELAY)


    # =========================
    # AGARRE PARALELO (FLUIDO DESDE APERTURA)
    # =========================
    def grasp_parallel(self):

        print("Grasp paralelo (inicio natural)...")

        # =========================
        # JOINTS
        # =========================
        THUMB_BASE = 0
        THUMB_1 = 1
        THUMB_2 = 2

        MIDDLE_BASE = 3
        MIDDLE_TIP  = 4

        INDEX_BASE  = 5
        INDEX_TIP   = 6

        # =========================
        # 1. NO TOCAR EL PULGAR (CLAVE)
        # =========================
        self.q[THUMB_BASE] = 0.0   # mantener centrado
        # NO resetear THUMB_1
        # NO resetear THUMB_2

        # =========================
        # 2. SOLO ESTIRAR OTROS DEDOS
        # =========================
        self.q[MIDDLE_TIP] = 0.0
        self.q[INDEX_TIP]  = 0.0

        self.send()
        time.sleep(0.5)

        # =========================
        # 3. TARGETS
        # =========================
        targets = {}

        # índice y medio (bases)
        for i in [MIDDLE_BASE, INDEX_BASE]:
            if CLOSE_DIR[i] == 1:
                targets[i] = maxLimits[i]
            else:
                targets[i] = minLimits[i]

        # solo thumb_1 se mueve DESDE donde esté
        if CLOSE_DIR[THUMB_1] == 1:
            targets[THUMB_1] = maxLimits[THUMB_1]
        else:
            targets[THUMB_1] = minLimits[THUMB_1]

        print("Cierre progresivo desde apertura real...")

        # =========================
        # 4. LOOP
        # =========================
        while True:

            pressure = self.get_pressure()
            print(f"[Parallel Natural] Pressure: {pressure:.3f}")

            if pressure > PRESSURE_THRESHOLD:
                print("Contacto detectado ✔")

                for i in range(MOTOR_MAX):
                    self.msg.motor_cmd[i].kp = HOLD_KP

                break

            # índice y medio
            for i in [MIDDLE_BASE, INDEX_BASE]:
                self.q[i] += (targets[i] - self.q[i]) * 0.02

            # pulgar fluido (desde apertura real)
            self.q[THUMB_1] += (targets[THUMB_1] - self.q[THUMB_1]) * 0.02

            # thumb_2 se queda quieto (no tocar)

            self.send()
            self.log(pressure)

            time.sleep(STEP_DELAY)
    
    # =========================
    # AGARRE DE PRECISIÓN (OBJETOS PEQUEÑOS)
    # =========================
    def grasp_precision(self):

        print("Grasp precisión (thumb + index)...")

        # =========================
        # JOINTS
        # =========================
        THUMB_BASE = 0
        THUMB_1 = 1
        THUMB_2 = 2

        MIDDLE_BASE = 3
        MIDDLE_TIP  = 4

        INDEX_BASE  = 5
        INDEX_TIP   = 6

        # =========================
        # 1. CONFIG INICIAL
        # =========================
        self.q[THUMB_BASE] = -0.4   # rotación

        # pulgar recto inicial
        self.q[THUMB_2] = 0.0

        # índice recto
        self.q[INDEX_TIP] = 0.0

        # medio fuera del agarre
        self.q[MIDDLE_BASE] = 0.0
        self.q[MIDDLE_TIP]  = 0.0

        self.send()
        time.sleep(0.5)

        # =========================
        # 2. TARGETS
        # =========================
        targets = {}

        # índice base
        if CLOSE_DIR[INDEX_BASE] == 1:
            targets[INDEX_BASE] = maxLimits[INDEX_BASE]
        else:
            targets[INDEX_BASE] = minLimits[INDEX_BASE]

        # pulgar (solo thumb_1)
        if CLOSE_DIR[THUMB_1] == 1:
            targets[THUMB_1] = maxLimits[THUMB_1]
        else:
            targets[THUMB_1] = minLimits[THUMB_1]

        print("Cerrando pinza de precisión...")

        # =========================
        # 3. LOOP
        # =========================
        while True:

            pressure = self.get_pressure()
            print(f"[Precision] Pressure: {pressure:.3f}")

            if pressure > PRESSURE_THRESHOLD:
                print("Objeto pequeño asegurado ✔")

                for i in range(MOTOR_MAX):
                    self.msg.motor_cmd[i].kp = HOLD_KP

                break

            # índice
            self.q[INDEX_BASE] += (targets[INDEX_BASE] - self.q[INDEX_BASE]) * 0.03

            # pulgar
            self.q[THUMB_1] += (targets[THUMB_1] - self.q[THUMB_1]) * 0.03

            self.send()
            self.log(pressure)

            time.sleep(STEP_DELAY)

    # =========================
    # HOLD
    # =========================
    def hold(self, t=3):

        print("Manteniendo agarre...")

        t0 = time.time()

        while time.time() - t0 < t:
            pressure = self.get_pressure()
            self.send()
            self.log(pressure)
            time.sleep(STEP_DELAY)

    def close_csv(self):
        self.csv_file.close()


# =========================
# MAIN
# =========================
def main():

    if len(sys.argv) < 2:
        print("Uso: python3 script.py <iface>")
        sys.exit()

    ChannelFactoryInitialize(0, sys.argv[1])

    hand = DexHand()
    hand.wait_state()

    # =========================
    # SELECCION DE MODO
    # =========================
    print("\nSelecciona modo:")
    print("1 → Cilindro")
    print("2 → Paralelo")
    print("3 → Precision")

    mode = input("Modo: ")

    hand.open_hand()
    time.sleep(1)

    if mode == "1":
        hand.grasp_cylinder()
    elif mode == "2":
        hand.grasp_parallel()
    elif mode == "3":
        hand.grasp_precision()
    else:
        print("Modo inválido")
        return

    hand.hold(3)
    hand.close_csv()

    print("Finalizado ✔")


if __name__ == "__main__":
    main()