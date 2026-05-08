# =====================================
# PLAYER COMPLETO BILATERAL
# BRAZOS + MANOS IZQ/DER
# =====================================

ruta = "dos_manos.txt"

import sys
import time
import math
import json

from unitree_sdk2py.core.channel import (
    ChannelPublisher,
    ChannelSubscriber,
    ChannelFactoryInitialize
)

from unitree_sdk2py.idl.unitree_hg.msg.dds_ import (
    HandCmd_,
    HandState_,
    LowCmd_,
    LowState_
)

from unitree_sdk2py.idl.default import (
    unitree_hg_msg_dds__HandCmd_,
    unitree_hg_msg_dds__LowCmd_
)

from unitree_sdk2py.utils.crc import CRC
from unitree_sdk2py.utils.thread import RecurrentThread


# =====================================
# CONFIG
# =====================================

PRESSURE_THRESHOLD = 8.10


# =====================================
# HANDS CONTROL
# =====================================

class Hands:

    def __init__(self):

        self.mode = "normal"

        # =====================================
        # PUBLISHERS
        # =====================================
        self.pubL = ChannelPublisher(
            "rt/dex3/left/cmd",
            HandCmd_
        )

        self.pubR = ChannelPublisher(
            "rt/dex3/right/cmd",
            HandCmd_
        )

        self.pubL.Init()
        self.pubR.Init()

        # =====================================
        # SUBSCRIBERS
        # =====================================
        self.subL = ChannelSubscriber(
            "rt/dex3/left/state",
            HandState_
        )

        self.subR = ChannelSubscriber(
            "rt/dex3/right/state",
            HandState_
        )

        self.subL.Init(self.cbL, 10)
        self.subR.Init(self.cbR, 10)

        # =====================================
        # MSGS
        # =====================================
        self.msgL = unitree_hg_msg_dds__HandCmd_()
        self.msgR = unitree_hg_msg_dds__HandCmd_()

        self.stateL = None
        self.stateR = None

        self.qL = [0.0] * 7
        self.qR = [0.0] * 7

        # =====================================
        # CONTROL
        # =====================================
        self.KP = 0.3
        self.KD = 0.05
        self.HOLD_KP = 0.6

        self.current_kpL = [self.KP] * 7
        self.current_kpR = [self.KP] * 7

        # =====================================
        # LIMITES IZQUIERDA
        # =====================================
        self.maxLimits_left = [
            1.05,
            1.05,
            1.75,
            0,
            0,
            0,
            0
        ]

        self.minLimits_left = [
            -1.05,
            -0.724,
            0,
            -1.57,
            -1.75,
            -1.57,
            -1.75
        ]

        # =====================================
        # LIMITES DERECHA
        # =====================================
        self.maxLimits_right = [
            1.05,
            0.742,
            0,
            1.57,
            1.75,
            1.57,
            1.75
        ]

        self.minLimits_right = [
            -1.05,
            -1.05,
            -1.75,
            0,
            0,
            0,
            0
        ]

        # =====================================
        # DIRECCIONES DE CIERRE
        # =====================================
        self.CLOSE_DIR_LEFT = [
            0,
            +1,
            +1,
            -1,
            -1,
            -1,
            -1
        ]

        self.CLOSE_DIR_RIGHT = [
            0,
            -1,
            -1,
            +1,
            +1,
            +1,
            +1
        ]

    # =====================================
    # CALLBACKS
    # =====================================

    def cbL(self, msg):
        self.stateL = msg

    def cbR(self, msg):
        self.stateR = msg

    # =====================================
    # WAIT
    # =====================================

    def wait(self):

        while self.stateL is None or self.stateR is None:
            time.sleep(0.01)

        for i in range(7):

            self.qL[i] = self.stateL.motor_state[i].q
            self.qR[i] = self.stateR.motor_state[i].q

    # =====================================
    # SEND
    # =====================================

    def send(self):

        for i in range(7):

            # LEFT
            self.msgL.motor_cmd[i].q = float(self.qL[i])
            self.msgL.motor_cmd[i].kp = self.current_kpL[i]
            self.msgL.motor_cmd[i].kd = self.KD

            # RIGHT
            self.msgR.motor_cmd[i].q = float(self.qR[i])
            self.msgR.motor_cmd[i].kp = self.current_kpR[i]
            self.msgR.motor_cmd[i].kd = self.KD

        self.pubL.Write(self.msgL)
        self.pubR.Write(self.msgR)

    # =====================================
    # MOVE NORMAL
    # =====================================

    def move(self, pos, duration=1.0):

        qL0 = self.qL.copy()
        qR0 = self.qR.copy()

        qL1 = self.qL.copy()
        qR1 = self.qR.copy()

        for k, v in pos.items():

            if "mano_izq" in k:

                idx = int(k.split("_")[-1])
                qL1[idx] = v

            elif "mano_der" in k:

                idx = int(k.split("_")[-1])
                qR1[idx] = v

        steps = max(1, int(duration / 0.02))

        for s in range(steps):

            r = (1 - math.cos(math.pi * s / steps)) / 2

            for i in range(7):

                self.qL[i] = qL0[i] + (qL1[i] - qL0[i]) * r
                self.qR[i] = qR0[i] + (qR1[i] - qR0[i]) * r

            self.send()

            time.sleep(0.02)

        self.qL = qL1.copy()
        self.qR = qR1.copy()

        self.send()

    # =====================================
    # PRESSURE
    # =====================================

    def pressure(self):

        def max_pressure(state):

            if state is None:
                return 0.0

            pmax = 0.0

            for s in state.press_sensor_state:

                vals = [v / 10000.0 for v in s.pressure]
                pmax = max(pmax, max(vals))

            return pmax

        return max_pressure(self.stateL), max_pressure(self.stateR)

    # =====================================
    # GRASP BILATERAL
    # =====================================

    def grasp(self):

        print("[HANDS] Bilateral grasp")

        self.mode = "grasp"

        targetL = self.qL.copy()
        targetR = self.qR.copy()

        # =====================================
        # TARGETS LEFT
        # =====================================
        for i in range(1, 7):

            if self.CLOSE_DIR_LEFT[i] == 1:
                targetL[i] = self.maxLimits_left[i]
            else:
                targetL[i] = self.minLimits_left[i]

        # =====================================
        # TARGETS RIGHT
        # =====================================
        for i in range(1, 7):

            if self.CLOSE_DIR_RIGHT[i] == 1:
                targetR[i] = self.maxLimits_right[i]
            else:
                targetR[i] = self.minLimits_right[i]

        # =====================================
        # CONTACTO GLOBAL
        # =====================================
        contact = False

        while True:

            pL, pR = self.pressure()

            print(f"L:{pL:.2f}  R:{pR:.2f}")

            # =====================================
            # DETECCIÓN CONTACTO
            # =====================================
            if (
                pL > 8.0
                or
                pR > 8.0
            ) and not contact:

                print("[CONTACT DETECTED]")
                contact = True

            # =====================================
            # FASE 1
            # CIERRE SUAVE
            # =====================================
            if not contact:

                for i in range(1, 7):

                    self.qL[i] += (
                        targetL[i] - self.qL[i]
                    ) * 0.05

                    self.qR[i] += (
                        targetR[i] - self.qR[i]
                    ) * 0.05

            # =====================================
            # FASE 2
            # APRIETE REAL
            # =====================================
            else:

                for i in range(1, 7):

                    self.qL[i] += (
                        0.01 *
                        self.CLOSE_DIR_LEFT[i]
                    )

                    self.qR[i] += (
                        0.01 *
                        self.CLOSE_DIR_RIGHT[i]
                    )

            self.send()

            # =====================================
            # EXIT
            # =====================================
            if (
                pL > PRESSURE_THRESHOLD
                or
                pR > PRESSURE_THRESHOLD
            ):

                print("[BILATERAL GRASP OK]")

                for i in range(7):

                    self.current_kpL[i] = self.HOLD_KP
                    self.current_kpR[i] = self.HOLD_KP

                self.send()

                break

            time.sleep(0.03)

    # =====================================
    # RELEASE
    # =====================================

    def release(self):

        print("[HANDS] Release")

        self.mode = "normal"

        for i in range(7):

            self.qL[i] = 0.0
            self.qR[i] = 0.0

            self.current_kpL[i] = self.KP
            self.current_kpR[i] = self.KP

        self.send()

        time.sleep(1.0)


