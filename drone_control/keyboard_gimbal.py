import rclpy
from rclpy.node import Node
from mavros_msgs.srv import CommandLong
import sys
import select
import termios
import tty

usage_msg = """
Control Your MAVROS Gimbal!
---------------------------
Arrow Keys OR W/A/S/D to move:

       [UP] / w
[LEFT] / a    [RIGHT] / d
      [DOWN] / s

x : Center Gimbal
CTRL-C to quit
"""

def main(args=None):
    if not sys.stdin.isatty():
        print("Error: Terminal stdin is not an interactive TTY.")
        return

    settings = termios.tcgetattr(sys.stdin)
    
    rclpy.init(args=args)
    node = rclpy.create_node('keyboard_gimbal')
    cli = node.create_client(CommandLong, '/mavros/cmd/command')
    
    print("Waiting for MAVROS service to become available...")
    while not cli.wait_for_service(timeout_sec=1.0):
        pass

    pitch = 0.0
    yaw = 0.0
    step = 5.0  # Degrees per key press

    print(usage_msg)

    # This persistent buffer ensures 3-part arrow keys are never split in half
    key_buffer = ""

    try:
        tty.setraw(sys.stdin.fileno())
        sys.stdout.write(f"\rPitch: {pitch:>6.1f} | Yaw: {yaw:>6.1f}   ")
        sys.stdout.flush()

        while rclpy.ok():
            # Wait up to 0.05 seconds for keyboard input
            rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
            
            # Swallow all available characters from the terminal into our buffer
            if rlist:
                key_buffer += sys.stdin.read(1)
                while select.select([sys.stdin], [], [], 0.0)[0]:
                    key_buffer += sys.stdin.read(1)

            updated = False

            # Parse the buffer sequentially
            while len(key_buffer) > 0:
                if key_buffer.startswith('\x03'):  # CTRL-C
                    raise KeyboardInterrupt
                
                # Handle 3-part Arrow Keys
                if key_buffer.startswith('\x1b'):
                    if len(key_buffer) >= 3:
                        seq = key_buffer[:3]
                        key_buffer = key_buffer[3:]  # Remove processed sequence
                        
                        if seq in ['\x1b[A', '\x1bOA']:    # UP
                            pitch += step
                            updated = True
                        elif seq in ['\x1b[B', '\x1bOB']:  # DOWN
                            pitch -= step
                            updated = True
                        elif seq in ['\x1b[D', '\x1bOD']:  # LEFT
                            yaw -= step
                            updated = True
                        elif seq in ['\x1b[C', '\x1bOC']:  # RIGHT
                            yaw += step
                            updated = True
                    else:
                        # The arrow key sequence was cut in half by the OS!
                        # Break out and wait for the rest of it on the next loop.
                        break 
                
                # Handle Single Characters (W, A, S, D, X)
                else:
                    char = key_buffer[0]
                    key_buffer = key_buffer[1:]  # Remove processed character
                    
                    if char in ['w', 'W']:
                        pitch += step
                        updated = True
                    elif char in ['s', 'S']:
                        pitch -= step
                        updated = True
                    elif char in ['a', 'A']:
                        yaw -= step
                        updated = True
                    elif char in ['d', 'D']:
                        yaw += step
                        updated = True
                    elif char in ['x', 'X']:
                        pitch = 0.0
                        yaw = 0.0
                        updated = True

            # If any movement was registered, send the command
            if updated:
                pitch = max(-90.0, min(90.0, pitch))
                yaw = max(-180.0, min(180.0, yaw))

                sys.stdout.write(f"\rPitch: {pitch:>6.1f} | Yaw: {yaw:>6.1f}   ")
                sys.stdout.flush()

                req = CommandLong.Request()
                req.command = 205
                req.param1 = float(pitch)
                req.param2 = 0.0
                req.param3 = float(yaw)
                req.param7 = 2.0
                cli.call_async(req)

            # Spin to keep ROS 2 alive
            rclpy.spin_once(node, timeout_sec=0.01)

    except KeyboardInterrupt:
        pass
    except Exception as e:
        sys.stdout.write(f"\r\nExecution error: {e}\r\n")

    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        print("\nNode shut down cleanly.")
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
