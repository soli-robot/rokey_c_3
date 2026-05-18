import os
import re
import subprocess
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.callbacks import StreamingStdOutCallbackHandler

class ROS2AutoAgent:
    def __init__(self):
        # 1. Gemma 모델 세팅 (로컬 구동)
        self.llm = ChatOllama(model="gemma4:e2b", temperature=0.0, callbacks=[StreamingStdOutCallbackHandler()])
        
        # 2. 파일 경로 세팅 (사용자 환경에 맞게 계정명 수정 필요)
        self.rules_file_path = "/home/soli/cobot_ws/src/cobot1/cobot1/dynamic_rules.txt"  # 진화하는 프롬프트(장기 기억)
        self.target_code_path = "/home/soli/cobot_ws/src/cobot1/cobot1/voice_cmd_node.py"
        self.ros_run_command = "cd ~/cobot_ws && source install/setup.bash && ros2 run cobot1 voice_cmd"
        # self.ros_run_command = "cd ~/corecode/VoiceProcessing && python3 voice_cmd_node.py"

        # 3. 에이전트 시스템 프롬프트 (수정됨: Import 위치 제약 조건 추가)
        self.system_prompt = """
        당신은 자율적으로 에러를 해결하고 코드를 진화시키는 '자율형 ROS2 및 두산 로봇(m0609) 수석 엔지니어 에이전트'입니다.
        당신의 목표는 주어진 [목표 동작]을 완벽히 수행하는 파이썬 코드를 작성하고, 만약 [에러 로그]가 주어졌다면 그 원인을 분석해 코드를 고치며 당신의 [필수 제약 조건]을 스스로 업데이트하는 것입니다.
        현재 로봇은 YOLO를 쓰기 전, Virtual 모드(rviz)에서 검증 중입니다.

        [1. 목표 동작]
        {target_action}

        [2. 에러 로그 및 이전 피드백]
        {error_log}

        [3. 필수 제약 조건 (Doosan m0609 & ROS2 특화)]
        - 🚨 [가장 중요] 라이브러리 임포트 위치: `from DSR_ROBOT2 import ...` 및 `from DR_common2 import ...` 같은 두산 전용 모듈은 **절대 파일 최상단에 임포트하지 마세요.** 반드시 `class` 내부의 메서드(`def`)나 `main()` 함수 내부에서 `rclpy.init()`이 호출된 이후에 임포트해야 NoneType 에러를 막을 수 있습니다.
        - 이동 명령: 순수 파이썬 리스트(`[]`)를 절대 `movel`이나 `movej`에 넣지 말 것. 반드시 `posx([x, y, z, rx, ry, rz])` 또는 `posj([j1~j6])` 객체로 감쌀 것. 숫자 타입은 float으로 통일.
        - 상대 이동: 현재 위치에서 특정 축으로만 이동할 때는 `mod=DR_MV_MOD_REL` 옵션을 사용할 것.
        - 그리퍼: `RG` 객체 사용 및 `close_gripper()`, `open_gripper()` 호출 후 반드시 동작 완료를 위해 `mwait()` 또는 `time.sleep()` 대기 시간을 부여할 것.
        {additional_constraints}

        [4. 출력 형식 (엄격한 규칙)]
        당신은 기계적인 파싱을 위해 절대 다른 인사말이나 설명을 추가하지 말고, 아래 두 가지 태그를 사용하여 출력해야 합니다.

        <CODE>
        # 여기에 즉시 실행 가능한 완성된 파이썬 코드만 작성하세요.
        </CODE>

        <NEXT_PROMPT>
        # 만약 [2. 에러 로그]가 존재했다면, 그 에러가 다시 발생하지 않도록 [3. 필수 제약 조건]에 추가할 "새로운 규칙 텍스트"만 여기에 작성하세요. 에러가 없었다면 'None'이라고 적으세요.
        </NEXT_PROMPT>
        """
        self.prompt_template = PromptTemplate(
            input_variables=["target_action", "error_log", "additional_constraints"],
            template=self.system_prompt
        )
        self.chain = self.prompt_template | self.llm

    def load_dynamic_rules(self):
        """저장된 추가 규칙(프롬프트)을 불러옵니다. (장기 기억 장치)"""
        if not os.path.exists(self.rules_file_path):
            return ""
        with open(self.rules_file_path, "r", encoding="utf-8") as f:
            return f.read()

    def append_dynamic_rule(self, new_rule):
        """Gemma가 찾아낸 새로운 에러 방지 규칙을 파일에 누적 저장합니다."""
        if new_rule and new_rule.strip().upper() != "NONE":
            with open(self.rules_file_path, "a", encoding="utf-8") as f:
                f.write(f"\n- {new_rule.strip()}")
            print(f"🧠 [에이전트 학습 완료] 새로운 규칙이 프롬프트에 영구 저장되었습니다: {new_rule}")

    def generate_and_save_code(self, target_action, error_log="없음"):
        """LLM을 호출하여 코드를 생성하고 파일로 저장합니다."""
        print("\n⏳ Gemma가 코드를 (재)작성 중입니다...")
        
        additional_rules = self.load_dynamic_rules()
        response = self.chain.invoke({
            "target_action": target_action,
            "error_log": error_log,
            "additional_constraints": additional_rules
        })
        
        raw_text = response.content
        
        # 정규표현식으로 <CODE> 와 <NEXT_PROMPT> 블록 파싱 (오타 수정됨)
        code_match = re.search(r'<CODE>(.*?)</CODE>', raw_text, re.DOTALL | re.IGNORECASE)
        rule_match = re.search(r'<NEXT_PROMPT>(.*?)</NEXT_PROMPT>', raw_text, re.DOTALL | re.IGNORECASE)

        if code_match:
            code_content = code_match.group(1).strip()
            code_content = re.sub(
                r'^```(?:python)?|```$',  # 무엇을 찾을 것인가?
                '',                       # 무엇으로 바꿀 것인가? ('' = 빈칸, 즉 지워버림)
                code_content,             # 어디서 찾을 것인가?
                flags=re.MULTILINE        # 여러 줄(엔터)이 있어도 각 줄의 처음과 끝을 검사함
            ).strip()
            
            with open(self.target_code_path, "w", encoding="utf-8") as f:
                f.write(code_content)
            print(f"✅ 코드가 성공적으로 저장되었습니다. ({self.target_code_path})")
        else:
            print("❌ LLM 응답에서 <CODE> 태그를 찾지 못했습니다.")
            return False

        if rule_match:
            self.append_dynamic_rule(rule_match.group(1))
            
        return True

    def execute_ros_node(self):
        """ROS2 노드를 실행하고 터미널의 에러를 캡처합니다."""
        print(f"\n🚀 가상 로봇 연동 ROS2 노드 실행 중... \n(명령어: {self.ros_run_command})")
        
        process = subprocess.Popen(
            self.ros_run_command, 
            shell=True, 
            executable='/bin/bash', 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        
        stdout, stderr = process.communicate()
        
        # 'Error', 'Exception', 'Traceback' 등 치명적인 에러 키워드 감지
        if process.returncode != 0 or any(kw in stderr for kw in ["Error", "Exception", "Traceback"]):
            print("🚨 노드 실행 중 오류가 발생했습니다!")
            print(f"[Captured Error]\n{stderr.strip()}")
            return stderr.strip()
        else:
            print("🎉 노드가 에러 없이 성공적으로 실행(또는 종료)되었습니다!")
            return None

    def run_autonomous_loop(self, voice_command):
        """에러가 해결될 때까지 무한 루프를 도는 에이전트 핵심 메서드"""
        target_action = f"명령: {voice_command}"
        error_log = "없음"
        max_retries = 3  
        
        for attempt in range(max_retries):
            print(f"\n=== [에이전트 사이클 {attempt + 1}/{max_retries}] ===")
            
            # 1. 코드 생성 및 저장
            success = self.generate_and_save_code(target_action, error_log)
            if not success:
                break
                
            # 2. 코드 실행 및 에러 감지
            new_error = self.execute_ros_node()
            
            # 3. 결과 판단
            if new_error is None:
                print("\n🤖 [미션 완료] 에이전트가 주어진 명령을 완벽하게 수행했습니다.")
                break
            else:
                error_log = f"다음 에러가 발생했습니다:\n{new_error}"
                print("\n🔄 에이전트가 에러를 분석하고 코드를 수정하여 재시도합니다...")
        else:
            print("\n❌ 최대 재시도 횟수(3회)를 초과했습니다. 에이전트 로직을 확인해주세요.")
            print("💡 안심하세요! 지금까지 찾은 에러 방지 규칙은 dynamic_rules.txt에 저장되어 다음 실행 시 똑똑해집니다.")

# ==========================================
# 실제 실행 부분
# ==========================================
if __name__ == "__main__":
    print("======================================================")
    print("⚠️ [안내] 에이전트 실행 전, 다른 터미널에서 아래 명령어로")
    print("가상 시뮬레이터를 켜두셨는지 확인해 주세요.")
    print("ros2 launch dsr_bringup2 dsr_bringup2_rviz.launch.py mode:=virtual host:=192.168.1.100 port:=12345 model:=m0609")
    print("======================================================\n")

    agent = ROS2AutoAgent()
    
    # 임시 테스트용 음성 텍스트
    voice_text = "망치를 집어서 바구니에 넣어줘" 
    print(f"🎤 입력된 명령: {voice_text}")
    
    # 무한 루프 시작
    agent.run_autonomous_loop(voice_text)