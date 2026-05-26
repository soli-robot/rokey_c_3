import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.append(src_dir)

import json
import streamlit as st
import ollama
import websocket  # pip install websocket-client
import asyncio
import threading
import websockets # 1650에서 받을 때 사용 (서버)
import threading

# PostgreSQL 인프라 연동 컴포넌트 임포트
from FireBaseDB.fireSQLconnet import FirebaseSQLconnetTaskUploader

# =====================================================================
# 🌐 [스레드 안전] 1650 감각 PC에서 들어오는 실시간 전역 버퍼 클래스
# =====================================================================
class SensoryDataBuffer:
    def __init__(self):
        self.command = "대기 중... (1650 PC의 음성 명령을 기다립니다)"
        self.yolo = {}
        self.lock = threading.Lock()  # 데이터 동시 접근 방지용 안전장치

    def update(self, command, yolo):
        with self.lock:
            if command:
                self.command = command
            if yolo:
                self.yolo = yolo

    def get_data(self):
        with self.lock:
            return self.command, self.yolo

# 전역 객체 생성 (Streamlit의 상태와 무관하게 백그라운드에서 항상 접근 가능)
if 'global_buffer' not in st.session_state:
    st.session_state['global_buffer'] = SensoryDataBuffer()

global_sensor_buffer = st.session_state['global_buffer']

# =====================================================================
# 🚀 1650으로부터 데이터를 수신하는 백그라운드 웹소켓 서버
# =====================================================================
def run_ws_server_for_1650():
    async def handler(websocket):
        print("📡 [5060] 1650 감각 PC 연결 수립 완료!")
        try:
            async for message in websocket:
                data = json.loads(message)
                print(f"📥 [5060] 1650으로부터 데이터 수신: {data}")
                
                # 💡 [핵심 변경] st.session_state 대신 전역 버퍼 클래스에 안전하게 저장
                cmd = data.get("command")
                yolo = data.get("yolo")
                global_sensor_buffer.update(cmd, yolo)
                    
        except websockets.exceptions.ConnectionClosed:
            print("🛑 [5060] 1650 감각 PC 연결 종료")

    async def main_server():
        async with websockets.serve(handler, "0.0.0.0", 8889):
            await asyncio.Future()

    asyncio.run(main_server())

@st.cache_resource
def start_background_server():
    print("🤖 [5060] 1650 수신용 백그라운드 서버 시작 (포트: 8889)")
    thread = threading.Thread(target=run_ws_server_for_1650, daemon=True)
    thread.start()
    return thread

# =====================================================================
# 메인 클래스 (DualAgentControlCenter)
# =====================================================================


