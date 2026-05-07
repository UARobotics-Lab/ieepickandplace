import sys
import time

from unitree_sdk2py.core.channel import ChannelPublisher, ChannelFactoryInitialize
from unitree_sdk2py.idl.unitree_hg.msg.dds_ import HandCmd_
from unitree_sdk2py.idl.default import unitree_hg_msg_dds__HandCmd_

# =========================
# CONFIG
# =========================
MOTOR_MAX = 7

def build_mode(motor_id, status=0, timeout=0):
    return (motor_id & 0x0F) | ((status & 0x07) << 4) | ((timeout & 0x01) << 7)

# =========================
# MAIN
# =========================
def main():

    if len(sys.argv) < 2:
        print("Uso: python3 disable_hand.py <iface>")
        sys.exit()

    # Inicializar comunicación
    ChannelFactoryInitialize(0, sys.argv[1])

    # 🔥 LEFT
    pub_left = ChannelPublisher("rt/dex3/left/cmd", HandCmd_)
    pub_left.Init()

    # 🔥 RIGHT
    pub_right = ChannelPublisher("rt/dex3/right/cmd", HandCmd_)
    pub_right.Init()

    msg_left = unitree_hg_msg_dds__HandCmd_()
    msg_right = unitree_hg_msg_dds__HandCmd_()

    print("Deshabilitando motores (izq + der)...")

    # =========================
    # CONFIGURAR MENSAJE OFF
    # =========================
    for i in range(MOTOR_MAX):

        # LEFT
        msg_left.motor_cmd[i].mode = build_mode(i, 0, 0)
        msg_left.motor_cmd[i].kp = 0.0
        msg_left.motor_cmd[i].kd = 0.0
        msg_left.motor_cmd[i].q = 0.0
        msg_left.motor_cmd[i].dq = 0.0
        msg_left.motor_cmd[i].tau = 0.0

        # RIGHT
        msg_right.motor_cmd[i].mode = build_mode(i, 0, 0)
        msg_right.motor_cmd[i].kp = 0.0
        msg_right.motor_cmd[i].kd = 0.0
        msg_right.motor_cmd[i].q = 0.0
        msg_right.motor_cmd[i].dq = 0.0
        msg_right.motor_cmd[i].tau = 0.0

    # =========================
    # ENVIAR
    # =========================
    for _ in range(5):
        pub_left.Write(msg_left)
        pub_right.Write(msg_right)
        time.sleep(0.05)

    print("Motores deshabilitados (izq + der) ✔")


if __name__ == "__main__":
    main()
