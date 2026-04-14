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

# 👉 umbral REAL en escala
PRESSURE_THRESHOLD = 10.0  

maxLimits = [1.05, 1.05, 1.75, 0.0, 0.0, 0.0, 0.0]
minLimits = [-1.05, -0.724, 0.0, -1.57, -1.75, -1.57, -1.75]

CLOSE_DIR = [0, +1, +1, -1, -1, -1, -1]

# =========================
# BUILD MODE
# =========================
def build_mode(motor_id, status=1, timeout=0):
    return (motor_id & 0x0F) | ((status & 0x07) << 4) | ((timeout & 0x01) << 7)

# =========================
# CLASE
# =========================
class DexHandLogger:

    def __init__(self):

        self.pub = ChannelPublisher("rt/dex3/left/cmd", HandCmd_)
        self.pub.Init()

        self.sub = ChannelSubscriber("rt/lf/dex3/left/state", HandState_)
        self.sub.Init(self.cb, 1)

        self.msg = unitree_hg_msg_dds__HandCmd_()
        self.state = None

        self.q = [0]*MOTOR_MAX

        # CSV
        self.csv_file = open("dex3_full_dataset.csv", "w", newline="")
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
    # LOG
    # =========================
    def log(self, pressure):

        if len(self.state.press_sensor_state) == 0:
            return

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
    # SMART GRASP
    # =========================
    def smart_grasp(self):

        print("Iniciando smart grasp...")

        # -------------------------
        # BASELINE
        # -------------------------
        print("Calibrando sensores...")

        baseline = 0

        for _ in range(30):
            max_p = 0

            for sensor in self.state.press_sensor_state:
                values = [
                    0 if v == INVALID_VALUE else v / SCALE
                    for v in sensor.pressure
                ]
                max_p = max(max_p, max(values))

            baseline += max_p
            time.sleep(0.02)

        baseline /= 30
        print(f"Baseline: {baseline:.3f}")

        # -------------------------
        # TARGET
        # -------------------------
        targets = []

        for i in range(MOTOR_MAX):
            if i == 0:
                targets.append(self.q[i])
            else:
                targets.append(maxLimits[i] if CLOSE_DIR[i] == 1 else minLimits[i])

        print("Cerrando...")

        contact = False

        while True:

            # -------------------------
            # PRESIÓN ESCALADA
            # -------------------------
            max_pressure = 0

            for sensor in self.state.press_sensor_state:
                values = [
                    0 if v == INVALID_VALUE else v / SCALE
                    for v in sensor.pressure
                ]
                max_pressure = max(max_pressure, max(values))

            delta = max_pressure - baseline

            print(f"Pressure: {max_pressure:.3f} | Delta: {delta:.3f}")

            # -------------------------
            # DETECCIÓN
            # -------------------------
            if max_pressure > PRESSURE_THRESHOLD:

                print("AGARRE REAL DETECTADO ✔")

                for i in range(MOTOR_MAX):
                    self.msg.motor_cmd[i].kp = HOLD_KP

                contact = True

            # -------------------------
            # MOVIMIENTO
            # -------------------------
            if not contact:
                for i in range(1, MOTOR_MAX):
                    self.q[i] += (targets[i] - self.q[i]) * 0.02

            self.send()
            self.log(max_pressure)

            time.sleep(STEP_DELAY)

            if contact:
                break

        # -------------------------
        # HOLD
        # -------------------------
        print("Manteniendo agarre...")

        t0 = time.time()

        while time.time() - t0 < 3:
            self.send()
            self.log(max_pressure)
            time.sleep(STEP_DELAY)

        print("Finalizado ✔")
        self.csv_file.close()


# =========================
# MAIN
# =========================
def main():

    if len(sys.argv) < 2:
        print("Uso: python3 script.py <iface>")
        sys.exit()

    ChannelFactoryInitialize(0, sys.argv[1])

    hand = DexHandLogger()

    hand.wait_state()

    hand.open_hand()
    time.sleep(1)

    hand.smart_grasp()


if __name__ == "__main__":
    main()