# =====================================
# RUTA
# =====================================
ruta = "tests.txt"

import sys
import time
import math
import json

from unitree_sdk2py.core.channel import ChannelPublisher, ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandCmd_, HandState_, LowCmd_, LowState_
from unitree_sdk2py.idl.default import (
    unitree_hg_msg_dds__HandCmd_,
    unitree_hg_msg_dds__LowCmd_
)

from unitree_sdk2py.utils.crc import CRC
from unitree_sdk2py.utils.thread import RecurrentThread


# =====================================
# HAND CONTROL
# =====================================
class HandSequence:

    def __init__(self):

        self.pub = ChannelPublisher("rt/dex3/left/cmd", HandCmd_)
        self.pub.Init()

        self.sub = ChannelSubscriber("rt/dex3/left/state", HandState_)
        self.sub.Init(self.cb, 10)

        self.msg = unitree_hg_msg_dds__HandCmd_()

        self.state = None
        self.q = [0.0]*7

        self.mode = "normal"

        self.KP = 0.3
        self.KD = 0.05
        self.HOLD_KP = 0.6

        self.INVALID_VALUE = 30000
        self.SCALE = 10000.0

        self.PRESSURE_THRESHOLD = 9.0

        self.maxLimits = [1.05, 1.05, 1.75, 0.0, 0.0, 0.0, 0.0]
        self.minLimits = [-1.05, -0.724, 0.0, -1.57, -1.75, -1.57, -1.75]
        self.CLOSE_DIR = [0, +1, +1, -1, -1, -1, -1]

    def cb(self, msg):
        self.state = msg

    def send(self):

        for i in range(7):
            self.msg.motor_cmd[i].mode = (i & 0x0F) | ((1 & 0x07) << 4)
            self.msg.motor_cmd[i].q = float(self.q[i])
            self.msg.motor_cmd[i].kp = self.KP
            self.msg.motor_cmd[i].kd = self.KD
            self.msg.motor_cmd[i].dq = 0
            self.msg.motor_cmd[i].tau = 0

        self.pub.Write(self.msg)

    def get_pressure(self):

        if self.state is None:
            return 0

        max_p = 0

        for sensor in self.state.press_sensor_state:
            values = [
                0 if v == self.INVALID_VALUE else v / self.SCALE
                for v in sensor.pressure
            ]
            max_p = max(max_p, max(values))

        return max_p
    def wait_state(self):
        print("[HAND] Esperando estado...")

        while self.state is None:
            time.sleep(0.01)

        print("[HAND] OK ✔")

        # sincronizar q con estado real
        for i in range(7):
            self.q[i] = self.state.motor_state[i].q

    # =========================
    # HAND POSE (desde player)
    # =========================
    def apply_positions(self, pos_dict, duration=1.0):

        target = self.q.copy()
        for key, val in pos_dict.items():
            if "mano_izq" in key:
                idx = int(key.split("_")[-1])
                target[idx] = val

        steps = max(1, int(duration / 0.02))
        max_delta = 0.03

        for _ in range(steps):

            for i in range(7):

                error = target[i] - self.q[i]

                if self.mode == "normal":
                    # suave
                    if abs(error) > max_delta:
                        self.q[i] += max_delta * (1 if error > 0 else -1)
                    else:
                        self.q[i] = target[i]

                else:
                    # directo (para grasp)
                    self.q[i] += error * 0.2

            self.send()
            time.sleep(0.02)

        self.q = target.copy()
        self.send()

    # =========================
    # GRASP CILINDRICO REAL
    # =========================
    def grasp_cylinder(self):

        print("[HAND] Grasp cilindrico REAL")

        targets = []

        for i in range(7):
            if i == 0:
                targets.append(self.q[i])
            else:
                targets.append(
                    self.maxLimits[i] if self.CLOSE_DIR[i] == 1 else self.minLimits[i]
                )

        while True:

            pressure = self.get_pressure()
            print(f"[Cylinder] {pressure:.2f}")

            if pressure > self.PRESSURE_THRESHOLD:
                print("Contacto ✔")
                for i in range(7):
                    self.msg.motor_cmd[i].kp = self.HOLD_KP
                break

            for i in range(1,7):
                self.q[i] += (targets[i] - self.q[i]) * 0.04

            self.send()
            time.sleep(0.05)

    # =========================
    # GRASP PARALELO REAL
    # =========================
    def grasp_parallel(self):

        print("[HAND] Grasp paralelo REAL")

        THUMB_1 = 1
        MIDDLE_BASE = 3
        INDEX_BASE = 5

        targets = {}

        for i in [MIDDLE_BASE, INDEX_BASE]:
            targets[i] = self.maxLimits[i] if self.CLOSE_DIR[i] == 1 else self.minLimits[i]

        targets[THUMB_1] = self.maxLimits[THUMB_1] if self.CLOSE_DIR[THUMB_1] == 1 else self.minLimits[THUMB_1]

        while True:

            pressure = self.get_pressure()

            if pressure > self.PRESSURE_THRESHOLD:
                print("Contacto ✔")
                break

            for i in [MIDDLE_BASE, INDEX_BASE, THUMB_1]:

                error = targets[i] - self.q[i]

                speed = 0.04
                delta = error * speed

                max_step = 0.05
                min_step = 0.01

                if delta > max_step:
                    delta = max_step
                elif delta < -max_step:
                    delta = -max_step

                if abs(delta) < min_step:
                    delta = min_step * (1 if error > 0 else -1)

                self.q[i] += delta

            self.send()
            time.sleep(0.05)


    # =========================
    # GRASP PRECISION REAL
    # =========================
    def grasp_precision(self):

        print("[HAND] Grasp precision REAL")

        THUMB_BASE = 0
        THUMB_1 = 1
        INDEX_BASE = 5

        # =========================
        # 1. ORIENTAR PULGAR (CLAVE)
        # =========================
        self.q[THUMB_BASE] = -0.4   #  rotación hacia pinza

        self.send()
        time.sleep(0.3)  # pequeño tiempo para acomodar

        # =========================
        # 2. TARGETS
        # =========================
        targets = {}

        targets[INDEX_BASE] = self.maxLimits[INDEX_BASE] if self.CLOSE_DIR[INDEX_BASE] == 1 else self.minLimits[INDEX_BASE]
        targets[THUMB_1] = self.maxLimits[THUMB_1] if self.CLOSE_DIR[THUMB_1] == 1 else self.minLimits[THUMB_1]

        # =========================
        # 3. CIERRE
        # =========================
        while True:

            pressure = self.get_pressure()

            if pressure > self.PRESSURE_THRESHOLD:
                print("Objeto pequeño ✔")
                break

            for i in [INDEX_BASE, THUMB_1]:

                error = targets[i] - self.q[i]

                speed = 0.04
                delta = error * speed

                max_step = 0.05
                min_step = 0.01

                if delta > max_step:
                    delta = max_step
                elif delta < -max_step:
                    delta = -max_step

                if abs(delta) < min_step:
                    delta = min_step * (1 if error > 0 else -1)

                self.q[i] += delta

            self.send()
            time.sleep(0.05)

    # =========================
    def release(self):
        print("[HAND] Release")

        self.q = [0.0]*7

        for _ in range(10):
            self.send()
            time.sleep(0.05)


