"""
[Coder Agent 3.2 - Ollama + ROS2 Topic + Firebase 연동 코드 생성 스크립트]

이 코드는 로컬 PC에서 Ollama 모델을 호출하여,
작업반장 Agent가 만든 작업 시퀀스를 두산 M0609 로봇 제어용 Python 코드로 변환하는 Coder Agent 스크립트이다.

전체 동작 흐름:
1. SYSTEM_PROMPT와 task_sequence를 Ollama 모델에 입력한다.
2. Ollama 모델은 시스템 프롬프트 규칙에 따라 두산 M0609용 Python 코드를 생성한다.
3. 생성된 코드에서 markdown 코드블록(```python 등)을 제거한다.
4. 생성된 Python 코드를 로컬 파일(latest_generated_robot_task.py)로 저장한다.
5. 생성된 코드를 ROS2 Topic(/generated_robot_code)으로 Publish하여 다른 PC 또는 노드로 전달한다.
6. 생성 결과와 입력 프롬프트를 Firebase Firestore에 로그로 저장한다.
7. 모든 작업이 끝나면 ROS2 노드를 종료하고 스크립트를 마무리한다.

구성 요소:
- SYSTEM_PROMPT:
  생성될 로봇 코드의 구조, 금지 규칙, DSR_ROBOT2 import 위치, 그리퍼 제어 방식 등을 정의한다.

- FirebaseLogUploader:
  입력 프롬프트와 생성된 코드를 Firebase Firestore에 기록하는 클래스이다.

- CodePublisher:
  생성된 Python 코드를 ROS2 String 메시지로 /generated_robot_code 토픽에 Publish하는 노드이다.

- generate_robot_code():
  Ollama chat API를 호출하여 SYSTEM_PROMPT와 task_sequence를 전달하고, 모델 출력을 Python 코드 문자열로 정리한다.

- main():
  ROS2 노드 초기화, 코드 생성, 로컬 파일 저장, ROS2 Publish, Firebase 업로드를 순서대로 수행한다.

주의사항:
- 이 스크립트는 로봇을 직접 움직이는 코드가 아니라, 로봇 실행용 Python 코드를 생성하고 전송하는 코드 생성기이다.
- Ollama 서버가 실행 중이어야 한다.
- MODEL_NAME에 지정된 모델이 ollama list에 등록되어 있어야 한다.
- Firebase를 사용하려면 key_path에 지정된 Firebase 인증 JSON 파일이 실제로 존재해야 한다.
- ROS2 Topic 통신을 사용하려면 송신 PC와 수신 PC의 ROS_DOMAIN_ID, RMW 설정, 네트워크 설정이 맞아야 한다.
- 생성된 코드가 실제 로봇에서 실행되기 전에는 반드시 문법 검사 및 버츄얼 검증을 거치는 것이 좋다.
"""

import ollama
import re
import os
import time
from datetime import datetime

# ROS2 통신 라이브러리
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

# Firebase 라이브러리
import firebase_admin
from firebase_admin import credentials, firestore

# ============================================================
# 1. 모델 프롬프트 (생성될 로봇 코드의 템플릿 - 변동 없음)
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

# ============================================================
# 2. Firebase 업로더 클래스
# ============================================================
class FirebaseLogUploader:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        key_path = '/home/rokey/Downloads/rokey2-e9270-firebase-adminsdk-fbsvc-c831c80eb6.json'
        
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
        if self.db is None:
            return

        log_data = {
            'timestamp': datetime.now(),
            'prompt': prompt,
            'data_code': data_code,
            'is_error': bool(error_message),
        }

        if error_message:
            log_data['error_message'] = error_message

        try:
            update_time, doc_ref = self.db.collection('CoderLLM_Logs').add(log_data)
            print(f"☁️ 파이어베이스 업로드 완료 [문서 ID: {doc_ref.id}]")
        except Exception as e:
            print(f"❌ 파이어베이스 통신 에러 발생: {e}")


# ============================================================
# 3. ROS2 코드 퍼블리셔 (다른 PC로 전송)
# ============================================================
class CodePublisher(Node):
    def __init__(self):
        super().__init__('llm_code_generator_node')
        # '/generated_robot_code' 토픽으로 String 형태의 코드를 쏩니다.
        self.publisher_ = self.create_publisher(String, '/generated_robot_code', 10)
        self.get_logger().info("ROS2 Publisher 준비 완료.")

    def publish_code(self, code_string):
        msg = String()
        msg.data = code_string
        self.publisher_.publish(msg)
        self.get_logger().info("📡 ROS2 통신: 다른 PC로 생성된 코드를 Publish 했습니다! (토픽: /generated_robot_code)")


# ============================================================
# 4. LLM 코드 생성 함수
# ============================================================
def generate_robot_code(task_sequence):
    print(f"🚀 [{MODEL_NAME}] 모델이 로봇 코드를 생성 중입니다...")
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
# 5. 메인 실행 흐름
# ============================================================
def main(args=None):
    rclpy.init(args=args)
    
    # 노드 및 업로더 초기화
    code_pub_node = CodePublisher()
    uploader = FirebaseLogUploader()

    # 입력할 Task 내용
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
        
        # [STEP 1] Ollama 코드 생성
        generated_code = generate_robot_code(task_input)
        
        # [STEP 2] 생성된 코드를 로컬 .py 파일로 저장
        save_filename = "latest_generated_robot_task.py"
        with open(save_filename, "w", encoding="utf-8") as f:
            f.write(generated_code)
        print(f"💾 로컬 파일 저장 완료: [{save_filename}]")
        
        # [STEP 3] ROS2 Publish (다른 컴퓨터로 전송)
        code_pub_node.publish_code(generated_code)
        
        # [STEP 4] Firebase Upload (데이터베이스 저장)
        uploader.upload_log(prompt=task_input.strip(), data_code=generated_code)
        
        # 네트워크 전송이 완벽히 이루어지도록 1.5초 대기
        time.sleep(1.5)
        
        print("="*50)
        print("🎉 모든 작업(생성 ➔ 파일 저장 ➔ Publish ➔ DB저장)이 완료되었습니다.")

    except Exception as e:
        code_pub_node.get_logger().error(f"오류 발생: {e}")
    finally:
        # 단 1회 실행 후 프로세스 깔끔하게 종료
        code_pub_node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()