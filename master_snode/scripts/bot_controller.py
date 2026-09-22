#!/usr/bin/env python3
"""
Bot Controller Node for Tank Cleaning Robot System
This node handles WebSocket communication with tank_snode and translates between
ROS topics and WebSocket messages.
"""

import rospy
from std_msgs.msg import String
import asyncio
import websockets
import threading
import json
from datetime import datetime
import time
import os
from dotenv import load_dotenv

# Load .env from the current catkin workspace or this repository checkout.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
load_dotenv(os.path.join(REPO_ROOT, '.env'))

class BotController:
    def __init__(self):
        rospy.init_node('bot_controller')
        
        # WebSocket configuration
        ws_host = os.getenv('TANK_WEBSOCKET_HOST', os.getenv('WEBSOCKET_HOST', 'localhost'))
        ws_port = os.getenv('WEBSOCKET_PORT', '8765')
        self.tank_websocket_uri = f"ws://{ws_host}:{ws_port}"
        
        # WebSocket connection state
        self.websocket_connection = None
        self.is_connected = False
        self.connection_established = False
        self.event_loop = None
        
        # Publishers - send responses back to master
        self.tank_response_pub = rospy.Publisher('/tank_response', String, queue_size=10)
        self.tank_status_pub = rospy.Publisher('/tank_status', String, queue_size=10)
        self.connection_status_pub = rospy.Publisher('/bot_connection', String, queue_size=10)
        
        # Subscribers - receive commands from master
        rospy.Subscriber('/bot_commands', String, self.bot_command_callback)
        
        # Connection tracking
        self.last_command = None
        self.command_history = []
        
        print("BOT CONTROLLER: WebSocket controller initialized")
        print("BOT CONTROLLER: Ready to connect to tank_snode")
        
    def bot_command_callback(self, msg):
        """Handle commands from master node"""
        command = msg.data.strip().lower()
        print(f"BOT CONTROLLER: Received command from master: {command}")
        
        if self.is_connected and self.event_loop:
            try:
                asyncio.run_coroutine_threadsafe(
                    self.send_websocket_command(command), self.event_loop
                )
            except Exception as e:
                print(f"ERROR BOT CONTROLLER: Error scheduling command: {e}")
                self.tank_response_pub.publish(f"ERROR: Failed to send command - {e}")
        else:
            print("WARNING BOT CONTROLLER: Not connected to tank - command ignored")
            self.tank_response_pub.publish("ERROR: Not connected to tank")
            
    async def send_websocket_command(self, command):
        """Send command to tank via WebSocket"""
        if not self.is_connected or not self.websocket_connection:
            print("ERROR BOT CONTROLLER: No WebSocket connection to tank")
            return None
            
        try:
            # Create JSON command message
            message = {
                "command": command,
                "timestamp": time.time(),
                "type": "command"
            }
            
            await self.websocket_connection.send(json.dumps(message))
            print(f"BOT CONTROLLER: Sent '{command}' command to tank")
            
            # Log command history
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            command_record = {
                "timestamp": timestamp,
                "command": command,
                "response": "Command sent - waiting for response"
            }
            
            self.command_history.append(command_record)
            self.last_command = command_record
            
            return {"result": "Command sent successfully"}
            
        except Exception as e:
            print(f"ERROR BOT CONTROLLER: Error sending command: {e}")
            self.is_connected = False
            self.websocket_connection = None
            self.connection_status_pub.publish("DISCONNECTED: WebSocket connection lost")
            return None
            
    async def connect_to_tank(self):
        """Establish WebSocket connection to tank_snode"""
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                print(f"BOT CONTROLLER: Connection attempt {attempt + 1}/{max_retries}")
                print("BOT CONTROLLER: Connecting to tank...")
                
                self.websocket_connection = await websockets.connect(self.tank_websocket_uri)
                self.is_connected = True
                
                print("BOT CONTROLLER: WebSocket connection established")
                print("BOT CONTROLLER: Waiting for tank initialization...")
                
                # Wait for welcome message
                welcome_msg = await self.websocket_connection.recv()
                welcome_data = json.loads(welcome_msg)
                
                if welcome_data.get("type") == "connection_established":
                    self.connection_established = True
                    tank_status = welcome_data.get("tank_status", "ready")
                    
                    print("BOT CONTROLLER: Connection fully established!")
                    print(f"BOT CONTROLLER: Tank status: {tank_status}")
                    
                    # Notify master node of successful connection
                    self.connection_status_pub.publish("CONNECTED: Tank communication ready")
                    self.tank_status_pub.publish(f"STATUS: {tank_status}")
                    
                    return True
                else:
                    print("WARNING BOT CONTROLLER: Unexpected welcome message")
                    
            except ConnectionRefusedError:
                print(f"BOT CONTROLLER: Tank not ready yet, retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            except Exception as e:
                print(f"ERROR BOT CONTROLLER: Connection error: {e}")
                await asyncio.sleep(retry_delay)
                
        print("ERROR BOT CONTROLLER: Failed to connect after all retries")
        self.connection_status_pub.publish("FAILED: Unable to connect to tank")
        return False
        
    async def listen_for_tank_responses(self):
        """Listen for responses and status updates from tank"""
        try:
            while self.is_connected and self.websocket_connection:
                try:
                    message = await asyncio.wait_for(self.websocket_connection.recv(), timeout=1.0)
                    data = json.loads(message)
                    
                    message_type = data.get("type", "unknown")
                    
                    if message_type == "status_update":
                        # Forward status updates to master
                        is_cleaning = data.get("is_cleaning", False)
                        status_msg = data.get("message", "Tank status update")
                        
                        status = "cleaning" if is_cleaning else "ready"
                        self.tank_status_pub.publish(f"STATUS: {status}")
                        
                        print(f"BOT CONTROLLER: Tank status update - {status_msg}")
                        
                    elif message_type == "command_response":
                        # Forward command responses to master
                        result = data.get('result', 'Success')
                        command = data.get('command', 'unknown')
                        success = data.get('success', True)
                        
                        print(f"BOT CONTROLLER: Tank responded to '{command}': {result}")
                        
                        # Update command history
                        if self.last_command and self.last_command['command'] == command:
                            self.last_command['response'] = data
                        
                        # Forward response to master
                        response_msg = f"RESPONSE:{command}:{result}:{'SUCCESS' if success else 'FAILED'}"
                        self.tank_response_pub.publish(response_msg)
                        
                        # Update tank status if provided
                        if 'status' in data:
                            self.tank_status_pub.publish(f"STATUS: {data['status']}")
                        
                    elif message_type == "error_response":
                        error_msg = data.get('result', 'Unknown error')
                        print(f"ERROR BOT CONTROLLER: Tank error: {error_msg}")
                        self.tank_response_pub.publish(f"ERROR: {error_msg}")
                        
                    else:
                        print(f"BOT CONTROLLER: Received message: {data.get('message', str(data))}")
                        
                except asyncio.TimeoutError:
                    continue  # Normal timeout, keep listening
                except websockets.exceptions.ConnectionClosed:
                    print("BOT CONTROLLER: Tank disconnected")
                    self.is_connected = False
                    self.connection_status_pub.publish("DISCONNECTED: Tank connection lost")
                    break
                    
        except Exception as e:
            print(f"ERROR BOT CONTROLLER: Error listening for responses: {e}")
            self.is_connected = False
            self.connection_status_pub.publish("ERROR: Connection error")
            
    async def maintain_connection(self):
        """Main connection management loop"""
        while not rospy.is_shutdown():
            if not self.is_connected:
                print("BOT CONTROLLER: Attempting to connect to tank...")
                success = await self.connect_to_tank()
                
                if success:
                    # Start listening for responses
                    listen_task = asyncio.create_task(self.listen_for_tank_responses())
                else:
                    print("BOT CONTROLLER: Connection failed, will retry...")
                    await asyncio.sleep(5)  # Wait before retry
            else:
                # Connection is active, just wait
                await asyncio.sleep(1)
                
    def run(self):
        """Start the bot controller"""
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.event_loop = loop
            
            try:
                loop.run_until_complete(self.maintain_connection())
            except Exception as e:
                print(f"ERROR BOT CONTROLLER: Async loop error: {e}")
            finally:
                if self.websocket_connection:
                    loop.run_until_complete(self.websocket_connection.close())
                loop.close()
                
        # Start async operations in separate thread
        self.async_thread = threading.Thread(target=run_async, daemon=True)
        self.async_thread.start()
        
        print("BOT CONTROLLER: WebSocket thread started")
        print("BOT CONTROLLER: Ready to receive commands from master")
        
        # Publish initial status
        self.connection_status_pub.publish("INITIALIZING: Starting bot controller")

def main():
    try:
        controller = BotController()
        controller.run()
        
        # Main ROS loop
        rate = rospy.Rate(1)  # 1 Hz status updates
        while not rospy.is_shutdown():
            # Publish connection status periodically
            if controller.is_connected:
                controller.connection_status_pub.publish("CONNECTED: Tank communication active")
            else:
                controller.connection_status_pub.publish("DISCONNECTED: No tank connection")
            
            rate.sleep()
            
    except rospy.ROSInterruptException:
        print("BOT CONTROLLER: ROS shutdown requested")
    except KeyboardInterrupt:
        print("\nBOT CONTROLLER: Keyboard interrupt received")
    except Exception as e:
        print(f"ERROR BOT CONTROLLER: Fatal error: {e}")
    finally:
        print("BOT CONTROLLER: Shutdown complete")

if __name__ == '__main__':
    main()
