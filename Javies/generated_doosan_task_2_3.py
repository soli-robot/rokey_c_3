"""
이 코드는 qwen2.5-coder-7B 모델이 생성한 2.3 버전 코드입니다. 2.x 버전부터 그리퍼 제어 방식을 RG 모듈을 사용하도록 시스템 프롬프트를 수정하고, 응답 속도를 위해 영어로 작성했습니다.
테스크는 그리퍼 동작을 확인하도록 다음과 같이 입력했습니다.

task_sequence = 
Task: gripper_test

Steps:
1. action=open_gripper
2. action=wait, duration=0.5
3. action=move_gripper, width=500, force=300
4. action=wait, duration=0.5
5. action=close_gripper
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
GRIPPER_FORCE = 400
GRIPPER_WAIT_TIME = 1.5

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
    node.get_logger().info("open_gripper")
    gripper.open_gripper()
    time.sleep(GRIPPER_WAIT_TIME)

def close_gripper(node):
    '''Close the RG gripper'''
    node.get_logger().info("close_gripper")
    gripper.close_gripper()
    time.sleep(GRIPPER_WAIT_TIME)

def move_gripper(node, width_val, force_val=None):
    '''Move the RG gripper to a specific width'''
    node.get_logger().info("move_gripper")

    if force_val is None:
        gripper.move_gripper(width_val=width_val, force_val=GRIPPER_FORCE)
    else:
        gripper.move_gripper(width_val=width_val, force_val=force_val)

    time.sleep(GRIPPER_WAIT_TIME)

def perform_task(node):
    '''Tasks for the robot to perform'''
    node.get_logger().info("Performing task...")
    from DSR_ROBOT2 import posx, movej, movel, wait

    # Step 1: Open gripper
    open_gripper(node)

    # Step 2: Wait for 0.5 seconds
    wait(0.5)

    # Step 3: Move gripper to width 500 with force 300
    move_gripper(node, width_val=500, force_val=300)

    # Step 4: Wait for 0.5 seconds
    wait(0.5)

    # Step 5: Close gripper
    close_gripper(node)

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