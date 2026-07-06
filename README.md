| Información | Detalle |
|-------------|---------|
| Proyecto | Evaluación funcional y determinación de límites operativos de una mano robótica para aplicaciones de inventarios en el sector eléctrico y electrónico |
| Plataforma | Unitree G1 EDU (Aura) |
| Mano robótica | Dex3-1 |
| Lenguaje | Python |
| Universidad | Universidad de los Andes |
| Autora | Laura Andrea Hurtado Acosta |

# Control de la Mano Robótica Dex3-1 para Manipulación e Inventario

Este repositorio contiene el software desarrollado durante el trabajo de grado **"Evaluación funcional y determinación de límites operativos de una mano robótica para aplicaciones de inventarios en el sector eléctrico y electrónico"**, realizado en la Universidad de los Andes.

El proyecto implementa rutinas de control para la mano robótica **Dex3-1** integrada al robot humanoide **Unitree G1 EDU (Aura)**, utilizando **Python**. El repositorio incluye desde movimientos básicos de los dedos hasta rutinas completas de agarre (*grasping*), manipulación y **pick-and-place**, desarrolladas para evaluar experimentalmente las capacidades funcionales de la mano robótica durante tareas de inventario y manipulación de objetos.

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

## 4. Supervisión durante la puesta en marcha

Si es la primera vez que se utiliza este sistema, o si se van a realizar modificaciones en el hardware o en la configuración del robot, se recomienda realizar la puesta en marcha bajo la supervisión del líder o responsable del laboratorio.

Durante el desarrollo de este proyecto, el apoyo técnico y la supervisión del sistema fueron realizados por **Álvaro Uriel Achury Florian**, líder del laboratorio, quien cuenta con la experiencia necesaria para la operación segura del robot y sus componentes.

En caso de dudas sobre el estado del sistema, el procedimiento de inicialización o el funcionamiento del hardware, se recomienda solicitar el acompañamiento del responsable del laboratorio antes de continuar con la ejecución de las pruebas.

---

# Contenido del repositorio

El repositorio se encuentra organizado en dos módulos principales:

- **`src/`**: contiene las rutinas básicas para el control de la mano robótica, incluyendo movimientos individuales de los dedos, posiciones básicas y funciones auxiliares utilizadas durante el desarrollo del proyecto. Asi como la lectura inicial de los sensores que posee cada mano.

- **`pick_and_place_movements/`**: contiene las rutinas de mayor nivel implementadas para la manipulación de objetos, incluyendo configuraciones de agarre, secuencias de recogida (*pick*), transporte y liberación (*place*), utilizadas durante la evaluación experimental del sistema.

## Requisitos

### Hardware

- Robot Unitree G1 EDU
- Mano robótica Dex3-1
- Computador con Ubuntu
- Conexión Ethernet entre el computador y el robot

### Software

- Python 3
- Unitree SDK2 para Python
- Dependencias del SDK

## Conexión con el robot

Todos los programas de este repositorio establecen comunicación directa con la mano robótica mediante el Unitree SDK2 utilizando DDS.

Al ejecutar cualquier script se solicitará el nombre de la interfaz de red conectada al robot, por ejemplo:

```text
Network interface (eth0/enp...):
```

Debe ingresarse la interfaz Ethernet correspondiente a la conexión física entre el computador y el robot.

## Estructura del repositorio

El software desarrollado durante este proyecto se encuentra organizado en dos módulos principales, siguiendo las diferentes etapas del trabajo de investigación.


### `src/`

Esta carpeta contiene el desarrollo base del proyecto. Aquí se implementaron las primeras rutinas necesarias para comprender el funcionamiento de la mano robótica Dex3-1 y establecer la comunicación con el sistema.

Incluye funcionalidades como:

- Movimientos básicos de los dedos.
- Pruebas individuales de articulaciones.
- Lectura de sensores táctiles.
- Consulta de atributos disponibles del SDK.
- Reinicio de motores.
- Rutinas iniciales de validación del movimiento.

Estas rutinas sirvieron como base para el desarrollo de los experimentos posteriores.

---

### `pick_and_place_movements/`


Esta carpeta contiene las herramientas desarrolladas para implementar tareas de manipulación mediante captura y reproducción de movimientos.

La metodología consiste en registrar una secuencia de movimiento realizada con el robot (brazos, cintura y manos), almacenarla en archivos de trayectoria y posteriormente reproducirla para ejecutar tareas repetitivas de manipulación.

Las trayectorias capturadas no incluyen movimientos de locomoción; únicamente consideran los grados de libertad correspondientes a las extremidades superiores del robot.

A partir de estas capturas se desarrollaron las rutinas experimentales utilizadas para la evaluación de agarres y tareas de *pick and place*.

1. Encender robot
        │
        ▼
2. Ejecutar Captura_posiciones.py
        │
        ▼
3. Mover el robot manualmente
        │
        ▼
4. Guardar trayectoria (.txt)
        │
        ▼
5. Ejecutar rc_bimanual_player.py
        │
        ▼
6. Reproducir movimiento
        │
        ▼
7. Construir rutina de agarre
        │
        ▼
8. Ejecutar validación

---

### `data_tests/`

Esta carpeta contiene los conjuntos de datos (*datasets*) generados durante el desarrollo y la validación experimental del proyecto.

Los archivos almacenados corresponden principalmente a datos en formato **CSV**, obtenidos a partir de la lectura de los sensores de la mano robótica y del registro de diferentes variables durante la ejecución de las pruebas experimentales.

Estos datos fueron utilizados para:

- Evaluar el comportamiento de los sensores táctiles durante las tareas de manipulación.
- Analizar la respuesta de la mano robótica bajo diferentes configuraciones de agarre.
- Caracterizar el desempeño del sistema frente a objetos con distintas geometrías, masas y condiciones de contacto.
- Calcular las métricas experimentales empleadas en el trabajo de grado.
- Generar las figuras, tablas y resultados presentados en el informe de investigación.

La carpeta constituye el respaldo de los datos experimentales obtenidos durante el proyecto y permite reproducir los análisis realizados a partir de las mediciones registradas.