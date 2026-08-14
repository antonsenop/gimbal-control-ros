# Hardware Deployment Guide: SITL to Pixhawk 6X

This guide documents the transition from a simulated Gazebo environment (SITL) to a physical Hardware-In-The-Loop (HITL) or fully physical drone build using an **ArduCopter 4.6.0**, a **Pixhawk 6X**, and **MAVROS**.

---

## 1. Physical Hardware Architecture

To run ROS 2 on a physical drone, the flight controller (Pixhawk) must be paired with a Companion Computer (e.g., Raspberry Pi 4/5, Nvidia Jetson).

*   **Flight Controller:** Pixhawk 6X running ArduCopter 4.6.0 firmware.
*   **Companion Computer:** Runs Ubuntu 22.04 and ROS 2 Humble.
*   **Physical Connection:** A UART serial cable connecting the Pixhawk's `TELEM 2` port to the Companion Computer's Serial/USB port.
*   **The Bridge (MAVROS):** Replaces the `micro_ros_agent` used in simulation. MAVROS listens to the physical serial port, translates the MAVLink heartbeat, and exposes ROS 2 topics.

---

## 2. Compiling Firmware for the Pixhawk 6X

# The same ArduPilot source code used for the simulation can generate the physical firmware executables for the Pixhawk 6X. 

#On your development machine, navigate to the ArduPilot source directory:
```bash
cd ~/ardupilot_gz/ros2_ws/src/ardupilot

#Configure the build environment specifically for the Pixhawk 6X architecture:

./waf configure --board Pixhawk6X

# Compile the ArduCopter 4.6.0 firmware:
./waf copter

#  Once compilation is complete, the executable firmware file will be located at: 
#  build/Pixhawk6X/bin/arducopter.apj

# You can flash this .apj file directly to your Pixhawk 6X using Mission Planner, QGroundControl, or via command line if connected via USB:

./waf --target bin/arducopter --upload

---
## 3. Companion Computer Setup (MAVROS)

# On the physical drone's Companion Computer, you do not need to install Gazebo or the massive SITL environment. You only need standard ROS 2 Humble, MAVROS, and your custom python package.
# Install MAVROS:

sudo apt update
sudo apt install ros-humble-mavros ros-humble-mavros-extras

# Launch MAVROS (Connecting to the Pixhawk):
# Assuming your Pixhawk is connected to the Companion Computer via USB (/dev/ttyUSB0) with a baud rate of 921600:
# bash:

ros2 launch mavros apm.launch fcu_url:=serial:///dev/ttyTHS1:921600

---
## 4. Adapting the Python Node for MAVROS

# When moving from our native DDS simulation setup to a MAVROS hardware setup, the topic names and message formats change slightly.

    DDS (Simulation): Uses /ap/v1/joy with sensor_msgs/msg/Joy (Values: -1.0 to 1.0).

    MAVROS (Hardware): Uses /mavros/rc/override with mavros_msgs/msg/OverrideRCIn (Values: 1000 to 2000 PWM, where 0 means release control).

# To run the gimbal controller on physical hardware, the Python script's publisher must be updated to target MAVROS.
# Required Code Adjustments for MAVROS:
# Python: 

from mavros_msgs.msg import OverrideRCIn

# Update the publisher to target MAVROS instead of DDS

self.publisher_ = self.create_publisher(OverrideRCIn, '/mavros/rc/override', 10)

# MAVROS uses raw PWM values instead of -1.0 to 1.0

rc_msg = OverrideRCIn()
rc_msg.channels = [0] * 18  # 0 means "return control to flight controller"

# Map Gimbal Pitch (Ch 6) and Yaw (Ch 7) to standard PWM signals

rc_msg.channels[5] = 1500 + int(self.pitch * 500)  # Scales -1.0/1.0 to 1000/2000 PWM
rc_msg.channels[6] = 1500 + int(self.yaw * 500)

self.publisher_.publish(rc_msg)

# Once updated, you run this node on the Companion Computer exactly as you did in simulation:
# Bash:

ros2 run drone_control keyboard_gimbal


***

