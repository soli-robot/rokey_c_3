"""
이 코드는 qwen2.5-coder-7B 모델이 생성한 1.3 버전 코드입니다. 다른 Task 입력에 대한 올바른 출력을 테스트하기 위해 생성되었습니다.
System, User 프롬프트는 동일합니다. 1.2 버전 이하와 비교하여 다음의 작업반장의 Task만 다릅니다.

task_sequence = 
Task: pick_and_place

Object: wrench
PickPosition: [250, -120, 70]

Destination: tool_box
PlacePosition: [520, 180, 110]

SafeZOffset: 100

Steps:
1. action=movej, target=[0, 0, 90, 0, 90, 0]
2. action=open_gripper
3. action=movel, target=[250, -120, 170]
4. action=movel, target=[250, -120, 70]
5. action=close_gripper
6. action=wait, duration=0.5
7. action=movel, target=[250, -120, 170]
8. action=movel, target=[520, 180, 210]
9. action=movel, target=[520, 180, 110]
10. action=open_gripper
11. action=wait, duration=0.5
12. action=movel, target=[520, 180, 210]
"""

import rclpy
import DR_init
import time

ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"
ROBOT_TOOL = "Tool Weight"
ROBOT_TCP = "GripperDA_v1"

VELOCITY = 40
ACC = 60

DR_init.__dsr__id = ROBOT_ID
DR_init.__dsr__model = ROBOT_MODEL

def initialize_robot():
    '''로봇의 Tool과 TCP를 설정'''
    from DSR_ROBOT2 import set_tool, set_tcp, get_tool, get_tcp, ROBOT_MODE_MANUAL, ROBOT_MODE_AUTONOMOUS
    from DSR_ROBOT2 import get_robot_mode, set_robot_mode

    set_robot_mode(ROBOT_MODE_MANUAL)
    set_tool(ROBOT_TOOL)
    set_tcp(ROBOT_TCP)

    set_robot_mode(ROBOT_MODE_AUTONOMOUS)
    time.sleep(2)

    print("#" * 50)
    print("Initializing robot with the following settings:")
    print(f"ROBOT_ID: {ROBOT_ID}")
    print(f"ROBOT_MODEL: {ROBOT_MODEL}")
    print(f"ROBOT_TCP: {get_tcp()}")
    print(f"ROBOT_TOOL: {get_tool()}")
    print(f"ROBOT_MODE 0:수동, 1:자동 : {get_robot_mode()}")
    print(f"VELOCITY: {VELOCITY}")
    print(f"ACC: {ACC}")
    print("#" * 50)

def open_gripper():
    '''그리퍼 열기'''
    from DSR_ROBOT2 import set_digital_output, wait

    print("open_gripper")
    set_digital_output(1, 0)
    set_digital_output(2, 1)
    wait(0.5)

def close_gripper():
    '''그리퍼 닫기'''
    from DSR_ROBOT2 import set_digital_output, wait

    print("close_gripper")
    set_digital_output(1, 1)
    set_digital_output(2, 0)
    wait(0.5)

def perform_task():
    '''로봇이 수행할 작업'''
    print("Performing task...")
    from DSR_ROBOT2 import posx, movej, movel, wait

    # 사용자의 Steps를 여기에서 순서대로 실행한다.
    j_step_1 = [0, 0, 90, 0, 90, 0]
    print("movej")
    movej(j_step_1, vel=VELOCITY, acc=ACC)

    open_gripper()

    pos_step_3 = posx([250, -120, 170, 150, 179, 150])
    print("movel")
    movel(pos_step_3, vel=VELOCITY, acc=ACC)

    pos_step_4 = posx([250, -120, 70, 150, 179, 150])
    print("movel")
    movel(pos_step_4, vel=VELOCITY, acc=ACC)

    close_gripper()
    wait(0.5)

    pos_step_7 = posx([250, -120, 170, 150, 179, 150])
    print("movel")
    movel(pos_step_7, vel=VELOCITY, acc=ACC)

    pos_step_8 = posx([520, 180, 210, 150, 179, 150])
    print("movel")
    movel(pos_step_8, vel=VELOCITY, acc=ACC)

    pos_step_9 = posx([520, 180, 110, 150, 179, 150])
    print("movel")
    movel(pos_step_9, vel=VELOCITY, acc=ACC)

    open_gripper()
    wait(0.5)

    pos_step_12 = posx([520, 180, 210, 150, 179, 150])
    print("movel")
    movel(pos_step_12, vel=VELOCITY, acc=ACC)

def main(args=None):
    '''메인 함수: ROS2 노드 초기화 및 동작 수행'''
    rclpy.init(args=args)
    node = rclpy.create_node("move_basic", namespace=ROBOT_ID)

    DR_init.__dsr__node = node

    try:
        initialize_robot()
        perform_task()

    except KeyboardInterrupt:
        print("\nNode interrupted by user. Shutting down...")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        rclpy.shutdown()

if __name__ == "__main__":
    main()