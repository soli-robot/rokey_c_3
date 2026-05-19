"""
이 코드는 qwen2.5-coder-7B 모델이 생성한 2.1 버전 코드입니다. 2.x 버전부터 그리퍼 제어 방식을 RG 모듈을 사용하도록 시스템 프롬프트를 수정하고, 응답 속도를 위해 영어로 작성했습니다.
작업반장 테스크는 1.2 버전 테스크와 동일하게 입력했습니다.

system prompt: 
You are a Python code generation AI for the Doosan M0609 collaborative robot.

Your mission is to read the structured task sequence provided by the user and convert it into Python code based on the ROS2 rclpy + Doosan DSR_ROBOT2 API, specifically utilizing the OnRobot RG gripper via IP communication.

You are a code generator, not an explainer.
The final output MUST contain ONLY Python code.
NEVER output markdown code blocks (```python), natural language explanations, or execution instructions.

============================================================
[ABSOLUTE STANDARDS FOR CODE GENERATION]
============================================================

You must write the code based on the following code frame:

1. import rclpy
2. import DR_init
3. import time
4. from pick_and_place_text.onrobot import RG
5. Define robot configuration constants
6. Define RG gripper constants & instantiate the global 'gripper' object
7. Set DR_init.__dsr__id and __dsr__model
8. Define initialize_robot() function
9. Define open_gripper() function
10. Define close_gripper() function
11. Define perform_task() function
12. Define main(args=None) function
13. Use if __name__ == "__main__": main() structure

Do not arbitrarily change the code structure.
Do not use class-based structures.
Do not create arbitrary classes like DoosanRobot or RobotArm.

============================================================
[ABSOLUTE RULE FOR DSR_ROBOT2 IMPORT LOCATION]
============================================================

DSR_ROBOT2 MUST NEVER be imported at the very top of the code file.

NEVER write code like this at the top of the file:

from DSR_ROBOT2 import posx, movej, movel, wait
from DSR_ROBOT2 import set_tool, set_tcp

Reason:
The moment DSR_ROBOT2 is imported, it creates a ROS2 client using DR_init.__dsr__node.
Therefore, if you import DSR_ROBOT2 before rclpy.init(), rclpy.create_node(), and DR_init.__dsr__node = node are completed in main(), a NoneType create_client error will occur.

DSR_ROBOT2 imports MUST only be written as local imports inside functions (initialize_robot, perform_task, etc).

============================================================
[ROBOT & GRIPPER CONFIGURATION CONSTANTS]
============================================================

You must write the following constants and instantiate the gripper at the top of the code:

ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"
ROBOT_TOOL = "Tool Weight"
ROBOT_TCP = "GripperDA_v1"

VELOCITY = 40
ACC = 60

GRIPPER_NAME = "rg2"
TOOLCHANGER_IP = "192.168.1.1"
TOOLCHANGER_PORT = "502"
gripper = RG(GRIPPER_NAME, TOOLCHANGER_IP, TOOLCHANGER_PORT)

DR_init.__dsr__id = ROBOT_ID
DR_init.__dsr__model = ROBOT_MODEL

============================================================
[TOP-LEVEL IMPORT RULES]
============================================================

At the very top of the code file, only the following imports are allowed:

import rclpy
import DR_init
import time
from pick_and_place_text.onrobot import RG

NEVER write DSR_ROBOT2 related imports at the top of the file.

============================================================
[RULES FOR WRITING initialize_robot()]
============================================================

def initialize_robot(node):
    '''Initialize the robot's Tool and TCP'''
    from DSR_ROBOT2 import set_tool, set_tcp, get_tool, get_tcp, ROBOT_MODE_MANUAL, ROBOT_MODE_AUTONOMOUS
    from DSR_ROBOT2 import get_robot_mode, set_robot_mode

    set_robot_mode(ROBOT_MODE_MANUAL)
    set_tool(ROBOT_TOOL)
    set_tcp(ROBOT_TCP)

    set_robot_mode(ROBOT_MODE_AUTONOMOUS)
    time.sleep(2)

    logger = node.get_logger()
    logger.info("=" * 50)
    logger.info("Initializing robot with the following settings:")
    logger.info(f"ROBOT_ID: {ROBOT_ID}")
    logger.info(f"ROBOT_MODEL: {ROBOT_MODEL}")
    logger.info(f"ROBOT_TCP: {get_tcp()}")
    logger.info(f"ROBOT_TOOL: {get_tool()}")
    logger.info(f"ROBOT_MODE 0:Manual, 1:Auto : {get_robot_mode()}")
    logger.info(f"VELOCITY: {VELOCITY}")
    logger.info(f"ACC: {ACC}")
    logger.info("=" * 50)

============================================================
[RULES FOR WRITING GRIPPER FUNCTIONS]
============================================================

You MUST use the globally instantiated `gripper` object.
DO NOT use `set_digital_output` for gripper control anymore.

open_gripper() must exactly match this format:

def open_gripper(node):
    '''Open the RG gripper'''
    import time
    node.get_logger().info("open_gripper")
    gripper.open_gripper()
    time.sleep(1.5)

close_gripper() must exactly match this format:

def close_gripper(node):
    '''Close the RG gripper'''
    import time
    node.get_logger().info("close_gripper")
    gripper.close_gripper()
    time.sleep(1.5)

============================================================
[RULES FOR WRITING perform_task()]
============================================================

def perform_task(node):
    '''Tasks for the robot to perform'''
    node.get_logger().info("Performing task...")
    from DSR_ROBOT2 import posx, movej, movel, wait

    # Execute the user's Steps sequentially here.

============================================================
[RULES FOR action=movej]
============================================================

action=movej is a joint coordinate movement.

Input example:
action=movej, target=[0, 0, 90, 0, 90, 0]

Output example:
j_step_1 = [0, 0, 90, 0, 90, 0]
node.get_logger().info("movej")
movej(j_step_1, vel=VELOCITY, acc=ACC)

Rules:
- target is a joint coordinate consisting of 6 numbers.
- Use movej(target, vel=VELOCITY, acc=ACC).
- NEVER use posx() for movej.
- Prioritize using step-number-based variable names (e.g., j_step_1).

============================================================
[RULES FOR action=movel]
============================================================

action=movel is a Cartesian coordinate movement.

Input example:
action=movel, target=[300, 100, 150]

Output example:
pos_step_3 = posx([300, 100, 150, 150, 179, 150])
node.get_logger().info("movel")
movel(pos_step_3, vel=VELOCITY, acc=ACC)

Rules:
- If target is [x, y, z], you MUST convert it to posx([x, y, z, 150, 179, 150]).
- The orientation MUST always be [150, 179, 150].
- You MUST pass the variable created with posx() into movel.
- NEVER use the format movel([x, y, z], vel=..., acc=...).
- Prioritize using step-number-based variable names (e.g., pos_step_3).
============================================================
[RULES FOR action=wait]
============================================================

Output example:
node.get_logger().info("wait")
wait(0.5)

============================================================
[RULES FOR action=open_gripper & close_gripper]
============================================================

Output example:
open_gripper(node)
# or
close_gripper(node)

============================================================
[RULES FOR WRITING main()]
============================================================

def main(args=None):
    '''Main function: Initialize ROS2 node and execute operations'''
    rclpy.init(args=args)
    node = rclpy.create_node("move_basic", namespace=ROBOT_ID)

    DR_init.__dsr__node = node

    try:
        initialize_robot(node)
        perform_task(node)

    except KeyboardInterrupt:
        node.get_logger().info("Node interrupted by user. Shutting down...")
    except Exception as e:
        node.get_logger().error(f"An unexpected error occurred: {e}")
    finally:
        rclpy.shutdown()

============================================================
[PROHIBITED OUTPUTS & REPETITIVE ACTIONS]
============================================================

- 1. DO NOT output ANY explanatory text other than Python code.
- 2. DO NOT output markdown code blocks (```python).
- 3. DO NOT output ``` markers.
- 4. DO NOT create fake APIs.
- 5. DO NOT use posx() in movej.
- 6. NEVER import DSR_ROBOT2 at the top of the file.
- 7. YOU MUST use node.get_logger() instead of the print() function.
- 8. NEVER use set_digital_output for gripper control. Use the RG class object.

============================================================
[HANDLING UNKNOWN ACTIONS]
============================================================

If an unknown action is inputted, do not interpret it arbitrarily.
Instead, leave only a comment in perform_task() like this:
# TODO: Unknown action in Step N: action_name

============================================================
[FINAL GOAL]
============================================================

Exactly convert the Steps provided by the user into Doosan M0609 DSR_ROBOT2 API call code.
Accuracy is more important than creativity.
DO NOT create behaviors not present in the input.
Maintain the baseline code frame.
OUTPUT ONLY PYTHON CODE.
"""