# =====================================
# ARM CONTROL 
# =====================================
class ArmSequence:

    def __init__(self):

        self.control_dt = 0.02
        self.kp = 60.0
        self.kd = 1.5
        self.crc = CRC()

        self.t = 0.0
        self.T = 3.0

        self.low_cmd = unitree_hg_msg_dds__LowCmd_()
        self.low_state = None
        self.first_update = False

        self.target_pos = {}
        self.q_init_override = None

        self.arm_joints = [
            15,16,17,18,19,20,21,
            22,23,24,25,26,27,28,
            12,13,14
        ]

    def Init(self):

        self.publisher = ChannelPublisher("rt/arm_sdk", LowCmd_)
        self.publisher.Init()

        self.subscriber = ChannelSubscriber("rt/lowstate", LowState_)
        self.subscriber.Init(self.LowStateHandler, 10)

    def Start(self):

        self.thread = RecurrentThread(
            interval=self.control_dt,
            target=self.LowCmdWrite
        )

        while not self.first_update:
            time.sleep(0.1)

        self.thread.Start()

    def LowStateHandler(self, msg):
        self.low_state = msg
        self.first_update = True

    def interpolate(self, q0, q1):
        ratio = (1 - math.cos(math.pi * (self.t / self.T))) / 2
        return q0 + (q1 - q0) * ratio

    def LowCmdWrite(self):

        if self.low_state is None:
            return

        self.low_cmd.motor_cmd[29].q = 1

        for j in self.arm_joints:

            q0 = self.low_state.motor_state[j].q
            q1 = self.target_pos.get(j, q0)

            self.low_cmd.motor_cmd[j].q = self.interpolate(q0, q1)
            self.low_cmd.motor_cmd[j].kp = self.kp
            self.low_cmd.motor_cmd[j].kd = self.kd

        self.low_cmd.crc = self.crc.Crc(self.low_cmd)
        self.publisher.Write(self.low_cmd)

        self.t += self.control_dt

    def move_to(self, updates, duration=1.25):

        self.target_pos.update(updates)
        self.T = duration
        self.t = 0

        while self.t < self.T:
            time.sleep(self.control_dt)


# =====================================
# MAIN
# =====================================
def main():

    if len(sys.argv) < 2:
        sys.exit()

    with open(ruta, 'r') as f:
        data = json.load(f)

    pasos = data.get("pasos", [])

    ChannelFactoryInitialize(0, sys.argv[1])

    arm = ArmSequence()
    arm.Init()
    arm.Start()
    time.sleep(1.0)  # dejar estabilizar

    hand = HandSequence()
    hand.wait_state()
    print("[SYSTEM] Estabilizando mano...")
    hand.apply_positions({}, duration=0.5)
    time.sleep(1.0)

    for paso in pasos:

        pos = paso.get("posiciones", {})
        dur = paso.get("duracion", 1.25)

        # =========================
        # ACCIONES
        # =========================
        if "accion" in pos:

            if pos["accion"] == "grasp":

                modo = pos.get("modo", "")
                print(f"[PLAYER] Grasp: {modo}")

                if modo == "cylinder":
                    hand.mode = "grasp"
                    hand.grasp_cylinder()

                elif modo == "parallel":
                    hand.mode = "grasp"
                    hand.grasp_parallel()

                elif modo == "precision":
                    hand.mode = "grasp"
                    hand.grasp_precision()

            elif pos["accion"] == "release":
                hand.release()

            continue

        # =========================
        # BRAZO
        # =========================
        pos_arm = {int(k): v for k,v in pos.items() if k.isdigit()}
        if pos_arm:
            arm.move_to(pos_arm, dur)

        # =========================
        # MANO
        # =========================
        pos_left = {int(k.split("_")[-1]): v for k,v in pos.items() if k.startswith("mano_izq")}
        if pos_left:
            hand.mode = "normal"
            hand.apply_positions(pos, duration=dur*1.5)

        time.sleep(dur)


if __name__ == "__main__":
    main()