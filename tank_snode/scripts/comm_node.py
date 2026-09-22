#!/usr/bin/env python3
"""Communication Node for Tank Cleaning Robot
This node handles communication with the master_snode and manages tank cleaning operations.
"""
import rospy
from std_msgs.msg import String
import asyncio
import websockets
import threading
import json
import time
import os
from dotenv import load_dotenv

# Load .env from the current catkin workspace or this repository checkout.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
load_dotenv(os.path.join(REPO_ROOT, '.env'))

class CommNode:
    def __init__(self):
        # Initialize ROS node
        self.status_pub = rospy.Publisher('/status_report', String, queue_size=10)
        self.control_pub = rospy.Publisher('/tank_control', String, queue_size=10)
        self.is_cleaning = False
        self.master_connected = False
        self.websocket_connection = None
        
        print("COMM NODE: Initializing WebSocket server...")
        print("COMM NODE: Waiting for master_snode connection...")
        
    async def send_status_to_master(self, status_msg):
        """Send status updates"""
        if self.websocket_connection and self.master_connected:
            try:
                message = {
                    "type": "status_update",
                    "is_cleaning": self.is_cleaning,
                    "message": status_msg,
                    "timestamp": time.time()
                }
                await self.websocket_connection.send(json.dumps(message))
                print(f"COMM NODE: Sent status to master: {status_msg}")
            except Exception as e:
                print(f"ERROR COMM NODE: Failed to send status to master: {e}")
                self.master_connected = False
        
    def start_cleaning(self):
        """Start operation"""
        if not self.is_cleaning:
            self.is_cleaning = True
            rospy.loginfo("Received START signal - Beginning tank cleaning operation")
            self.status_pub.publish("Tank cleaning started")
            self.control_pub.publish("START_CLEANING")
            print("COMM NODE: Tank cleaning operation STARTED")
            
            return "Tank cleaning started"
        else:
            rospy.loginfo("WARNING: Tank is already cleaning")
            print("WARNING COMM NODE: Tank already in cleaning mode")
            return "Tank already running"
            
    def stop_cleaning(self):
        """Stop operation"""      
        if self.is_cleaning:
            self.is_cleaning = False
            rospy.loginfo("Received STOP signal - Stopping tank cleaning operation")
            self.status_pub.publish("Tank cleaning stopped")
            self.control_pub.publish("STOP_CLEANING")
            print("COMM NODE: Tank cleaning operation STOPPED")
            
            return "Tank cleaning stopped"
        else:
            rospy.loginfo("INFO: Tank is not currently cleaning")
            print("INFO COMM NODE: Tank not in cleaning mode")
            return "Tank is not running"

def run_comm_node(comm):
    rate = rospy.Rate(0.5) 

    while not rospy.is_shutdown():
        if comm.master_connected:
            if comm.is_cleaning:
                status_msg = "Tank is actively cleaning"
            else:
                status_msg = "Tank ready - waiting for commands"
            comm.status_pub.publish(status_msg)
        else:
            comm.status_pub.publish("Tank waiting for master connection")
            
        rate.sleep()

