import ollama
import re
import os
import socket
from datetime import datetime

# Firebase 라이브러리
import firebase_admin
from firebase_admin import credentials, firestore
from fastapi import FastAPI, Request
import uvicorn
# ============================================================
# 1. 모델 프롬프트 (생성될 로봇 코드의 템플릿 - ROS2 출력용)
# ============================================================
MODEL_NAME = "qwen2.5:7b" 

SYSTEM_PROMPT = r"""
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
        
if __name__ == "__main__":
	   main()

============================================================
[FINAL GOAL]
Exactly convert the Steps provided by the user into Doosan M0609 DSR_ROBOT2 API call code.
Accuracy is more important than creativity.
DO NOT create behaviors not present in the input.
OUTPUT ONLY PYTHON CODE.
"""

# ============================================================
# 2. Firebase 업로더 클래스 (4060에서 실행됨)
# ============================================================
class FirebaseLogUploader:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        key_path = os.path.join(current_dir, "resource", "rokey2-e9270-firebase-adminsdk-fbsvc-c831c80eb6.json")
        try:
            cred = credentials.Certificate(key_path)
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
            self.db = firestore.client()
            print('✅ Firebase Admin SDK 초기화 성공!')
        except Exception as e:
            print(f'❌ Firebase 초기화 실패: {e}')
            self.db = None

    def upload_log(self, prompt, data_code, error_message=None):
        if self.db is None: return
        log_data = {'timestamp': datetime.now(), 'prompt': prompt, 'data_code': data_code, 'is_error': bool(error_message)}
        if error_message: log_data['error_message'] = error_message

        try:
            update_time, doc_ref = self.db.collection('CoderLLM_Logs').add(log_data)
            print(f"☁️ 파이어베이스 업로드 완료 [문서 ID: {doc_ref.id}]")
        except Exception as e:
            print(f"❌ 파이어베이스 통신 에러 발생: {e}")


# ============================================================
# 3. 파이썬 소켓 전송기 (만들어진 코드를 5060 뇌로 쏴줌)
# ============================================================
def send_code_to_5060(code_string, target_ip, port=9999):
    try:
        print(f"📡 5060 컴퓨터({target_ip})로 코드 전송을 시도합니다...")
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(5.0) # 5초 대기
        client_socket.connect((target_ip, port))
        
        client_socket.sendall(code_string.encode('utf-8'))
        client_socket.close()
        print("✅ 5060 컴퓨터로 코드 전송 성공! (임무 완수)")
    except Exception as e:
        print(f"❌ 5060 컴퓨터 전송 실패: {e}")
        print("💡 5060 컴퓨터가 수신 대기 상태인지 확인해주세요.")


# ============================================================
# 4. LLM 로컬 코드 생성 (4060 본인 컴퓨터에서 Ollama 실행)
# ============================================================
def generate_robot_code(task_sequence):
    print(f"🚀 [4060 실행] {MODEL_NAME} 모델이 코드를 생성 중입니다...")
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': task_sequence},
        ],
        options={'temperature': 0.0} 
    )
    result = response['message']['content'].strip()
    result = re.sub(r"^```python\n?", "", result, flags=re.IGNORECASE)
    result = re.sub(r"^```\n?", "", result)
    result = re.sub(r"```$", "", result)
    return result.strip()


# ============================================================
# 5. 메인 실행 (4060 기준)
# ============================================================
if __name__ == "__main__":
    # 🌟🌟 여기에 코드를 받을 '5060 컴퓨터'의 IP를 적어주세요! 🌟🌟
    BRAIN_5060_IP = "192.168.0.20"  
    
    uploader = FirebaseLogUploader()

    task_input = '''
        Task: shake_object
        Object: salt
        PickPosition: [320, -160, 80]
        Destination: seasoning_area
        PlacePosition: [500, 0, 180]
        SafeZOffset: 100
        Steps:
        1. action=movej, target=[0, 0, 90, 0, 90, 0]
        2. action=open_gripper
        3. action=movel, target=[320, -160, 180]
        4. action=movel, target=[320, -160, 80]
        5. action=close_gripper
        6. action=movel, target=[320, -160, 180]
        7. action=movel, target=[500, 0, 180]
        8. action=shake, repeat=3
        9. action=movel, target=[320, -160, 180]
        10. action=movel, target=[320, -160, 80]
        11. action=open_gripper
        12. action=movel, target=[320, -160, 180]
    '''
    
    try:
        print("\n" + "="*50)
        
        # [STEP 1] 4060에서 직접 코드 생성
        generated_code = generate_robot_code(task_input)
        
        # [STEP 2] 4060 로컬에 파일 백업
        save_filename = "4060_local_backup.py"
        with open(save_filename, "w", encoding="utf-8") as f:
            f.write(generated_code)
        
        # [STEP 3] 5060으로 생성된 코드 쏴주기 (네트워크 통신)
        send_code_to_5060(generated_code, BRAIN_5060_IP)
        
        # [STEP 4] Firebase에 데이터 저장
        uploader.upload_log(prompt=task_input.strip(), data_code=generated_code)
        
        print("="*50)
        print("🎉 4060 임무 완수! 코드를 무사히 5060으로 넘겼습니다.")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")