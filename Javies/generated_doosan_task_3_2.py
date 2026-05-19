"""
이 코드는 로컬에서 파이썬 스크립트로 실행한 qwen2.5-coder-7B 모델이 생성한 3.2 버전 코드입니다.
qwen_2_1.py 스크립트가 도출한 코드입니다.
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
    time.sleep(0.5)


def close_gripper(node):
    '''Close the RG gripper'''
    import time
    node.get_logger().info("close_gripper")
    gripper.close_gripper()
    time.sleep(0.5)


def perform_task(node):
    '''Tasks for the robot to perform'''
    node.get_logger().info("Performing task...")
    from DSR_ROBOT2 import posx, movej, movel, wait

    # Step 1
    j_step_1 = [0, 0, 90, 0, 90, 0]
    node.get_logger().info("movej")
    movej(j_step_1, vel=VELOCITY, acc=ACC)

    # Step 2
    open_gripper(node)

    # Step 3
    pos_step_3 = posx([320, -160, 180, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_3, vel=VELOCITY, acc=ACC)

    # Step 4
    pos_step_4 = posx([320, -160, 80, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_4, vel=VELOCITY, acc=ACC)

    # Step 5
    close_gripper(node)

    # Step 6
    pos_step_6 = posx([320, -160, 180, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_6, vel=VELOCITY, acc=ACC)

    # Step 7
    pos_step_7 = posx([500, 0, 180, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_7, vel=VELOCITY, acc=ACC)

    # Step 8
    # TODO: Unknown action in Step 8: shake

    # Step 9
    pos_step_9 = posx([320, -160, 180, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_9, vel=VELOCITY, acc=ACC)

    # Step 10
    pos_step_10 = posx([320, -160, 80, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_10, vel=VELOCITY, acc=ACC)

    # Step 11
    open_gripper(node)

    # Step 12
    pos_step_12 = posx([320, -160, 180, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_12, vel=VELOCITY, acc=ACC)


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