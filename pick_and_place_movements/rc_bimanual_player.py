import sys
import time
import math
import json

from unitree_sdk2py.core.channel import ChannelPublisher, ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandCmd_, HandState_, LowCmd_, LowState_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__HandCmd_, unitree_hg_msg_dds__LowCmd_

from unitree_sdk2py.utils.crc import CRC
from unitree_sdk2py.utils.thread import RecurrentThread

# =========================
# CONFIG
# =========================
ruta = "testtotal.txt"
PRESSURE_THRESHOLD = 11.0

# =========================
# HANDS (IZQ + DER)
# =========================
class Hands:

    def __init__(self):

        self.pubL = ChannelPublisher("rt/dex3/left/cmd", HandCmd_)
        self.pubR = ChannelPublisher("rt/dex3/right/cmd", HandCmd_)

        self.pubL.Init()
        self.pubR.Init()

        self.subL = ChannelSubscriber("rt/dex3/left/state", HandState_)
        self.subR = ChannelSubscriber("rt/dex3/right/state", HandState_)

        self.subL.Init(self.cbL, 10)
        self.subR.Init(self.cbR, 10)

        self.msgL = unitree_hg_msg_dds__HandCmd_()
        self.msgR = unitree_hg_msg_dds__HandCmd_()

        self.stateL = None
        self.stateR = None

        self.qL = [0]*7
        self.qR = [0]*7

        self.KP = 0.3
        self.KD = 0.05
        self.HOLD_KP = 0.6

    def cbL(self, msg): self.stateL = msg
    def cbR(self, msg): self.stateR = msg

    def wait(self):
        while self.stateL is None or self.stateR is None:
            time.sleep(0.01)

        for i in range(7):
            self.qL[i] = self.stateL.motor_state[i].q
            self.qR[i] = self.stateR.motor_state[i].q

    def send(self):

        for i in range(7):
            self.msgL.motor_cmd[i].q = self.qL[i]
            self.msgL.motor_cmd[i].kp = self.KP
            self.msgL.motor_cmd[i].kd = self.KD

            self.msgR.motor_cmd[i].q = self.qR[i]
            self.msgR.motor_cmd[i].kp = self.KP
            self.msgR.motor_cmd[i].kd = self.KD

        self.pubL.Write(self.msgL)
        self.pubR.Write(self.msgR)

    # =========================
    # POSICIONES SUAVES
    # =========================
    def move(self, pos, duration):

        qL0 = self.qL.copy()
        qR0 = self.qR.copy()

        qL1 = self.qL.copy()
        qR1 = self.qR.copy()

        for k,v in pos.items():

            if "mano_izq" in k:
                i = int(k.split("_")[-1])
                qL1[i] = v

            if "mano_der" in k:
                i = int(k.split("_")[-1])
                qR1[i] = v

        steps = int(duration/0.02)

        for s in range(steps):

            r = (1-math.cos(math.pi*s/steps))/2

            for i in range(7):
                self.qL[i] = qL0[i] + (qL1[i]-qL0[i])*r
                self.qR[i] = qR0[i] + (qR1[i]-qR0[i])*r

            self.send()
            time.sleep(0.02)

    # =========================
    # PRESIÓN
    # =========================
    def pressure(self):

        def maxp(state):
            if state is None: return 0
            p = 0
            for s in state.press_sensor_state:
                p = max(p, max([v/10000.0 for v in s.pressure]))
            return p

        return maxp(self.stateL), maxp(self.stateR)

    # =========================
    # GRASP SIMPLE
    # =========================
    def grasp(self):

        while True:

            pL, pR = self.pressure()

            # cerrar progresivo
            for i in range(1,7):
                self.qL[i] += 0.01
                self.qR[i] += 0.01

            self.send()
            time.sleep(0.02)

            # 🔥 condición OR
            if pL > PRESSURE_THRESHOLD or pR > PRESSURE_THRESHOLD:

                print(f"[GRASP OK] L:{pL:.2f} R:{pR:.2f}")

                for i in range(7):
                    self.msgL.motor_cmd[i].kp = self.HOLD_KP
                    self.msgR.motor_cmd[i].kp = self.HOLD_KP

                break

    def release(self):

        for i in range(7):
            self.qL[i] = 0
            self.qR[i] = 0

        self.send()
        time.sleep(1)


# =========================
# ARM
# =========================
class Arm:

    def __init__(self):

        self.pub = ChannelPublisher("rt/arm_sdk", LowCmd_)
        self.pub.Init()

        self.sub = ChannelSubscriber("rt/lowstate", LowState_)
        self.sub.Init(self.cb, 10)

        self.state = None
        self.first = False

        self.cmd = unitree_hg_msg_dds__LowCmd_()
        self.crc = CRC()

        self.q = {}
        self.target = {}
        self.T = 2
        self.t0 = 0

        self.joints = list(range(12,29))

    def cb(self,msg):
        self.state = msg
        self.first = True

    def start(self):

        while not self.first:
            time.sleep(0.1)

        self.thread = RecurrentThread(0.02, self.loop)
        self.thread.Start()

    def loop(self):

        if self.state is None: return

        for j in self.joints:

            q0 = self.q.get(j, self.state.motor_state[j].q)
            q1 = self.target.get(j, q0)

            t = min((time.time()-self.t0)/self.T,1)
            r = (1-math.cos(math.pi*t))/2

            q = q0 + (q1-q0)*r

            self.cmd.motor_cmd[j].q = q
            self.cmd.motor_cmd[j].kp = 20
            self.cmd.motor_cmd[j].kd = 3.5

            self.q[j] = q

        self.cmd.crc = self.crc.Crc(self.cmd)
        self.pub.Write(self.cmd)

    def move(self, pos, duration):

        self.target = pos
        self.T = duration
        self.t0 = time.time()

        time.sleep(duration)


# =========================
# MAIN
# =========================
def main():

    if len(sys.argv) < 2:
        sys.exit()

    ChannelFactoryInitialize(0, sys.argv[1])

    with open(ruta,"r") as f:
        data = json.load(f)

    pasos = data["pasos"]

    arm = Arm()
    arm.start()

    hands = Hands()
    hands.wait()

    print("🚀 Ejecutando rutina...")

    for paso in pasos:

        pos = paso["posiciones"]
        dur = paso.get("duracion",1.5)

        # =========================
        # ACCIONES
        # =========================
        if "accion" in pos:

            if pos["accion"] == "grasp":
                hands.grasp()

            elif pos["accion"] == "release":
                hands.release()

            continue

        # =========================
        # BRAZO
        # =========================
        arm_pos = {int(k):v for k,v in pos.items() if k.isdigit()}

        if arm_pos:
            arm.move(arm_pos, dur)

        # =========================
        # MANOS
        # =========================
        hands.move(pos, dur)

    print("✔ Rutina terminada")


if __name__ == "__main__":
    main()