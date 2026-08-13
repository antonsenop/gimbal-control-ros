#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from rclpy.qos import qos_profile_sensor_data
import sys
import termios
import tty
import threading

msg = """
Gimbal Keyboard Controller Active!
----------------------------------
[Up/Down Arrows]    : Pitch Up/Down
[Left/Right Arrows] : Yaw Left/Right
[ CTRL-C ]          : Quit
"""

class KeyboardGimbal(Node):
    def __init__(self):
        super().__init__('keyboard_gimbal')
        
        # FIX 1: Use SensorData QoS (Best Effort) so ArduPilot actually listens to it!
        self.publisher_ = self.create_publisher(Joy, '/ap/v1/joy', qos_profile_sensor_data)
        
        self.timer = self.create_timer(0.1, self.timer_callback)
        self.pitch = 0.0
        self.yaw = 0.0

    def timer_callback(self):
        joy_msg = Joy()
        
        # FIX 2: No more NaNs. We will send safe, explicit values.
        # Channel 3 (Index 2) is Throttle. -1.0 = 0% Throttle (1000 PWM)
        # All other flight controls are 0.0 = Centered (1500 PWM)
        joy_msg.axes = [
            0.0,   # Ch 1: Roll
            0.0,   # Ch 2: Pitch
            -1.0,  # Ch 3: Throttle (Safely at Zero)
            0.0,   # Ch 4: Yaw
            0.0,   # Ch 5: Flight Mode
            self.pitch, # Ch 6: Gimbal Pitch
            self.yaw,   # Ch 7: Gimbal Yaw
            0.0    # Ch 8: Aux
        ]
        
        self.publisher_.publish(joy_msg)

def get_key(settings):
    tty.setraw(sys.stdin.fileno())
    key = sys.stdin.read(1)
    if key == '\x1b':
        key += sys.stdin.read(2)
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key

def main(args=None):
    settings = termios.tcgetattr(sys.stdin)
    rclpy.init(args=args)
    node = KeyboardGimbal()
    print(msg)

    def keyboard_loop():
        while rclpy.ok():
            key = get_key(settings)
            
            if key == '\x1b[A':    # Up Arrow
                node.pitch += 0.05
            elif key == '\x1b[B':  # Down Arrow
                node.pitch -= 0.05
            elif key == '\x1b[C':  # Right Arrow
                node.yaw += 0.05
            elif key == '\x1b[D':  # Left Arrow
                node.yaw -= 0.05
            elif key == '\x03':    # CTRL-C
                break
            
            node.pitch = max(-1.0, min(1.0, node.pitch))
            node.yaw = max(-1.0, min(1.0, node.yaw))
            
            sys.stdout.write(f'\rPitch: {node.pitch:.2f} | Yaw: {node.yaw:.2f}     ')
            sys.stdout.flush()

    thread = threading.Thread(target=keyboard_loop)
    thread.start()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()
    thread.join()

if __name__ == '__main__':
    main()
