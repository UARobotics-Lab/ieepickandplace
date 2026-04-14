# =====================================
# RUTA
# =====================================
ruta = "tests1.txt"

import sys
import time
import math
import json

from unitree_sdk2py.core.channel import ChannelPublisher, ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandCmd_, LowCmd_, LowState_
from unitree_sdk2py.idl.default import (
    unitree_hg_msg_dds__HandCmd_,
    unitree_hg_msg_dds__LowCmd_
)

from unitree_sdk2py.utils.crc import CRC
from unitree_sdk2py.utils.thread import RecurrentThread


# =====================================
# JOINT INDEX
# =====================================

class G1JointIndex:
    LeftShoulderPitch = 15
    LeftShoulderRoll = 16
    LeftShoulderYaw = 17
    LeftElbow = 18
    LeftWristRoll = 19
    LeftWristPitch = 20
    LeftWristYaw = 21

    RightShoulderPitch = 22
    RightShoulderRoll = 23
    RightShoulderYaw = 24
    RightElbow = 25
    RightWristRoll = 26
    RightWristPitch = 27
    RightWristYaw = 28

    WaistYaw = 12
    WaistRoll = 13
    WaistPitch = 14

    kNotUsedJoint = 29


# =====================================
# HAND CONTROL
# =====================================

class HandSequence:

    def __init__(self):

        self.publisher_left = ChannelPublisher("rt/dex3/left/cmd", HandCmd_)
        self.publisher_left.Init()

        self.publisher_right = ChannelPublisher("rt/dex3/right/cmd", HandCmd_)
        self.publisher_right.Init()

        self.msg_left = unitree_hg_msg_dds__HandCmd_()
        self.msg_right = unitree_hg_msg_dds__HandCmd_()

        self.num_motors = 7
        self.kp = 1.5
        self.kd = 0.2

        self._init_msg(self.msg_left)
        self._init_msg(self.msg_right)

    def _init_msg(self, msg):
        for i in range(self.num_motors):
            mode = (i & 0x0F) | ((1 & 0x07) << 4)
            msg.motor_cmd[i].mode = mode
            msg.motor_cmd[i].dq = 0
            msg.motor_cmd[i].tau = 0
            msg.motor_cmd[i].kp = self.kp
            msg.motor_cmd[i].kd = self.kd

    def send(self, posiciones, mano):

        msg = self.msg_left if mano == "left" else self.msg_right
        pub = self.publisher_left if mano == "left" else self.publisher_right

        for i in range(self.num_motors):
            msg.motor_cmd[i].q = posiciones.get(i, 0.0)

        
        pub.Write(msg)

    # RELEASE MANOS
    def release(self):

        for i in range(self.num_motors):

            # izquierda
            self.msg_left.motor_cmd[i].kp = 0.0
            self.msg_left.motor_cmd[i].kd = 0.0
            self.msg_left.motor_cmd[i].tau = 0.0

            # derecha
            self.msg_right.motor_cmd[i].kp = 0.0
            self.msg_right.motor_cmd[i].kd = 0.0
            self.msg_right.motor_cmd[i].tau = 0.0

        # enviar
        
        self.publisher_left.Write(self.msg_left)
        self.publisher_right.Write(self.msg_right)


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

            q0 = self.q_init_override.get(j, self.low_state.motor_state[j].q) if self.q_init_override else self.low_state.motor_state[j].q
            q1 = self.target_pos.get(j, q0)

            self.low_cmd.motor_cmd[j].q = self.interpolate(q0, q1)
            self.low_cmd.motor_cmd[j].dq = 0
            self.low_cmd.motor_cmd[j].tau = 0
            self.low_cmd.motor_cmd[j].kp = self.kp
            self.low_cmd.motor_cmd[j].kd = self.kd

        self.low_cmd.crc = self.crc.Crc(self.low_cmd)
        self.publisher.Write(self.low_cmd)

        self.t += self.control_dt

    def move_to(self, updates, duration=1.25, q_init_override=None):

        self.target_pos.update(updates)
        self.T = duration
        self.t = 0
        self.q_init_override = q_init_override

        while self.t < self.T:
            time.sleep(self.control_dt)

    # RELEASE BRAZO
    def freeze_and_release(self):

        for j in self.arm_joints:
            self.low_cmd.motor_cmd[j].q = self.low_state.motor_state[j].q
            self.low_cmd.motor_cmd[j].kp = 0
            self.low_cmd.motor_cmd[j].kd = 0

        self.low_cmd.motor_cmd[29].q = 0
        self.low_cmd.crc = self.crc.Crc(self.low_cmd)
        self.publisher.Write(self.low_cmd)


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

    q_prev = None

    for paso in pasos:

        pos = paso.get("posiciones", {})
        dur = paso.get("duracion", 1.25)

        # BRAZO
        pos_arm = {int(k): v for k,v in pos.items() if k.isdigit()}

        if pos_arm:
            arm.move_to(pos_arm, dur, q_prev)
            q_prev = pos_arm

        # MANO IZQUIERDA
        pos_left = {int(k.split("_")[-1]): v for k,v in pos.items() if k.startswith("mano_izq")}
        if pos_left:
            hand.send(pos_left, "left")

        # MANO DERECHA
        pos_right = {int(k.split("_")[-1]): v for k,v in pos.items() if k.startswith("mano_der")}
        if pos_right:
            hand.send(pos_right, "right")

        time.sleep(dur)

    # RELEASE TOTAL
    time.sleep(0.5)
    arm.freeze_and_release()
    hand.release()


if __name__ == "__main__":
    main()