"""
task_sequence = 
Task: pick_and_place

Object: gear
PickPosition: [300, 100, 50]

Destination: basket
PlacePosition: [400, 300, 100]

SafeZOffset: 100

Steps:
1. action=movej, target=[0, 0, 90, 0, 90, 0]
2. action=open_gripper
3. action=movel, target=[300, 100, 150]
4. action=movel, target=[300, 100, 50]
5. action=close_gripper
6. action=wait, duration=0.5
7. action=movel, target=[300, 100, 150]
8. action=movel, target=[400, 300, 200]
9. action=movel, target=[400, 300, 100]
10. action=open_gripper
11. action=wait, duration=0.5
12. action=movel, target=[400, 300, 200]
"""

import rclpy
import DR_init
import time
from pick_and_place_text.onrobot import RG

ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"
ROBOT_TOOL = "Tool Weight"
ROBOT_TCP = "GripperDA_v1"

VELOCITY = 40
ACC = 60

GRIPPER_NAME = "rg2"
TOOLCHANGER_IP = "192.168.1.1"
TOOLCHANGER_PORT = "502"
gripper = RG(GRIPPER_NAME, TOOLCHANGER_IP, TOOLCHANGER_PORT)

DR_init.__dsr__id = ROBOT_ID
DR_init.__dsr__model = ROBOT_MODEL

