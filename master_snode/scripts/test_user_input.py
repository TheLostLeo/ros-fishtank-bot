#!/usr/bin/env python3
"""
Interactive Test Script for Tank Cleaning Robot
This script allows users to send commands to the master_node via ROS topics
"""

import rospy
from std_msgs.msg import String
import sys
import time

class TankTestController:
    def __init__(self):
        rospy.init_node('tank_test_controller')
        
        # Publisher to send commands to master_node
        self.command_pub = rospy.Publisher('/master_control', String, queue_size=10)
        
        # Subscribe to master status and responses
        rospy.Subscriber('/master_status', String, self.status_callback)
        rospy.Subscriber('/master_commands', String, self.command_response_callback)
        
        self.last_status = None
        self.last_response = None
        self.status_requested = False
        
        print("Tank Test Controller initialized")
        print("Connected to master_node via ROS topics")
        
    def status_callback(self, msg):
        """Handle status updates from master_node"""
        self.last_status = msg.data
        
        # Only print status if user specifically requested it
        if self.status_requested:
            self.show_tank_status()
            self.status_requested = False
        
    def command_response_callback(self, msg):
        """Handle command responses from master_node"""
        self.last_response = msg.data
        # Only show meaningful responses, filter out the "TANK_RESPONSE:" prefix
        response_text = msg.data.replace("TANK_RESPONSE: ", "")
        print(f"Tank Response: {response_text}")
        
    def show_tank_status(self):
        """Display the tank status in a user-friendly format"""
        if not self.last_status:
            print("No status information available yet")
            return
            
        try:
            import json
            status_data = json.loads(self.last_status)
            
            print("\n" + "="*50)
            print("        TANK SYSTEM STATUS REPORT")
            print("="*50)
            
            # Connection status
            if status_data.get("connected_to_tank", False):
                print("Connection to Tank:       CONNECTED")
            else:
                print("Connection to Tank:       DISCONNECTED")
                
            if status_data.get("connection_established", False):
                print("Initialization:          COMPLETE")
            else:
                print("Initialization:          PENDING")
            
            # Tank operation status
            tank_status = status_data.get("tank_status", "unknown")
            is_cleaning = status_data.get("tank_is_cleaning", False)
            
            if is_cleaning:
                print("Tank Operation:          BOT IS RUNNING")
            elif tank_status == "ready":
                print("Tank Operation:          BOT IS READY TO START")
            else:
                print(f"Tank Operation:          {tank_status.upper()}")
            
            # Command information
            total_commands = status_data.get("total_commands_sent", 0)
            print(f"Total Commands Sent:     {total_commands}")
            
            last_command = status_data.get("last_command")
            if last_command:
                print(f"Last Command:            {last_command.get('command', 'N/A').upper()}")
                print(f"Last Command Time:       {last_command.get('timestamp', 'N/A')}")
            else:
                print("Last Command:            None")
            
            print("="*50)
            
        except json.JSONDecodeError:
            print(f"Status (raw): {self.last_status}")
        except Exception as e:
            print(f"Error displaying status: {e}")
            print(f"Raw status: {self.last_status}")
        
    def send_command(self, command):
        """Send command to master_node"""
        print(f"\nSending command: '{command}' to master_node...")
        self.command_pub.publish(command)
        
        # Wait a moment for response
        time.sleep(1)
        
    def show_menu(self):
        """Display the interactive menu"""
        print("Available Commands:")
        print("  1. start         - Start tank cleaning operation")
        print("  2. stop          - Stop tank cleaning operation") 
        print("  3. status        - Get current tank status")
        print("  4. system_status - Get complete system status")
        print("  5. help          - Show this menu")
        print("  6. quit          - Exit test program")
        
    def run_interactive_test(self):
        """Run the interactive test interface"""
        print("\nStarting Interactive Test Mode...")
        print("Type commands to control the tank cleaning robot")
        
        self.show_menu()
        
        while not rospy.is_shutdown():
            try:
                user_input = input("\nEnter command (or 'help' for menu): ").strip().lower()
                
                if user_input in ['quit', 'exit', 'q', '6']:
                    print("Exiting test controller...")
                    break
                    
                elif user_input in ['help', 'h', '5']:
                    self.show_menu()
                    
                # Tank controls
                elif user_input in ['start', '1']:
                    print("\nStarting tank cleaning operation...")
                    self.send_command('start')
                    
                elif user_input in ['stop', '2']:
                    print("\nStopping tank cleaning operation...")
                    self.send_command('stop')
                    
                elif user_input in ['status', '3']:
                    print("\nRequesting tank status...")
                    self.status_requested = True  # Flag to show status when received
                    self.send_command('status')
                    
                # System controls
                elif user_input in ['system_status', '4']:
                    print("\nRequesting complete system status...")
                    self.status_requested = True
                    self.send_command('system_status')
                    
                elif user_input == '':
                    continue  # Skip empty input
                    
                else:
                    print(f"Unknown command: '{user_input}'")
                    print("Type 'help' to see available commands")
                    
            except KeyboardInterrupt:
                print("\nReceived Ctrl+C, exiting...")
                break
            except EOFError:
                print("\nReceived EOF, exiting...")
                break
                
    def run_automated_test(self):
        """Run a sequence of automated tests"""
        print("\nRunning Automated Test Sequence...")
        print("This will demonstrate various tank operations")
        
        test_sequence = [
            ("Getting initial status", "status"),
            ("Starting cleaning operation", "start"),
            ("Checking status during cleaning", "status"),
            ("Stopping cleaning operation", "stop"),
            ("Getting final status", "status")
        ]
        
        for description, command in test_sequence:
            print(f"\nTest: {description}")
            print("-" * 40)
            if command == "status":
                self.status_requested = True  # Flag to show status when received
            self.send_command(command)
            time.sleep(3)  # Wait between commands
            
        print("\nAutomated test sequence completed!")

def main():    
    try:
        controller = TankTestController()
        
        # Wait a moment for ROS to initialize
        time.sleep(1)
        
        if len(sys.argv) > 1:
            # Command line mode - filter out ROS arguments
            args = [arg for arg in sys.argv[1:] if not arg.startswith('__')]
            if args:
                command = args[0].lower()
                if command in ['start', 'stop', 'status', 'system_status']:
                    print(f"Command line mode: sending '{command}'")
                    if command in ['status', 'system_status']:
                        controller.status_requested = True  # Flag to show status when received
                    controller.send_command(command)
                elif command == 'auto':
                    controller.run_automated_test()
                else:
                    print(f"Invalid command: {command}")
                    print("Valid commands: start, stop, status, system_status, auto")
            else:
                # No valid arguments, go to interactive mode
                controller.run_interactive_test()
        else:
            # Interactive mode
            controller.run_interactive_test()
            
    except rospy.ROSInterruptException:
        print("ROS shutdown requested")
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Tank test controller shutdown complete")

if __name__ == '__main__':
    main()