# =====================================
# ARM CONTROL
# =====================================

class Arm:

    def __init__(self):

        self.control_dt = 0.02

        self.crc = CRC()

        self.cmd = unitree_hg_msg_dds__LowCmd_()

        self.state = None
        self.first = False

        self.current_q = {}
        self.q_init = {}
        self.target = {}

        self.T = 2.0
        self.start_time = 0.0

        self.joints = list(range(12, 29))

    # =====================================
    # INIT
    # =====================================

    def init(self):

        self.pub = ChannelPublisher(
            "rt/arm_sdk",
            LowCmd_
        )

        self.pub.Init()

        self.sub = ChannelSubscriber(
            "rt/lowstate",
            LowState_
        )

        self.sub.Init(self.cb, 10)

    # =====================================
    # CALLBACK
    # =====================================

    def cb(self, msg):

        self.state = msg
        self.first = True

    # =====================================
    # START
    # =====================================

    def start(self):

        while not self.first:
            time.sleep(0.1)

        self.thread = RecurrentThread(
            interval=self.control_dt,
            target=self.loop
        )

        self.thread.Start()

    # =====================================
    # INTERPOLATION
    # =====================================

    def interpolate(self, q0, q1):

        t = time.time() - self.start_time

        ratio = min(t / self.T, 1.0)

        ratio = (1 - math.cos(math.pi * ratio)) / 2

        return q0 + (q1 - q0) * ratio

    # =====================================
    # CONTROL LOOP
    # =====================================

    def loop(self):

        if self.state is None:
            return

        self.cmd.motor_cmd[29].q = 1

        for j in self.joints:

            q0 = self.q_init.get(
                j,
                self.state.motor_state[j].q
            )

            q1 = self.target.get(j, q0)

            q = self.interpolate(q0, q1)

            # codos más rígidos
            if j in [18, 25]:

                kp = 40.0
                kd = 5.0

            else:

                kp = 20.0
                kd = 3.5

            self.cmd.motor_cmd[j].q = q
            self.cmd.motor_cmd[j].kp = kp
            self.cmd.motor_cmd[j].kd = kd

            self.current_q[j] = q

        self.cmd.crc = self.crc.Crc(self.cmd)

        self.pub.Write(self.cmd)

    # =====================================
    # MOVE
    # =====================================

    def move(self, pos, duration=2.0):

        self.q_init = {

            j: self.current_q.get(
                j,
                self.state.motor_state[j].q
            )

            for j in self.joints
        }

        self.target = pos.copy()

        self.T = duration

        self.start_time = time.time()

        while time.time() - self.start_time < self.T:
            time.sleep(self.control_dt)