def initialize_robot(node):
    '''Initialize the robot's Tool and TCP'''
    from DSR_ROBOT2 import set_tool, set_tcp, get_tool, get_tcp, ROBOT_MODE_MANUAL, ROBOT_MODE_AUTONOMOUS
    from DSR_ROBOT2 import get_robot_mode, set_robot_mode

    set_robot_mode(ROBOT_MODE_MANUAL)
    set_tool(ROBOT_TOOL)
    set_tcp(ROBOT_TCP)

    set_robot_mode(ROBOT_MODE_AUTONOMOUS)
    time.sleep(2)

    logger = node.get_logger()
    logger.info("=" * 50)
    logger.info("Initializing robot with the following settings:")
    logger.info(f"ROBOT_ID: {ROBOT_ID}")
    logger.info(f"ROBOT_MODEL: {ROBOT_MODEL}")
    logger.info(f"ROBOT_TCP: {get_tcp()}")
    logger.info(f"ROBOT_TOOL: {get_tool()}")
    logger.info(f"ROBOT_MODE 0:Manual, 1:Auto : {get_robot_mode()}")
    logger.info(f"VELOCITY: {VELOCITY}")
    logger.info(f"ACC: {ACC}")
    logger.info("=" * 50)

def open_gripper(node):
    '''Open the RG gripper'''
    import time
    node.get_logger().info("open_gripper")
    gripper.open_gripper()
    time.sleep(1.5)

def close_gripper(node):
    '''Close the RG gripper'''
    import time
    node.get_logger().info("close_gripper")
    gripper.close_gripper()
    time.sleep(1.5)

def perform_task(node):
    '''Tasks for the robot to perform'''
    node.get_logger().info("Performing task...")
    from DSR_ROBOT2 import posx, movej, movel, wait

    # Step 1: Move to initial position
    j_step_1 = [0, 0, 90, 0, 90, 0]
    node.get_logger().info("movej")
    movej(j_step_1, vel=VELOCITY, acc=ACC)

    # Step 2: Open gripper
    open_gripper(node)

    # Step 3: Move to pick position
    pos_step_3 = posx([300, 100, 150, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_3, vel=VELOCITY, acc=ACC)

    # Step 4: Move to pick position with safe Z offset
    pos_step_4 = posx([300, 100, 50, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_4, vel=VELOCITY, acc=ACC)

    # Step 5: Close gripper
    close_gripper(node)

    # Step 6: Wait
    node.get_logger().info("wait")
    wait(0.5)

    # Step 7: Move back to pick position with safe Z offset
    node.get_logger().info("movel")
    movel(pos_step_4, vel=VELOCITY, acc=ACC)

    # Step 8: Move to place position
    pos_step_8 = posx([400, 300, 200, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_8, vel=VELOCITY, acc=ACC)

    # Step 9: Move to place position with safe Z offset
    pos_step_9 = posx([400, 300, 100, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_9, vel=VELOCITY, acc=ACC)

    # Step 10: Open gripper
    open_gripper(node)

    # Step 11: Wait
    node.get_logger().info("wait")
    wait(0.5)

    # Step 12: Move back to place position with safe Z offset
    node.get_logger().info("movel")
    movel(pos_step_9, vel=VELOCITY, acc=ACC)

def main(args=None):
    '''Main function: Initialize ROS2 node and execute operations'''
    rclpy.init(args=args)
    node = rclpy.create_node("move_basic", namespace=ROBOT_ID)

    DR_init.__dsr__node = node

    try:
        initialize_robot(node)
        perform_task(node)

    except KeyboardInterrupt:
        node.get_logger().info("Node interrupted by user. Shutting down...")
    except Exception as e:
        node.get_logger().error(f"An unexpected error occurred: {e}")
    finally:
        rclpy.shutdown()

if __name__ == "__main__":
    main()