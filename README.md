# ROS Fish Tank Cleaning Bot

ROS1 project for a Raspberry Pi + ESP32 fish tank cleaning robot. The current system focuses on tank cleaning movement, edge detection, and Pi-to-tank communication. Water pump, drain, fill, and water-change control have been removed from the active project scope.

## Architecture

The project is split into two ROS packages:

- `master_snode`: Raspberry Pi/master-side coordination, WebSocket client, and user command interface.
- `tank_snode`: tank-side communication server, cleaning decision logic, IR edge sensing, and motor command handling.

Command flow:

```text
User input
  -> /master_control
  -> master_snode/scripts/master_node.py
  -> /bot_commands
  -> master_snode/scripts/bot_controller.py
  -> WebSocket JSON
  -> tank_snode/scripts/comm_node.py
  -> /tank_control
  -> tank_snode/scripts/decision_node.py
  -> /motor_command
  -> tank_snode/scripts/motor_node.py
```

## Project Structure

```text
.
|-- master_snode/
|   |-- launch/master.launch
|   `-- scripts/
|       |-- bot_controller.py
|       |-- master_node.py
|       `-- test_user_input.py
|-- tank_snode/
|   |-- launch/tank_bot.launch
|   `-- scripts/
|       |-- comm_node.py
|       |-- decision_node.py
|       |-- ir_sensor_node.py
|       `-- motor_node.py
|-- example.env
|-- requirements.txt
`-- README.md
```

## Requirements

- ROS Noetic
- Python 3
- Catkin workspace
- Python packages from `requirements.txt`

## Setup

Clone this repository into a catkin workspace:

```bash
cd ~/catkin_ws/src
git clone https://github.com/TheLostLeo/ROS_FISHTANK_BOT.git
cd ~/catkin_ws
catkin_make
source devel/setup.bash
```

Install Python dependencies from the repository root:

```bash
python3 -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
```

Create a local environment file:

```bash
cp example.env .env
```

For same-machine testing, the default host values work. For real Pi-to-tank network use:

- On the tank side, set `WEBSOCKET_HOST=0.0.0.0`.
- On the master side, set `TANK_WEBSOCKET_HOST` to the tank device IP or hostname.
- Keep `WEBSOCKET_PORT=8765` unless you need a different port.

## Running

Start the tank-side nodes first:

```bash
roslaunch tank_snode tank_bot.launch
```

Start the master-side nodes in another terminal:

```bash
roslaunch master_snode master.launch
```

## Commands

The interactive test node supports:

```text
start          Start tank cleaning
stop           Stop tank cleaning
status         Ask the tank for current status
system_status  Show master-side system status
help           Show the command menu
quit           Exit the test program
```

The removed commands are intentionally unsupported: `drain`, `fill`, `water_change`, and `pump_stop`.

## ROS Topics

Master-side topics:

- `/master_control`: user commands into the master node.
- `/master_status`: JSON system status from the master node.
- `/master_commands`: command responses for the user interface.
- `/bot_commands`: validated tank commands from master to bot controller.
- `/tank_response`: command responses from tank to master.
- `/tank_status`: tank cleaning/ready state updates.
- `/bot_connection`: WebSocket connection status.

Tank-side topics:

- `/tank_control`: local start/stop cleaning command.
- `/edge_status`: IR edge detection state.
- `/motor_command`: movement command for the motor node.
- `/status_report`: tank status text.

## Initial ESP32 Pin Plan

No real pins were previously assigned. These are first-pass defaults and should be verified against the exact ESP32 board and motor driver before wiring:

| Signal | ESP32 GPIO | Notes |
| --- | --- | --- |
| Left motor IN1 | GPIO25 | Motor driver input |
| Left motor IN2 | GPIO26 | Motor driver input |
| Right motor IN1 | GPIO27 | Motor driver input |
| Right motor IN2 | GPIO14 | Motor driver input |
| Left IR sensor | GPIO34 | Input-only sensor pin |
| Right IR sensor | GPIO35 | Input-only sensor pin |

The current Python nodes still simulate motor and IR behavior. Add ESP32 firmware or a serial/ROS bridge before driving real hardware.

## Troubleshooting

- If the master cannot connect, start `tank_snode` first and check `WEBSOCKET_HOST`, `TANK_WEBSOCKET_HOST`, and `WEBSOCKET_PORT`.
- If `roslaunch` cannot find scripts, confirm the package is inside a sourced catkin workspace and rebuild with `catkin_make`.
- Use `rostopic list` and `rostopic echo /master_commands` to inspect command routing.

## License

MIT
