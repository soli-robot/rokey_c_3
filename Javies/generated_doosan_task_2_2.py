"""
이 코드는 qwen2.5-coder-7B 모델이 생성한 2.2 버전 코드입니다. 2.x 버전부터 그리퍼 제어 방식을 RG 모듈을 사용하도록 시스템 프롬프트를 수정하고, 응답 속도를 위해 영어로 작성했습니다.
2.1 버전과 비교하여 테스크를 변경했습니다. 테스크는 1.5 버전에 사용한 것을 입력했습니다.

task_sequence = 
Task: multi_pick_and_place

Object: hammer, screwdriver
PickPosition:
- hammer: [260, 100, 60]
- screwdriver: [280, -80, 55]

Destination: tool_box
PlacePosition:
- hammer: [520, 120, 100]
- screwdriver: [540, -100, 100]

SafeZOffset: 100

Steps:
1. action=movej, target=[0, 0, 90, 0, 90, 0]
2. action=open_gripper
3. action=movel, target=[260, 100, 160]
4. action=movel, target=[260, 100, 60]
5. action=close_gripper
6. action=wait, duration=0.5
7. action=movel, target=[260, 100, 160]
8. action=movel, target=[520, 120, 200]
9. action=movel, target=[520, 120, 100]
10. action=open_gripper
11. action=wait, duration=0.5
12. action=movel, target=[520, 120, 200]
13. action=open_gripper
14. action=movel, target=[280, -80, 155]
15. action=movel, target=[280, -80, 55]
16. action=close_gripper
17. action=wait, duration=0.5
18. action=movel, target=[280, -80, 155]
19. action=movel, target=[540, -100, 200]
20. action=movel, target=[540, -100, 100]
21. action=open_gripper
22. action=wait, duration=0.5
23. action=movel, target=[540, -100, 200]
24. action=movej, target=[0, 0, 90, 0, 90, 0]
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

    # Step 1
    j_step_1 = [0, 0, 90, 0, 90, 0]
    node.get_logger().info("movej")
    movej(j_step_1, vel=VELOCITY, acc=ACC)

    # Step 2
    open_gripper(node)

    # Step 3
    pos_step_3 = posx([260, 100, 160, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_3, vel=VELOCITY, acc=ACC)

    # Step 4
    pos_step_4 = posx([260, 100, 60, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_4, vel=VELOCITY, acc=ACC)

    # Step 5
    close_gripper(node)

    # Step 6
    node.get_logger().info("wait")
    wait(0.5)

    # Step 7
    pos_step_7 = posx([260, 100, 160, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_7, vel=VELOCITY, acc=ACC)

    # Step 8
    pos_step_8 = posx([520, 120, 200, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_8, vel=VELOCITY, acc=ACC)

    # Step 9
    pos_step_9 = posx([520, 120, 100, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_9, vel=VELOCITY, acc=ACC)

    # Step 10
    open_gripper(node)

    # Step 11
    node.get_logger().info("wait")
    wait(0.5)

    # Step 12
    pos_step_12 = posx([520, 120, 200, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_12, vel=VELOCITY, acc=ACC)

    # Step 13
    open_gripper(node)

    # Step 14
    pos_step_14 = posx([280, -80, 155, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_14, vel=VELOCITY, acc=ACC)

    # Step 15
    pos_step_15 = posx([280, -80, 55, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_15, vel=VELOCITY, acc=ACC)

    # Step 16
    close_gripper(node)

    # Step 17
    node.get_logger().info("wait")
    wait(0.5)

    # Step 18
    pos_step_18 = posx([280, -80, 155, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_18, vel=VELOCITY, acc=ACC)

    # Step 19
    pos_step_19 = posx([540, -100, 200, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_19, vel=VELOCITY, acc=ACC)

    # Step 20
    pos_step_20 = posx([540, -100, 100, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_20, vel=VELOCITY, acc=ACC)

    # Step 21
    open_gripper(node)

    # Step 22
    node.get_logger().info("wait")
    wait(0.5)

    # Step 23
    pos_step_23 = posx([540, -100, 200, 150, 179, 150])
    node.get_logger().info("movel")
    movel(pos_step_23, vel=VELOCITY, acc=ACC)

    # Step 24
    j_step_24 = [0, 0, 90, 0, 90, 0]
    node.get_logger().info("movej")
    movej(j_step_24, vel=VELOCITY, acc=ACC)

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