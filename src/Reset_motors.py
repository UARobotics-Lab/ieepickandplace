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

    pub = ChannelPublisher("rt/dex3/left/cmd", HandCmd_)
    pub.Init()

    msg = unitree_hg_msg_dds__HandCmd_()

    print("Deshabilitando motores...")

    # =========================
    # DESHABILITAR
    # =========================
    for i in range(MOTOR_MAX):
        msg.motor_cmd[i].mode = build_mode(i, 0, 0)  # 🔥 status=0 → OFF
        msg.motor_cmd[i].kp = 0.0
        msg.motor_cmd[i].kd = 0.0
        msg.motor_cmd[i].q = 0.0
        msg.motor_cmd[i].dq = 0.0
        msg.motor_cmd[i].tau = 0.0

    # Enviar varias veces para asegurar
    for _ in range(5):
        pub.Write(msg)
        time.sleep(0.05)

    print("Motores deshabilitados ✔")


if __name__ == "__main__":
    main()