class DualAgentControlCenter:
    def __init__(self):
        # 4060 컴퓨터의 실제 IP 주소 및 웹소켓 엔드포인트 세팅
        self.WSS_4060_URL = "ws://192.168.0.190:8888"
        # 테스트 실제 IP 주소 및 웹소켓 엔드포인트 세팅
        # self.WSS_4060_URL = "ws://localhost:8888"
        
        
        self.planner_prompt = """
        너는 두산 로봇 제어 프로젝트의 '수석 기획자'이자 '시맨틱 매칭(의미론적 추론) 엔진'이야.
        사용자의 명령을 분석하고, 현재 YOLO 센서 데이터 중에서 사용자의 의도를 가장 잘 충족할 수 있는 최적의 물체를 찾아 세부 스케줄(Steps)을 기획해.

        [시맨틱 매칭 및 절대 규칙]
        1. 사용자가 명령한 물체와 완벽히 똑같은 이름이 센서 데이터에 없더라도, 용도나 특성이 가장 비슷해서 대체 가능한 물체가 있다면 그것을 타겟으로 삼아 기획해. (예: '마실 것' -> 'water_bottle', '쓰레기' -> 'can')
        2. 의미적으로 도저히 대체할 물체조차 시야에 없다면, 아래 양식을 완전히 무시하고 오직 "Error: [명령한 물체] 및 대체품을 카메라에서 찾을 수 없습니다." 라고만 출력해.
        3. 타겟 물체가 정해지면, 센서 데이터의 좌표를 바탕으로 아래 [출력 양식]에 맞춰 정확한 스케줄을 작성해.
        4. Steps를 짤 때, 물체를 집거나 놓으러 가기 전에 반드시 Z축으로 SafeZOffset만큼 상승(movel)하는 안전 궤적을 포함해.

        [출력 양식]
        Task: [작업 유형 (예: pick_and_place)]
        Object: [최종 선택된 타겟 물체 이름]
        PickPosition: [X, Y, Z]
        Destination: [목적지 이름]
        PlacePosition: [X, Y, Z]
        SafeZOffset: 100

        Steps:
        1. action=movej, target=[0, 0, 90, 0, 90, 0]
        2. action=open_gripper
        3. action=movel, target=[X, Y, Z + 100]
        4. action=movel, target=[X, Y, Z]
        5. action=close_gripper
        6. action=wait, duration=0.5
        7. action=movel, target=[X, Y, Z + 100]
        """

        self.critic_prompt = """
        너는 두산 로봇(m0609) 제어 코드 안전 검수관이야. 
        아래 코드를 읽고 문법 에러나 충돌 위험이 없으면 오직 "PASS"라고만 출력해.
        만약 에러가 예상되거나 허용되지 않은 함수를 썼다면 "FAIL: [구체적인 에러 원인 및 수정 지시]"를 출력해.
        """
        self.sql_uploader = self._init_db_connector()

    @staticmethod
    @st.cache_resource
    def _init_db_connector():
        try:
            return FirebaseSQLconnetTaskUploader()
        except Exception as e:
            print(f"🚨 PostgreSQL 커넥터 초기화 실패: {e}")
            return None

    def log_to_sql(self, command_text: str, yolo_data_dict: dict, llama_output_text: str):
        if self.sql_uploader:
            self.sql_uploader.upload_log(
                voice_command=command_text,
                yolo_vision_data=yolo_data_dict,
                llama_raw_output=llama_output_text
            )
    
    def render_ui(self):
        st.title("🤖 ROS2 분산형 듀얼 에이전트 제어 센터 (5060 Node)")

        # 백그라운드 수신 서버 실행
        start_background_server()

        st.subheader("👁️ 감각 PC (1650) 데이터 수신부")
        
        # 💡 [핵심 변경] 새로고침 버튼 대신 '자동 동기화 스위치' 적용
        auto_refresh = st.toggle("🔄 실시간 자동 동기화 켜기 (Auto-Sync)", value=True)

        buf_command, buf_yolo = global_sensor_buffer.get_data()

        user_command = st.text_input("음성 명령 입력 (1650에서 자동 수신됨)", buf_command)
        yolo_status = buf_yolo
        st.text(f"현재 카메라 인식 상태 (1650 YOLO): {yolo_status}")
        st.divider()

        if st.button("1단계: 의도 분석 및 코드 생성 요청", key="start_btn"):
            with st.spinner("5060 시맨틱 매칭 엔진 연산 중..."):
                plan_res = ollama.chat(model='llama3', messages=[
                    {'role': 'system', 'content': self.planner_prompt},
                    {'role': 'user', 'content': f"명령: {user_command}\nYOLO 데이터: {yolo_status}"}
                ])
                flowchart = plan_res['message']['content'].strip()

                if "Error:" in flowchart or "에러" in flowchart:
                    st.error(f"🚨 센서 미인식 오류: {flowchart}")
                    return

                st.success("✅ 5060 시맨틱 기획 수립 완료!")
                st.info(f"📋 생성된 마스터 스케줄:\n{flowchart}")
                
                self.log_to_sql(user_command, yolo_status, flowchart)

                final_prompt_for_4060 = f"사용자는 다음과 같은 구조화된 작업 시퀀스를 제공한다.\n\n{flowchart}\n\n너는 Steps 항목만 실제 로봇 동작 코드로 변환한다."

                with st.spinner("📡 웹소켓을 통해 4060 컴퓨터에 코드 최적화 생성 요청 중..."):
                    try:
                        ws = websocket.create_connection(self.WSS_4060_URL, timeout=300)
                        payload = {"action": "generate", "task_input": final_prompt_for_4060}
                        ws.send(json.dumps(payload))
                        response = json.loads(ws.recv())
                        ws.close()
                        draft_code = response.get("code")
                    except Exception as e:
                        st.error(f"❌ 4060 컴퓨터와 통신 실패: {e}")
                        return


                with st.spinner("🔍 5060 감사관 노드 안전 설계 검수 검증 중..."):
                    review_res = ollama.chat(model='llama3', messages=[
                        {'role': 'system', 'content': self.critic_prompt},
                        {'role': 'user', 'content': f"검수할 코드:\n{draft_code}"}
                    ])
                    review = review_res['message']['content']

                    if "PASS" in review.upper():
                        st.success("✅ 5060 감사관 최종 검수 통과! 승인 대기 상태로 전환합니다.")
                        st.session_state['approved_code'] = draft_code
                        st.code(draft_code, language='python')
                    else:
                        st.warning(f"⚠️ 감사관 검증 실패 지적 사항: {review}")
                        st.error("안전 가이드라인 미달로 실로봇 실행 권한을 잠금 처리합니다.")

        if 'approved_code' in st.session_state:
            st.write("👉 RViz/Dart 시뮬레이터의 예상 동적 궤적 안전성을 육안 확인해 주세요.")
            if st.button("▶️ 궤적 검증 확인 완료! 4060으로 실로봇 구동 명령 전송"):
                with st.spinner("📡 4060 컴퓨터로 코드 원격 다운로드 및 실행 명령 전송 중..."):
                    try:
                        ws = websocket.create_connection(self.WSS_4060_URL, timeout=300)
                        payload = {"action": "execute", "code": st.session_state['approved_code']}
                        ws.send(json.dumps(payload))
                        exec_response = json.loads(ws.recv())
                        ws.close()
                        
                        if exec_response.get("exec_status") == "SUCCESS":
                            st.success(exec_response.get("message"))
                        else:
                            st.error(exec_response.get("message"))
                    except Exception as e:
                        st.error(f"❌ 4060 실행 커맨드 전송 에러: {e}")
        # =========================================================
        # 🔄 실시간 자동 동기화 무한 루프 (백그라운드 데이터 화면 반영)
        # =========================================================
        if auto_refresh:
            import time
            time.sleep(1.0)  # 1초마다 화면을 갱신 (부하 방지)
            try:
                st.rerun()   # Streamlit 화면 강제 새로고침
            except AttributeError:
                st.experimental_rerun() # 구버전 Streamlit 호환용  

if __name__ == "__main__":
    app = DualAgentControlCenter()
    app.render_ui()