# =====================================
# MAIN
# =====================================

def main():

    if len(sys.argv) < 2:

        print("Uso:")
        print("python3 player.py enp3s0")
        sys.exit()

    # =====================================
    # DDS
    # =====================================

    ChannelFactoryInitialize(
        0,
        sys.argv[1]
    )

    # =====================================
    # LOAD FILE
    # =====================================

    with open(ruta, "r") as f:

        data = json.load(f)

    pasos = data.get("pasos", [])

    # =====================================
    # ARM
    # =====================================

    arm = Arm()

    arm.init()
    arm.start()

    # =====================================
    # HANDS
    # =====================================

    hands = Hands()

    hands.wait()

    print("=================================")
    print("PLAYER BILATERAL INICIADO")
    print("=================================")

    # =====================================
    # EXECUTION
    # =====================================

    for paso in pasos:

        pos = paso.get("posiciones", {})
        dur = paso.get("duracion", 1.5)

        print(f"\n[STEP] duration = {dur}")

        # =====================================
        # ACTIONS
        # =====================================

        if "accion" in pos:

            accion = pos["accion"]

            print(f"[ACTION] {accion}")

            if accion == "grasp":
                hands.grasp()

            elif accion == "release":
                hands.release()

            continue

        # =====================================
        # ARM
        # =====================================

        arm_pos = {

            int(k): v

            for k, v in pos.items()

            if k.isdigit()
        }

        if arm_pos:

            arm.move(
                arm_pos,
                duration=dur
            )

        # =====================================
        # HANDS
        # =====================================

        if hands.mode != "grasp":

            hands.move(
                pos,
                duration=dur
            )

    print("\n✔ Rutina terminada")


# =====================================
# RUN
# =====================================

if __name__ == "__main__":
    main()