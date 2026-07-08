import numpy as np
import matplotlib.pyplot as plt

# =====================================
# LONGITUDES
# =====================================

L1 = 45.8
L2 = 52.31

# =====================================
# ORIENTACIÓN DEL PULGAR
# =====================================

phi = np.radians(55)

# =====================================
# RANGOS ARTICULARES
# =====================================

theta1_vals = np.linspace(0, 90, 100)
theta2_vals = np.linspace(0, 96, 100)

# workspace
x_points = []
y_points = []

# =====================================
# CALCULAR WORKSPACE
# =====================================

for t1_deg in theta1_vals:

    for t2_deg in theta2_vals:

        t1 = np.radians(t1_deg)
        t2 = np.radians(t2_deg)

        # articulación intermedia
        x1 = L1 * np.cos(phi + t1)
        y1 = L1 * np.sin(phi + t1)

        # punta
        x2 = x1 + L2 * np.cos(phi + t1 + t2)
        y2 = y1 + L2 * np.sin(phi + t1 + t2)

        x_points.append(x2)
        y_points.append(y2)

# =====================================
# GRAFICAR
# =====================================

plt.figure(figsize=(8,8))

plt.scatter(
    x_points,
    y_points,
    s=2
)

plt.title("Workspace del pulgar")

plt.xlabel("X [mm]")
plt.ylabel("Y [mm]")

plt.axis('equal')

plt.grid(True)

plt.tight_layout()

plt.show()