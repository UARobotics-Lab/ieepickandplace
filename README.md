# Control de la Mano Robótica Dex3-1 para Manipulación e Inventario

Este repositorio contiene el software desarrollado durante el trabajo de grado **"Evaluación funcional y determinación de límites operativos de una mano robótica para aplicaciones de inventarios en el sector eléctrico y electrónico"**, realizado en la Universidad de los Andes.

El proyecto implementa rutinas de control para la mano robótica **Dex3-1** integrada al robot humanoide **Unitree G1 EDU (Aura)**, utilizando **ROS 2** y **Python**. El repositorio incluye desde movimientos básicos de los dedos hasta rutinas completas de agarre (*grasping*), manipulación y **pick-and-place**, desarrolladas para evaluar experimentalmente las capacidades funcionales de la mano robótica durante tareas de inventario y manipulación de objetos.

---

# ⚠️ Preparación del sistema y recomendaciones de seguridad

Antes de ejecutar cualquier programa de este repositorio, es indispensable preparar correctamente el sistema robótico para evitar daños en el hardware y garantizar una operación segura.

## 1. Ensamble de las manos

Las manos robóticas deben estar completamente ensambladas e instaladas sobre una **superficie rígida y estable** antes de energizar el robot. No se recomienda encender el sistema mientras las manos se encuentren desmontadas o sin soporte mecánico.

## 2. Encendido del robot

Una vez encendido el robot, las manos ejecutarán automáticamente una **rutina de inicialización definida por el fabricante**.

Durante esta rutina todos los dedos realizan movimientos automáticos de apertura y cierre. Este comportamiento es completamente normal y permite verificar que el sistema de actuadores y control se encuentra funcionando correctamente.

No interfiera con el movimiento de los dedos durante esta etapa.

## 3. Antes de ejecutar cualquier programa

Antes de enviar comandos desde este repositorio verifique que:

- Las manos hayan finalizado completamente la rutina de inicialización.
- No existan personas u objetos dentro del rango de movimiento de los dedos.
- El robot se encuentre estable y correctamente energizado.
- La comunicación entre el computador y el robot haya sido establecida correctamente.

> **Importante:** Si durante la inicialización o la ejecución de algún programa se observa un comportamiento inesperado, detenga la ejecución y apague el robot antes de realizar cualquier inspección del hardware.

---

# Contenido del repositorio

El repositorio se encuentra organizado en dos módulos principales:

- **`src/`**: contiene las rutinas básicas para el control de la mano robótica, incluyendo movimientos individuales de los dedos, posiciones básicas y funciones auxiliares utilizadas durante el desarrollo del proyecto.

- **`pick_and_place_movements/`**: contiene las rutinas de mayor nivel implementadas para la manipulación de objetos, incluyendo configuraciones de agarre, secuencias de recogida (*pick*), transporte y liberación (*place*), utilizadas durante la evaluación experimental del sistema.