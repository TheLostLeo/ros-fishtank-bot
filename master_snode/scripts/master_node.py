#!/usr/bin/env python3
"""
Master Brain Node for Tank Cleaning Robot System
This node acts as the central coordinator that manages all subsystems through ROS topics.
It receives user commands and coordinates tank cleaning operations.
"""

import rospy
from std_msgs.msg import String
import json
from datetime import datetime

class MasterBrain:
    def __init__(self):
        rospy.init_node('master_brain')
        
        # Publishers - send commands to subsystems
        self.bot_command_pub = rospy.Publisher('/bot_commands', String, queue_size=10)
        self.system_status_pub = rospy.Publisher('/master_status', String, queue_size=10)
        self.master_response_pub = rospy.Publisher('/master_commands', String, queue_size=10)
        
        # Subscribers - receive status from subsystems and user commands
        rospy.Subscriber('/master_control', String, self.user_command_callback)
        rospy.Subscriber('/tank_response', String, self.tank_response_callback)
        rospy.Subscriber('/tank_status', String, self.tank_status_callback)
        rospy.Subscriber('/bot_connection', String, self.bot_connection_callback)
        
        # System state variables
        self.bot_connected = False
        self.tank_status = "unknown"
        self.tank_is_cleaning = False
        
        # Command history and coordination
        self.last_user_command = None
        self.command_history = []
        
        print("MASTER: Central coordinator initialized")
        print("MASTER: Managing tank communication and user interface")
        rospy.loginfo("Master Node started - coordinating all subsystems")

    def user_command_callback(self, msg):
        """Handle commands from user interface (test_user_input.py)"""
        command = msg.data.strip().upper()
        print(f"MASTER: Received user command: {command}")
        
        # Log command
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.last_user_command = {
            "command": command,
            "timestamp": timestamp,
            "status": "processing"
        }
        self.command_history.append(self.last_user_command)
        
        # Process user commands
        if command in ["START", "STOP", "STATUS"]:
            self.handle_tank_command(command)
        elif command == "SYSTEM_STATUS":
            self.publish_system_status(print_status=True)  # Print when user requests it
        else:
            print(f"MASTER: Unknown command: {command}")
            self.master_response_pub.publish(f"ERROR: Unknown command '{command}'")
            
    def handle_tank_command(self, command):
        """Handle tank cleaning related commands"""
        print(f"MASTER: Processing tank command: {command}")
        
        if not self.bot_connected:
            print("MASTER: Bot controller not connected - cannot execute tank command")
            self.master_response_pub.publish("ERROR: Tank not connected")
            return
            
        if command == "START":
            if self.tank_is_cleaning:
                self.master_response_pub.publish("TANK_RESPONSE: Bot already running")
            else:
                print("MASTER: Sending START command to tank")
                self.bot_command_pub.publish("start")
        elif command == "STOP":
            if not self.tank_is_cleaning:
                self.master_response_pub.publish("TANK_RESPONSE: Bot is not running")
            else:
                print("MASTER: Sending STOP command to tank")
                self.bot_command_pub.publish("stop")
        elif command == "STATUS":
            print("MASTER: Requesting tank status")
            self.bot_command_pub.publish("status")
            
    def tank_response_callback(self, msg):
        """Handle responses from tank via bot controller"""
        response = msg.data
        print(f"MASTER: Tank response: {response}")
        
        # Parse response format: "RESPONSE:command:result:status"
        if response.startswith("RESPONSE:"):
            parts = response.split(":", 3)
            if len(parts) >= 4:
                _, command, result, status = parts
                
                if command == "start":
                    if "already" in result.lower():
                        self.master_response_pub.publish("TANK_RESPONSE: Bot already running")
                    else:
                        self.master_response_pub.publish("TANK_RESPONSE: Bot is running")
                elif command == "stop":
                    if "not running" in result.lower():
                        self.master_response_pub.publish("TANK_RESPONSE: Bot is not running")
                    else:
                        self.master_response_pub.publish("TANK_RESPONSE: Bot stopped")
                elif command == "status":
                    self.master_response_pub.publish(f"TANK_RESPONSE: {result}")
        elif response.startswith("ERROR:"):
            self.master_response_pub.publish(f"TANK_RESPONSE: {response}")
            
    def tank_status_callback(self, msg):
        """Handle tank status updates"""
        status_msg = msg.data
        
        if status_msg.startswith("STATUS:"):
            status = status_msg.replace("STATUS:", "").strip()
            
            # Update tank state
            prev_cleaning = self.tank_is_cleaning
            self.tank_status = status
            self.tank_is_cleaning = (status == "cleaning")
            
            if prev_cleaning != self.tank_is_cleaning:
                print(f"MASTER: Tank cleaning state changed: {status}")
                
    def bot_connection_callback(self, msg):
        """Handle bot controller connection status"""
        connection_msg = msg.data
        
        if connection_msg.startswith("CONNECTED:"):
            if not self.bot_connected:
                self.bot_connected = True
                print("MASTER: Bot controller connected to tank")
        elif connection_msg.startswith("DISCONNECTED:") or connection_msg.startswith("FAILED:"):
            if self.bot_connected:
                self.bot_connected = False
                print("MASTER: Bot controller disconnected from tank")

    def publish_system_status(self, print_status=False):
        """Publish comprehensive system status"""
        system_status = {
            "bot_connected": self.bot_connected,
            "connected_to_tank": self.bot_connected,
            "connection_established": self.bot_connected,
            "tank_status": self.tank_status,
            "tank_is_cleaning": self.tank_is_cleaning,
            "last_command": self.last_user_command,
            "total_commands": len(self.command_history)
        }
        
        self.system_status_pub.publish(json.dumps(system_status))
        
        # Only print status when explicitly requested
        if print_status:
            print(f"MASTER: System status - Tank:{self.tank_status}, Connected:{self.bot_connected}")

def main():
    try:
        master = MasterBrain()

        print("MASTER: System coordination active")
        print("MASTER: Ready to receive user commands via /master_control")
        print("MASTER: Monitoring all subsystem status")

        # Main coordination loop
        rate = rospy.Rate(1)  # 1 Hz system monitoring
        while not rospy.is_shutdown():
            master.publish_system_status()  # Don't print - just publish to ROS topics
            rate.sleep()
            
    except rospy.ROSInterruptException:
        print("MASTER: ROS shutdown requested")
    except KeyboardInterrupt:
        print("\nMASTER: Keyboard interrupt received")
    except Exception as e:
        print(f"ERROR MASTER: Fatal error: {e}")
    finally:
        print("MASTER: Shutdown complete")

if __name__ == '__main__':
    main()
