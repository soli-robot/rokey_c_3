"""
[Coder Agent 1.1 - Ollama 기반 로컬 코드 생성 스크립트]

이 코드는 로컬 PC에서 Ollama로 실행 중인 qwen2.5-coder-7b 기반 모델을 호출하여,
작업반장 Agent가 만든 작업 시퀀스를 두산 M0609 로봇 제어용 Python 코드로 변환하는 스크립트이다.

전체 동작 흐름:
1. task_sequence에 작성된 로봇 작업 순서를 Ollama 모델(doosan-coder)에 입력한다.
2. Ollama는 Modelfile에 등록된 시스템 프롬프트 규칙에 따라 Python 코드를 생성한다.
3. 생성된 코드에서 markdown 코드블록(```python 등)을 제거한다.
4. 생성 코드를 로컬 폴더(~/cobot_generated)에 .py 파일로 저장한다.
5. Python 문법 검사(py_compile)와 프로젝트 규칙 검사를 수행한다.
6. 검사에 통과하면 최신 생성 코드 파일(generated_doosan_task_latest.py)을 사용할 수 있다.

주의사항:
- 이 스크립트는 Ollama 서버가 실행 중이어야 동작한다.
  확인 명령어: systemctl status ollama
- MODEL_NAME에 지정된 doosan-coder 모델이 ollama list에 등록되어 있어야 한다.
- doosan-coder 모델은 Modelfile을 통해 시스템 프롬프트와 파라미터가 설정되어 있어야 한다.
- 이 스크립트 자체는 로봇을 직접 움직이지 않고, 로봇 실행용 Python 코드를 생성하고 저장하는 역할을 한다.
"""

import ast
import os
import subprocess
from datetime import datetime

import requests


MODEL_NAME = "doosan-coder"
OLLAMA_URL = "http://localhost:11434/api/generate"

SAVE_DIR = os.path.expanduser("~/cobot_generated")
LATEST_FILENAME = "generated_doosan_task_latest.py"


def call_ollama(prompt: str) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0,
                "top_p": 1,
                "repeat_penalty": 1.05,
                "num_predict": 3000,
            },
        },
        timeout=180,
    )

    response.raise_for_status()
    return response.json()["response"]


def clean_generated_code(text: str) -> str:
    code = text.strip()

    if code.startswith("```python"):
        code = code[len("```python"):].strip()
    elif code.startswith("```"):
        code = code[len("```"):].strip()

    if code.endswith("```"):
        code = code[:-3].strip()

    return code + "\n"


def save_code(code: str) -> tuple[str, str]:
    os.makedirs(SAVE_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    timestamp_path = os.path.join(
        SAVE_DIR,
        f"generated_doosan_task_{timestamp}.py",
    )

    latest_path = os.path.join(
        SAVE_DIR,
        LATEST_FILENAME,
    )

    with open(timestamp_path, "w", encoding="utf-8") as f:
        f.write(code)

    with open(latest_path, "w", encoding="utf-8") as f:
        f.write(code)

    return timestamp_path, latest_path


def validate_python_syntax(code: str, path: str) -> None:
    ast.parse(code)

    result = subprocess.run(
        ["python3", "-m", "py_compile", path],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise SyntaxError(result.stderr)


def validate_project_rules(code: str) -> None:
    forbidden_patterns = [
        "set_digital_output",
        "wait(node",
        "wait(duration",
        "while True",
        "DoosanRobot",
        "RobotArm",
        "gripper.open()",
        "gripper.close()",
        "```",
    ]

    for pattern in forbidden_patterns:
        if pattern in code:
            raise ValueError(f"Forbidden pattern detected: {pattern}")

    top_lines = "\n".join(code.splitlines()[:25])

    if "from DSR_ROBOT2 import" in top_lines:
        raise ValueError("DSR_ROBOT2 was imported at top-level.")

    required_patterns = [
        "import rclpy",
        "import DR_init",
        "import time",
        "from pick_and_place_text.onrobot import RG",
        'ROBOT_ID = "dsr01"',
        'ROBOT_MODEL = "m0609"',
        'ROBOT_TOOL = "Tool Weight"',
        'ROBOT_TCP = "GripperDA_v1"',
        'GRIPPER_NAME = "rg2"',
        'TOOLCHANGER_IP = "192.168.1.1"',
        'TOOLCHANGER_PORT = "502"',
        "gripper = RG(GRIPPER_NAME, TOOLCHANGER_IP, TOOLCHANGER_PORT)",
        "DR_init.__dsr__id = ROBOT_ID",
        "DR_init.__dsr__model = ROBOT_MODEL",
        "def initialize_robot(node):",
        "def open_gripper(node):",
        "def close_gripper(node):",
        "def perform_task(node):",
        "def main(args=None):",
        "DR_init.__dsr__node = node",
        "node.get_logger()",
    ]

    for pattern in required_patterns:
        if pattern not in code:
            raise ValueError(f"Required pattern missing: {pattern}")


def generate_robot_code(task_sequence: str) -> str:
    prompt = task_sequence.strip()
    raw_output = call_ollama(prompt)
    code = clean_generated_code(raw_output)
    return code


def main():
    task_sequence = """
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

    try:
        print("[1] Calling Ollama...")
        code = generate_robot_code(task_sequence)

        print("[2] Saving generated code...")
        timestamp_path, latest_path = save_code(code)

        print("[3] Validating Python syntax...")
        validate_python_syntax(code, latest_path)

        print("[4] Validating project rules...")
        validate_project_rules(code)

        print("=" * 60)
        print("Code generation completed successfully.")
        print(f"Saved timestamp file: {timestamp_path}")
        print(f"Saved latest file:    {latest_path}")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("[ERROR] Cannot connect to Ollama server.")
        print("Check this command:")
        print("  systemctl status ollama")

    except requests.exceptions.Timeout:
        print("[ERROR] Ollama request timeout.")

    except requests.exceptions.HTTPError as e:
        print(f"[ERROR] Ollama HTTP error: {e}")

    except SyntaxError as e:
        print("[ERROR] Generated code has Python syntax error.")
        print(e)

    except ValueError as e:
        print("[ERROR] Generated code failed project rule validation.")
        print(e)

    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")


if __name__ == "__main__":
    main()