if __name__ == '__main__':
    comm_instance = None
    
    async def websocket_server(websocket, path):
        """Handle WebSocket connections"""
        global comm_instance
        comm = comm_instance 
        
        try:
            print("COMM NODE: Master node connected via WebSocket!")
            print("COMM NODE: Initialization complete - system ready")
            
            if comm:
                comm.master_connected = True
                comm.websocket_connection = websocket
                print(f"COMM NODE: Connected to master, current status: {'cleaning' if comm.is_cleaning else 'ready'}")

            welcome_msg = {
                "type": "connection_established",
                "message": "Tank communication node ready",
                "tank_status": "ready" if not (comm and comm.is_cleaning) else "cleaning"
            }
            await websocket.send(json.dumps(welcome_msg))
            
            async for message in websocket:
                try:
                    # JSON format
                    try:
                        msg_data = json.loads(message)
                        command = msg_data.get("command", "").lower()
                        msg_type = msg_data.get("type", "command")
                    except json.JSONDecodeError:
                        command = message.lower().strip()
                        msg_type = "command"
                    
                    print(f"COMM NODE: Received from master: {command}")
                    rospy.loginfo(f"Received WebSocket message from master: {command}")
                    
                    if command == "start":
                        if comm:
                            print(f"COMM NODE: Processing START command, current state: {'cleaning' if comm.is_cleaning else 'ready'}")
                            result_msg = comm.start_cleaning()
                            response = {
                                "type": "command_response", 
                                "command": "start",
                                "result": result_msg, 
                                "success": True,
                                "is_cleaning": comm.is_cleaning,
                                "status": "cleaning" if comm.is_cleaning else "ready"
                            }
                            print(f"COMM NODE: Sending response: {response}")
                        else:
                            print("ERROR COMM NODE: No comm instance available!")
                            response = {"type": "command_response", "command": "start", "result": "Tank communication error", "success": False}
                        await websocket.send(json.dumps(response))
                        
                    elif command == "stop":
                        if comm:
                            print(f"COMM NODE: Processing STOP command, current state: {'cleaning' if comm.is_cleaning else 'ready'}")
                            result_msg = comm.stop_cleaning()
                            response = {
                                "type": "command_response", 
                                "command": "stop",
                                "result": result_msg, 
                                "success": True,
                                "is_cleaning": comm.is_cleaning,
                                "status": "cleaning" if comm.is_cleaning else "ready"
                            }
                            print(f"COMM NODE: Sending response: {response}")
                        else:
                            print("ERROR COMM NODE: No comm instance available!")
                            response = {"type": "command_response", "command": "stop", "result": "Tank communication error", "success": False}
                        await websocket.send(json.dumps(response))
                        
                    elif command == "status":
                        if comm:
                            status = "cleaning" if comm.is_cleaning else "ready"
                            status_message = "Tank is running" if comm.is_cleaning else "Tank is ready to start"
                            response = {
                                "type": "command_response",
                                "command": "status", 
                                "status": status,
                                "is_cleaning": comm.is_cleaning,
                                "result": status_message,
                                "success": True
                            }
                            print(f"COMM NODE: Sending status response: {response}")
                        else:
                            print("ERROR COMM NODE: No comm instance available!")
                            response = {"type": "command_response", "command": "status", "result": "Tank communication error", "success": False}
                        await websocket.send(json.dumps(response))
                        
                    else:
                        response = {
                            "type": "error_response",
                            "result": "Unknown command. Use: start, stop, or status",
                            "success": False
                        }
                        await websocket.send(json.dumps(response))
                        
                except Exception as e:
                    print(f"ERROR COMM NODE: Error processing message: {e}")
                    error_response = {
                        "type": "error_response",
                        "result": f"Error processing command: {str(e)}",
                        "success": False
                    }
                    await websocket.send(json.dumps(error_response))
                    
        except websockets.exceptions.ConnectionClosed:
            print("COMM NODE: Master node disconnected")
            rospy.loginfo("Master WebSocket client disconnected")
            if comm:
                comm.master_connected = False
                comm.websocket_connection = None
        except Exception as e:
            print(f"ERROR COMM NODE: WebSocket server error: {e}")
            rospy.logerr(f"WebSocket server error: {e}")
            if comm:
                comm.master_connected = False
                comm.websocket_connection = None

    def run_websocket_server():
        """WebSocket server in background thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Get WebSocket configuration from environment variables (silently)
        ws_host = os.getenv('WEBSOCKET_HOST', 'localhost')
        ws_port = int(os.getenv('WEBSOCKET_PORT', '8765'))
        
        print("COMM NODE: Starting WebSocket server...")
        start_server = websockets.serve(websocket_server, ws_host, ws_port)
        rospy.loginfo("WebSocket server started")
        
        loop.run_until_complete(start_server)
        loop.run_forever()

    try:
        print("COMM NODE: Initializing ROS node...")
        rospy.init_node('comm_node')
        
        print("COMM NODE: Creating communication node instance...")
        
        comm_instance = CommNode()
        globals()['comm_instance'] = comm_instance  
        
        print("COMM NODE: Communication node created and ready")
        print(f"COMM NODE: Initial state - cleaning: {comm_instance.is_cleaning}")
         
        websocket_thread = threading.Thread(target=run_websocket_server, daemon=True)
        websocket_thread.start()
        
        print("COMM NODE: WebSocket server started, ready for master connection...")
        run_comm_node(comm_instance)
        
    except rospy.ROSInterruptException:
        print("COMM NODE: ROS shutdown requested")
        rospy.loginfo("COMM NODE: ROS shutdown requested")
    except KeyboardInterrupt:
        print("COMM NODE: Keyboard interrupt received")
        rospy.loginfo("COMM NODE: Keyboard interrupt received")
    except Exception as e:
        print(f"ERROR COMM NODE: Unexpected error: {e}")
        rospy.logerr(f"COMM NODE: Unexpected error: {e}")
    finally:
        print("COMM NODE: Shutting down")
        rospy.loginfo("COMM NODE: Shutting down")
