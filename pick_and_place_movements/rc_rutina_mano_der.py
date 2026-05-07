# =====================================
# RUTA
# =====================================
ruta = "tests1.txt"

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
# HAND CONTROL (SOLO DERECHA)
# =====================================
class HandSequence:

    def __init__(self):

        # =========================
        # COMUNICACIÓN DERECHA
        # =========================
        self.pub = ChannelPublisher("rt/dex3/right/cmd", HandCmd_)
        self.pub.Init()

        self.sub = ChannelSubscriber("rt/dex3/right/state", HandState_)
        self.sub.Init(self.cb, 10)

        self.msg = unitree_hg_msg_dds__HandCmd_()

        self.state = None
        self.q = [0.0]*7
        self.mode = "normal"

        # =========================
        # CONTROL
        # =========================
        self.HOLD_KP = 0.6
        self.KP = 0.3
        self.KD = 0.05

        # 🔥 Ajustado para derecha
        self.PRESSURE_THRESHOLD = 8.02

        # =========================
        # 🔥 LIMITES CORRECTOS DERECHA
        # =========================
        self.maxLimits = [1.05, 0.742, 0.0, 1.57, 1.75, 1.57, 1.75]
        self.minLimits = [-1.05, -1.05, -1.75, 0.0, 0.0, 0.0, 0.0]

        # 🔥 DIRECCIÓN CORRECTA DERECHA
        self.CLOSE_DIR = [0, -1, -1, +1, +1, +1, +1]

    # =========================
    def cb(self, msg):
        self.state = msg

    # =========================
    def wait_state(self):
        print("[HAND RIGHT] Esperando estado...")
        while self.state is None:
            time.sleep(0.01)

        for i in range(7):
            self.q[i] = self.state.motor_state[i].q

        print("[HAND RIGHT] OK ✔")

    # =========================
    def send(self):
        for i in range(7):
            self.msg.motor_cmd[i].q = float(self.q[i])
            self.msg.motor_cmd[i].kp = self.KP
            self.msg.motor_cmd[i].kd = self.KD

        self.pub.Write(self.msg)

    # =========================
    # MOVIMIENTO SUAVE
    # =========================
    def apply_positions(self, pos_dict, duration=1.0):

        q_init = self.q.copy()
        target = self.q.copy()

        for key, val in pos_dict.items():
            if "mano_der" in key:
                idx = int(key.split("_")[-1])
                target[idx] = val

        steps = max(1, int(duration / 0.02))

        for step in range(steps):

            ratio = (1 - math.cos(math.pi * step / steps)) / 2

            for i in range(7):
                self.q[i] = q_init[i] + (target[i] - q_init[i]) * ratio

            self.send()
            time.sleep(0.02)

        self.q = target.copy()
        self.send()

    # =========================
    # PRESIÓN
    # =========================
    def get_pressure(self):

        if self.state is None:
            return 0.0

        max_p = 0.0

        for sensor in self.state.press_sensor_state:
            values = [v / 10000.0 for v in sensor.pressure]
            max_p = max(max_p, max(values))

        return max_p

    # =========================
    # GRASP CILINDRO (CORREGIDO)
    # =========================
    def grasp_cylinder(self):

        print("[HAND RIGHT] Grasp cilindro")
        self.mode = "grasp"

        targets = []

        for i in range(7):
            if i == 0:
                targets.append(self.q[i])
            else:
                targets.append(
                    self.maxLimits[i] if self.CLOSE_DIR[i] == 1 else self.minLimits[i]
                )

        contact = False

        while True:

            pressure = self.get_pressure()
            print(f"[RIGHT] Pressure: {pressure:.2f}")

            if pressure > 7.5 and not contact:
                print("Contacto detectado → apretando")
                contact = True

            if not contact:
                for i in range(1,7):
                    self.q[i] += (targets[i] - self.q[i]) * 0.05
            else:
                for i in range(1,7):
                    self.q[i] += 0.01 * self.CLOSE_DIR[i]

            self.send()
            time.sleep(0.03)

            if contact and pressure > self.PRESSURE_THRESHOLD:
                print("Agarre firme ✔")

                for i in range(7):
                    self.msg.motor_cmd[i].kp = self.HOLD_KP

                break
     # =========================
    # GRASP PARALLEL (CORREGIDO)
    # =========================
    
    def grasp_parallel(self):

        print("[HAND RIGHT] Grasp paralelo")
        self.mode = "grasp"

        THUMB_BASE = 0
        THUMB_1 = 1
        MIDDLE_BASE = 3
        INDEX_BASE = 5

        # orientación correcta
        self.q[THUMB_BASE] = 0.0
        self.send()
        time.sleep(0.3)

        targets = {}

        for i in [MIDDLE_BASE, INDEX_BASE]:
            targets[i] = self.maxLimits[i] if self.CLOSE_DIR[i] == 1 else self.minLimits[i]

        targets[THUMB_1] = self.maxLimits[THUMB_1] if self.CLOSE_DIR[THUMB_1] == 1 else self.minLimits[THUMB_1]

        contact = False

        while True:

            pressure = self.get_pressure()
            print(f"[Parallel RIGHT] Pressure: {pressure:.2f}")

            if pressure > 7.5 and not contact:
                print("Contacto paralelo → apretando")
                contact = True

            if not contact:
                for i in [MIDDLE_BASE, INDEX_BASE]:
                    self.q[i] += (targets[i] - self.q[i]) * 0.05

                self.q[THUMB_1] += (targets[THUMB_1] - self.q[THUMB_1]) * 0.05

            else:
                for i in [MIDDLE_BASE, INDEX_BASE, THUMB_1]:
                    self.q[i] += 0.01 * self.CLOSE_DIR[i]

            self.send()
            time.sleep(0.03)

            if contact and pressure > self.PRESSURE_THRESHOLD:
                print("Agarre paralelo firme ✔")

                for i in range(7):
                    self.msg.motor_cmd[i].kp = self.HOLD_KP

                break
    
     # =========================
    # GRASP PRECISION (CORREGIDO)
    # =========================

    def grasp_precision(self):

        print("[HAND RIGHT] Grasp precisión")
        self.mode = "grasp"

        THUMB_BASE = 0
        THUMB_1 = 1
        INDEX_BASE = 5

        # rotación correcta del pulgar
        self.q[THUMB_BASE] = -0.4
        self.send()
        time.sleep(0.3)

        targets = {}

        targets[INDEX_BASE] = self.maxLimits[INDEX_BASE] if self.CLOSE_DIR[INDEX_BASE] == 1 else self.minLimits[INDEX_BASE]
        targets[THUMB_1]   = self.maxLimits[THUMB_1]   if self.CLOSE_DIR[THUMB_1] == 1 else self.minLimits[THUMB_1]

        contact = False

        while True:

            pressure = self.get_pressure()
            print(f"[Precision RIGHT] Pressure: {pressure:.2f}")

            if pressure > 6.5 and not contact:
                print("Contacto pinza → apretando")
                contact = True

            if not contact:
                self.q[INDEX_BASE] += (targets[INDEX_BASE] - self.q[INDEX_BASE]) * 0.05
                self.q[THUMB_1]   += (targets[THUMB_1]   - self.q[THUMB_1]) * 0.05

            else:
                self.q[INDEX_BASE] += 0.008 * self.CLOSE_DIR[INDEX_BASE]
                self.q[THUMB_1]   += 0.008 * self.CLOSE_DIR[THUMB_1]

            self.send()
            time.sleep(0.03)

            if contact and pressure > 7.98:
                print("Pinza firme ✔")

                for i in range(7):
                    self.msg.motor_cmd[i].kp = self.HOLD_KP

                break
    # =========================
    # RELEASE
    # =========================
    def release(self):

        print("[HAND RIGHT] Release")
        self.mode = "normal"

        self.apply_positions(
            {f"mano_der_{i}": 0.0 for i in range(7)},
            duration=1.0
        )


