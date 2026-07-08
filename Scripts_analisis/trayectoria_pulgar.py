import numpy as np
import matplotlib.pyplot as plt

# =====================================
# LONGITUDES
# =====================================

L1 = 45.8
L2 = 52.31

# =====================================
# ORIENTACIÓN REAL DEL PULGAR
# =====================================

phi = np.radians(55)

# =====================================
# ÁNGULOS ARTICULARES
# =====================================

theta1_vals = np.linspace(0, 90, 100)
theta2_vals = np.linspace(0, 96, 100)

# trayectoria
x_tip = []
y_tip = []

# =====================================
# FIGURA
# =====================================

plt.figure(figsize=(8,8))

# =====================================
# CINEMÁTICA
# =====================================

for i, (t1_deg, t2_deg) in enumerate(zip(theta1_vals, theta2_vals)):

    t1 = np.radians(t1_deg)
    t2 = np.radians(t2_deg)

    # articulación intermedia
    x1 = L1 * np.cos(phi + t1)
    y1 = L1 * np.sin(phi + t1)

    # punta
    x2 = x1 + L2 * np.cos(phi + t1 + t2)
    y2 = y1 + L2 * np.sin(phi + t1 + t2)

    # guardar trayectoria
    x_tip.append(x2)
    y_tip.append(y2)

    # dibujar configuraciones
    if i % 20 == 0:

        plt.plot(
            [0, x1, x2],
            [0, y1, y2],
            '-o',
            linewidth=2
        )

# =====================================
# TRAYECTORIA
# =====================================

plt.plot(
    x_tip,
    y_tip,
    linewidth=4,
    label='Trayectoria punta'
)

plt.scatter(
    x_tip[0],
    y_tip[0],
    s=120,
    label='Inicio'
)

plt.scatter(
    x_tip[-1],
    y_tip[-1],
    s=120,
    label='Final'
)

# =====================================
# ESTÉTICA
# =====================================

plt.title("Trayectoria cinemática del pulgar")

plt.xlabel("X [mm]")
plt.ylabel("Y [mm]")

plt.axis('equal')

plt.grid(True)

plt.legend()

plt.tight_layout()

plt.show()