# =====================================
# ARM CONTROL
# =====================================
class ArmSequence:

    def __init__(self):

        self.start_time = 0
        self.control_dt = 0.02

        self.crc = CRC()

        self.T = 2.0

        self.low_cmd = unitree_hg_msg_dds__LowCmd_()
        self.low_state = None
        self.first_update = False

        self.target_pos = {}
        self.q_init = {}
        self.current_q = {}

        self.arm_joints = list(range(12,29))

    def Init(self):
        self.publisher = ChannelPublisher("rt/arm_sdk", LowCmd_)
        self.publisher.Init()

        self.subscriber = ChannelSubscriber("rt/lowstate", LowState_)
        self.subscriber.Init(self.LowStateHandler, 10)

    def Start(self):
        self.thread = RecurrentThread(interval=self.control_dt, target=self.LowCmdWrite)

        while not self.first_update:
            time.sleep(0.1)

        self.thread.Start()

    def LowStateHandler(self, msg):
        self.low_state = msg
        self.first_update = True

    def interpolate(self, q0, q1):
        t = time.time() - self.start_time
        ratio = min(t / self.T, 1.0)
        ratio = (1 - math.cos(math.pi * ratio)) / 2
        return q0 + (q1 - q0) * ratio

    def LowCmdWrite(self):

        if self.low_state is None:
            return

        self.low_cmd.motor_cmd[29].q = 1

        for j in self.arm_joints:

            q0 = self.q_init.get(j, self.low_state.motor_state[j].q)
            q1 = self.target_pos.get(j, q0)

            q = self.interpolate(q0, q1)

            if j in [18, 25]:
                kp = 32.0
                kd = 4.0
            else:
                kp = 20.0
                kd = 3.5

            self.low_cmd.motor_cmd[j].q = q
            self.low_cmd.motor_cmd[j].kp = kp
            self.low_cmd.motor_cmd[j].kd = kd

            self.current_q[j] = q

        self.low_cmd.crc = self.crc.Crc(self.low_cmd)
        self.publisher.Write(self.low_cmd)

    def move_to(self, updates, duration=2.0):

        self.q_init = {
            j: self.current_q.get(j, self.low_state.motor_state[j].q)
            for j in self.arm_joints
        }

        self.target_pos = updates.copy()
        self.T = duration
        self.start_time = time.time()

        while time.time() - self.start_time < self.T:
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

    hand = HandSequence()
    hand.wait_state()

    print("[SYSTEM] Ejecución mano derecha")

    for paso in pasos:

        pos = paso.get("posiciones", {})
        dur = paso.get("duracion", 1.2)

        # =========================
        # ACCIONES (GRASP / RELEASE)
        # =========================
        if "accion" in pos:

            if pos["accion"] == "grasp":

                modo = pos.get("modo", "cylinder")
                print(f"[GRASP] modo: {modo}")

                if modo == "cylinder":
                    hand.grasp_cylinder()

                elif modo == "parallel":
                    hand.grasp_parallel()

                elif modo == "precision":
                    hand.grasp_precision()

                else:
                    print("Modo desconocido")

            elif pos["accion"] == "release":
                hand.release()

            continue  # IMPORTANTÍSIMO

        # =========================
        # BRAZO
        # =========================
        pos_arm = {int(k): v for k,v in pos.items() if k.isdigit()}
        if pos_arm:
            arm.move_to(pos_arm, dur)

        # =========================
        # MANO DERECHA
        # =========================
        pos_right = {k:v for k,v in pos.items() if "mano_der" in k}

        if pos_right and hand.mode != "grasp":
            hand.apply_positions(pos_right, duration=dur)


if __name__ == "__main__":
    main()