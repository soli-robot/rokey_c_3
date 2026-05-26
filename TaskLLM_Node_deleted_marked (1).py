import sys
import os
import ctypes

# =====================================================================
# 🚨 1. libcublas.so.12 물리적 강제 로딩 (무조건 최상단 실행)
# =====================================================================
v_env = os.environ.get('VIRTUAL_ENV') or os.path.dirname(os.path.dirname(sys.executable))

cublas_path = os.path.join(v_env, 'lib', 'python3.10', 'site-packages', 'nvidia', 'cublas', 'lib', 'libcublas.so.12')
cudnn_path = os.path.join(v_env, 'lib', 'python3.10', 'site-packages', 'nvidia', 'cudnn', 'lib', 'libcudnn.so.9')

try:
    ctypes.CDLL(cublas_path)
    ctypes.CDLL(cudnn_path)
    print("✅ [Fix] CUDA 12 라이브러리 메모리 강제 로드 성공!")
except Exception as e:
    print(f"❌ [Fix] 라이브러리 로드 실패. 가상환경 경로를 다시 확인하세요: {e}")


# =====================================================================
# 🔇 2. ALSA/JACK 로그 영구 차단 (C-level 에러 핸들러 덮어쓰기)
# =====================================================================
# 파이썬 경고 무시로는 안 되므로, 리눅스 오디오(ALSA)의 에러 출력 함수 자체를 백지로 만듭니다.
ERROR_HANDLER_FUNC = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
def py_error_handler(filename, line, function, err, fmt):
    pass  # 아무것도 출력하지 않음
c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)

try:
    asound = ctypes.cdll.LoadLibrary('libasound.so.2') # Ubuntu 표준
    asound.snd_lib_error_set_handler(c_error_handler)
except OSError:
    try:
        asound = ctypes.cdll.LoadLibrary('libasound.so')
        asound.snd_lib_error_set_handler(c_error_handler)
    except OSError:
        pass

os.environ['AUDIODRIVER'] = 'alsa'
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# --- 기존 경로 설정 ---
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.append(src_dir)

import json
import re
import streamlit as st
import ollama
import websocket  # pip install websocket-client
import asyncio
import threading
import websockets # yolo 수신용

import speech_recognition as sr
from faster_whisper import WhisperModel
# ==================== [삭제된 원본 코드 시작] ====================
# 삭제 사유: 버튼형 STT만 사용하기 위해 백그라운드 STT/파형/중복 로딩 잔재 제거
# [삭제됨] import queue
# [삭제됨] import numpy as np
# [삭제됨] import matplotlib.pyplot as plt
# [삭제됨] import matplotlib.animation as animation
# [삭제됨] import gc
# [삭제됨] import time # time 모듈이 상단에 없다면 추가해 주세요.
# ===================== [삭제된 원본 코드 끝] =====================
import tempfile
# ==================== [삭제된 원본 코드 시작] ====================
# 삭제 사유: 버튼형 STT만 사용하기 위해 백그라운드 STT/파형/중복 로딩 잔재 제거
# [삭제됨] import difflib
# ===================== [삭제된 원본 코드 끝] =====================

# 💡 모델을 매번 불러오지 않도록 캐싱 처리
@st.cache_resource
def load_whisper_model():
    print("⏳ [5060] Whisper 모델 로딩 중... (최초 1회만)")
    # VRAM 확보를 위해 device="cpu" 로 설정
    return WhisperModel("small", device="cpu", compute_type="int8")

def run_single_stt():
    recognizer = sr.Recognizer()
    
    # 1. 마이크 열고 딱 1번만 듣기
    with sr.Microphone() as source:
        # 주변 소음 적응 (0.5초)
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        # 최대 5초 대기, 말하기 시작하면 최대 5초까지만 녹음
        audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
        
    # 2. 녹음된 음성을 임시 파일로 저장
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        tmp_file.write(audio.get_wav_data())
        tmp_filename = tmp_file.name
        
    # 3. Whisper로 텍스트 변환
    model = load_whisper_model()
    segments, _ = model.transcribe(tmp_filename, beam_size=5, language="ko")
    text = "".join([segment.text for segment in segments]).strip()
    
    # 4. 임시 파일 삭제 후 텍스트 반환
    os.remove(tmp_filename)
    return text


# PostgreSQL 인프라 연동 컴포넌트 임포트
try:
    from FireBaseDB.fireSQLconnet import FirebaseSQLconnetTaskUploader
except ImportError:
    st.warning("⚠️ DB 모듈을 찾을 수 없습니다. 테스트 모드로 진행합니다.")

# =====================================================================
# ==================== [삭제된 원본 코드 시작] ====================
# 삭제 사유: 버튼형 STT만 사용하기 위해 백그라운드 STT/파형/중복 로딩 잔재 제거
# [삭제됨] # 🔇 [핵심] JACK 및 ALSA 디버그 로그 폭탄 무음 처리 (C-level 파일 디스크립터 제어)
# [삭제됨] # =====================================================================
# [삭제됨] class SuppressAudioLogs:
    # [삭제됨] """
    # [삭제됨] PortAudio가 마이크를 초기화할 때 터미널에 뿌리는 C-level JACK 에러(stderr)를
    # [삭제됨] /dev/null로 일시적으로 던져버려서 터미널을 깔끔하게 유지하는 컨텍스트 매니저입니다.
    # [삭제됨] """
    # [삭제됨] def __enter__(self):
        # [삭제됨] self.null_fd = os.open(os.devnull, os.O_RDWR)
        # [삭제됨] self.save_fd = os.dup(2)
        # [삭제됨] os.dup2(self.null_fd, 2)
        # [삭제됨] return self
# [삭제됨]
    # [삭제됨] def __exit__(self, *_):
        # [삭제됨] os.dup2(self.save_fd, 2)
        # [삭제됨] os.close(self.null_fd)
        # [삭제됨] os.close(self.save_fd)
# [삭제됨]
# [삭제됨]
# [삭제됨] # =====================================================================
# ===================== [삭제된 원본 코드 끝] =====================
# 🌐 [스레드 안전] yolo 감각 4060 PC에서 들어오는 실시간 전역 버퍼 클래스
# =====================================================================
class SensoryDataBuffer:
    def __init__(self):
        self.command = "대기 중... (4060 PC의 음성 명령을 기다립니다)"
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
# ==================== [삭제된 원본 코드 시작] ====================
# 삭제 사유: 버튼형 STT만 사용하기 위해 백그라운드 STT/파형/중복 로딩 잔재 제거
# [삭제됨]
# [삭제됨] # 실시간 통신 및 큐 처리 객체
# [삭제됨] audio_queue = queue.Queue()
# [삭제됨] text_task_queue = queue.Queue()
# [삭제됨] PLOT_CHUNK = 2048  
# [삭제됨]
# [삭제됨] # 1. Faster-Whisper 모델 로드 (CPU 및 int8 최적화)
# [삭제됨] print("⚡ [CPU] STT 모델을 RAM에 로드 중... (int8 최적화)")
# [삭제됨] model = WhisperModel("medium", device="cpu", compute_type="int8")
# [삭제됨] # 2. 마이크 및 Recognizer 초기화
# [삭제됨] recognizer = sr.Recognizer()
# [삭제됨] recognizer.dynamic_energy_threshold = False  # 감도 자동 조절 해제
# [삭제됨] recognizer.energy_threshold = 300            # 고정 음성 인식 감도 수치
# [삭제됨] recognizer.pause_threshold = 0.6         # (기본값 0.8) 말을 멈춘 후 0.4초만 지나면 즉시 문장 종료로 간주하고 STT로 넘김
# [삭제됨] recognizer.non_speaking_duration = 0.2   # (기본값 0.5) 오디오 파일 앞뒤에 붙는 불필요한 침묵(여백) 녹음 시간 단축
# [삭제됨]
# [삭제됨]
# [삭제됨] # =====================================================================
# [삭제됨] # 🚀 마이크 
# [삭제됨] # =====================================================================
# [삭제됨]
# [삭제됨]
# [삭제됨] class ObservableMicrophone(sr.Microphone):
    # [삭제됨] """
    # [삭제됨] 하나의 오디오 스트림을 열고, 데이터를 읽을 때마다 
    # [삭제됨] STT 모듈과 실시간 시각화 큐(audio_queue) 양쪽에 데이터를 공급하는 커스텀 마이크 클래스
    # [삭제됨] """
    # [삭제됨] def __enter__(self):
        # [삭제됨] super().__enter__()
        # [삭제됨] # 원래의 오디오 읽기 함수 저장
        # [삭제됨] self._original_read = self.stream.read
# [삭제됨]
        # [삭제됨] # 읽기 함수 가로채기 (래핑) - 오류를 유발한 파라미터 제거
        # [삭제됨] def read_wrapper(size):
            # [삭제됨] # 1. 마이크에서 원본 바이트 데이터 읽기 (순수 size만 전달)
            # [삭제됨] chunk_bytes = self._original_read(size)
# [삭제됨]
            # [삭제됨] # 2. 시각화를 위해 numpy 배열로 변환 후 큐에 복사본 밀어넣기
            # [삭제됨] try:
                # [삭제됨] samples = np.frombuffer(chunk_bytes, dtype=np.int16)
                # [삭제됨] if len(samples) > 0:
                    # [삭제됨] audio_queue.put_nowait(samples)
            # [삭제됨] except queue.Full:
                # [삭제됨] pass
# [삭제됨]
            # [삭제됨] # 3. STT 모듈 처리를 위해 원본 데이터 그대로 반환
            # [삭제됨] return chunk_bytes
# [삭제됨]
        # [삭제됨] # 가로챈 함수로 덮어씌우기
        # [삭제됨] self.stream.read = read_wrapper
        # [삭제됨] return self
# [삭제됨]
# [삭제됨] # ---------------------------------------------------------------------
# [삭제됨] # 📊 Matplotlib 실시간 파형 GUI (Main Thread)
# [삭제됨] # ---------------------------------------------------------------------
# [삭제됨] def run_realtime_plot():
    # [삭제됨] # 그래프 초기 생성 시 배경색 안정적 매핑
    # [삭제됨] fig, ax = plt.subplots(figsize=(10, 4), facecolor='#111111')
# [삭제됨]
    # [삭제됨] x = np.arange(0, PLOT_CHUNK)
    # [삭제됨] y = np.zeros(PLOT_CHUNK)
    # [삭제됨] line, = ax.plot(x, y, color='#00FF66', lw=1.5) 
# [삭제됨]
    # [삭제됨] ax.set_title("1650 Sensor PC - Audio Input Real-Time Test Dashboard", color='white', fontsize=12, pad=10)
    # [삭제됨] ax.set_facecolor('#111111') 
# [삭제됨]
    # [삭제됨] ax.set_ylim(-16000, 16000) 
    # [삭제됨] ax.set_xlim(0, PLOT_CHUNK)
    # [삭제됨] ax.get_xaxis().set_visible(False) 
    # [삭제됨] ax.tick_params(axis='y', colors='white')
    # [삭제됨] ax.grid(True, color='#333333', linestyle='--')
# [삭제됨]
    # [삭제됨] text_db = ax.text(0.02, 0.9, '', transform=ax.transAxes, color='#00FF66', weight='bold')
# [삭제됨]
    # [삭제됨] # 🟢 롤링 버퍼 생성 (전역 상태 유지)
    # [삭제됨] wave_data = np.zeros(PLOT_CHUNK)
# [삭제됨]
    # [삭제됨] def update_plot(frame):
        # [삭제됨] nonlocal wave_data
        # [삭제됨] data_present = False
# [삭제됨]
        # [삭제됨] # 큐에 쌓여 있는 실시간 스트리밍 조각들을 결합하여 파형 업데이트
        # [삭제됨] while not audio_queue.empty():
            # [삭제됨] try:
                # [삭제됨] samples = audio_queue.get_nowait()
                # [삭제됨] if len(samples) > 0:
                    # [삭제됨] # 새로운 데이터 길이만큼 왼쪽으로 밀어내고, 오른쪽 끝에 새 데이터 삽입
                    # [삭제됨] wave_data = np.roll(wave_data, -len(samples))
                    # [삭제됨] wave_data[-len(samples):] = samples
                    # [삭제됨] data_present = True
            # [삭제됨] except queue.Empty:
                # [삭제됨] break
# [삭제됨]
        # [삭제됨] if data_present:
            # [삭제됨] line.set_ydata(wave_data)
            # [삭제됨] rms = np.sqrt(np.mean(wave_data.astype(np.float64)**2)) + 1e-5
            # [삭제됨] db = 20 * np.log10(rms)
            # [삭제됨] text_db.set_text(f"Mic Input Level: {db:.1f} dB (RMS)")
        # [삭제됨] else:
            # [삭제됨] # 입력 소리가 비었을 때는 천천히 감쇠하도록 스무딩 (0.7 -> 0.9로 변경하여 더 부드럽게)
            # [삭제됨] wave_data = wave_data * 0.9
            # [삭제됨] line.set_ydata(wave_data)
# [삭제됨]
        # [삭제됨] return line, text_db
# [삭제됨]
    # [삭제됨] ani = animation.FuncAnimation(fig, update_plot, blit=True, interval=25, cache_frame_data=False)
    # [삭제됨] plt.tight_layout()
    # [삭제됨] plt.show()
# [삭제됨]
# ===================== [삭제된 원본 코드 끝] =====================

# =====================================================================
# 🚀 4060으로부터 데이터를 수신하는 백그라운드 웹소켓 서버
# =====================================================================
def run_ws_server_for_1650():
    async def handler(websocket):
        print("📡 [5060] 4060 감각 PC 연결 수립 완료!")
        try:
            async for message in websocket:
                data = json.loads(message)
                print(f"📥 [5060] 1650으로부터 데이터 수신: {data}")
                
                # 💡 [핵심 변경] 실제 들어오는 키(transformed_positions)를 잡아냅니다.
                cmd = data.get("command")
                # 만약 'yolo' 키로 들어오면 yolo를, 아니면 'transformed_positions'를 사용
                yolo = data.get("transformed_positions") or data.get("yolo") 
                
                global_sensor_buffer.update(cmd, yolo)
                    
        except websockets.exceptions.ConnectionClosed:
            print("🛑 [5060] 1650 감각 PC 연결 종료")

    async def main_server():
        async with websockets.serve(handler, "0.0.0.0", 8888):
            await asyncio.Future()

    asyncio.run(main_server())

@st.cache_resource
def start_background_server():
    print("🤖 [5060] 1650 수신용 백그라운드 서버 시작 (포트: 8888)")
    thread = threading.Thread(target=run_ws_server_for_1650, daemon=True)
    thread.start()
    return thread

class DualAgentControlCenter:
    def __init__(self):
        self.WSS_4060_URL = "ws://192.168.0.190:8888"

        # 1. Macro Prompt: 전체 작업의 큰 흐름(Sub-tasks) 자율 기획
        self.macro_prompt = """
        너는 두산 로봇 제어 프로젝트의 '총괄 디렉터'야.
        사용자의 음성 명령(Whisper)만 보고 큰 단위의 명령을 구현 후, 목표를 달성하기 위해 필요한 전체 작업(Sub-task)들을 순서대로 기획해.
        
        [사용 가능한 사내 제작 모듈 (Bringup 리스트)]
        - [Bring-1] (YOLO_Vision): 카메라를 켜고 특정 객체의 실시간 좌표를 계속 추적함. (target 명시 필요)

        
        [절대 규칙 - 무조건 지킬 것]
        1. 인사말, 설명, 과정 등 어떠한 자연어 텍스트도 절대 출력하지 마.
        2. 오직 아래 양식의 순수 JSON 배열(Array)만 딱 출력해.
        3. 'type' 필드의 값은 반드시 큰따옴표로 묶인 문자열이어야 해. (예: "[Task]")

        [핵심 기획 로직: 선행 조건(Prerequisite) 판단]
        현재 주어진 YOLO 데이터(global_sensor_buffer)에 사용자가 언급한 물체의 좌표가 **없다면**,
        로봇 팔이 움직이는 [Task] 작업을 지시하기 **전**에, 반드시 **무조건 카메라를 켜서 좌표를 찾는 [Bring-1] 작업을 1단계 스텝으로 먼저 기획**해야 해.

        [작업 타입 분류 규칙]
        - 위 모듈을 쓸 때는 'type'에 "[Bring-1]" 처럼 해당 태그만 단순하게 적어. (action 필드 불필요)
        - 로봇 팔이 직접 물건을 옮기는 물리적 동작은 'type'에 "[Task]"를 적고 세부 action을 적어.
        
        [절대 규칙 - 무조건 지킬 것]
        1. 인사말, 설명, 과정 등 어떠한 자연어 텍스트도 절대 출력하지 마.
        2. 오직 아래 양식의 순수 JSON 배열(Array)만 딱 출력해.
        3. 'type' 필드의 값은 반드시 큰따옴표로 묶인 문자열이어야 해. (예: "[Task]", "[Bring-1]")
        
        [출력 양식 예시 JSON Array (사용자 명령: "수건 세탁해줘"일 때)]
        [
            {"step": 1, "type": "[Bring-1]", "target": "수건"},
            {"step": 2, "type": "[Task]", "action": "pick_and_place", "target": "수건", "destination": "세탁기"}
        ]
        """
        
        # 2. Micro Prompt: 단일 작업에 대한 세부 관절/좌표 궤적 기획
        self.micro_prompt = """
        너는 로봇의 '단일 모션 플래너'야.
        총괄 디렉터가 넘겨준 [현재 진행할 단 하나의 스텝] 정보만 보고, 4060 코더가 파이썬 코드를 짤 수 있도록 세부 지시서를 작성해.
        
        [강력 절대 규칙 - 무조건 지킬 것]
        1. "알겠습니다", "분석 결과", "Since the type is...", "I will execute..." 등 어떠한 한글/영어 인사말이나 부연 설명도 절대 금지.
        2. 네 생각이나 과정을 서술하지 마.
        3. 오직 아래의 [출력 양식] 중 하나만 선택해서, {변수} 값만 바꿔서 그대로 텍스트로 출력해. 다른 글자는 단 한 글자도 추가하지 마.
        4. 첫 단계는 무조건 [Bring-1]로 시작해.

        ====================================================
        ▶ 상황 A: type이 '[Bring-X]' (예: [Bring-1]) 인 경우
        - 관절 궤적을 절대 짜지 마.
        - 오직 아래 문장 딱 한 줄만 출력해. (앞뒤로 빈 줄도 넣지 마)
        
        [상황 A 출력 양식]
        [Bring-1]
        ====================================================
        ▶ 상황 B: type이 '[Task]' 이고 pick_and_place 작업인 경우
        - 하드웨어 충돌 방지를 위해 반드시 아래의 '8단계 ㄷ자 접근/퇴각 무빙' 시퀀스를 엄격히 지켜서 Steps를 짜야 해.
        - YOLO 데이터에서 제공된 타겟의 '원 좌표'와 '안전 고도(SafeZOffset)가 더해진 좌표'를 활용해.
        
        [8단계 ㄷ자 무빙 시퀀스]
        ① [접근] 잡을 물건의 '위(Offset)' 좌표로 이동
        ② [하강] 잡을 물건의 '원' 좌표로 이동
        ③ [파지] close_gripper
        ④ [상승] 다시 물건 '위(Offset)' 좌표로 수직 상승
        ⑤ [이동] 놓을 위치의 '위(Offset)' 좌표로 이동
        ⑥ [하강] 놓을 위치의 '원' 좌표로 이동
        ⑦ [놓기] open_gripper
        ⑧ [복귀] 다시 놓을 위치 '위(Offset)' 좌표로 상승
           
        [상황 B 출력 양식 예시]
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
        ====================================================
        """
        
        # 3. Critic Prompt: 4060이 짠 코드를 검수
        self.critic_prompt = """
        너는 두산 로봇(m0609) 제어 코드 안전 검수관이야. 
        아래 코드를 읽고 문법 에러나 충돌 위험이 없으면 오직 "PASS"라고만 출력해.
        만약 에러가 예상되거나 허용되지 않은 함수를 썼다면 "FAIL: [구체적인 에러 원인 및 수정 지시]"를 출력해.
        """
        
        self.sql_uploader = None  # self._init_db_connector()

    @staticmethod
    @st.cache_resource
    def _init_db_connector():
        try:
            return FirebaseSQLconnetTaskUploader()
        except Exception as e:
            print(f"🚨 PostgreSQL 커넥터 초기화 실패: {e}")
            return None
        # ==================== [삭제된 원본 코드 시작] ====================
        # 삭제 사유: 버튼형 STT만 사용하기 위해 백그라운드 STT/파형/중복 로딩 잔재 제거
        # [삭제됨] pass
        # ===================== [삭제된 원본 코드 끝] =====================

    def log_to_sql(self, command_text: str, yolo_data_dict: dict, llama_output_text: str):
        if self.sql_uploader:
            self.sql_uploader.upload_log(
                voice_command=command_text,
                yolo_vision_data=yolo_data_dict,
                llama_raw_output=llama_output_text
            )
        pass

    # 👇 [여기에 추가!] 4060과 통신하고 '결과'를 받아오는 만능 함수
    def _send_to_4060(self, payload: dict):
        try:
            ws = websocket.create_connection(self.WSS_4060_URL, timeout=300)
            ws.send(json.dumps(payload))
            
            # 4060이 응답을 줄 때까지 기다렸다가 받음
            response_raw = ws.recv()
            ws.close()
            
            return json.loads(response_raw)
            
        except Exception as e:
            st.error(f"🚨 4060 통신 실패: {e}")
            return None

    # 4060 통신 및 검수 로직 (누락되었던 부분 복구)
    def _communicate_with_4060(self, final_prompt_for_4060):
        max_critic_retries = 3
        final_code = ""

        with st.spinner("📡 4060 코딩 생성 및 5060 감사관 검수 진행 중..."):
            for i in range(max_critic_retries):
                payload = {"action": "generate", "prompt": final_prompt_for_4060}
                response = self._send_to_4060(payload)
                if not response:
                    return None
                draft_code = response.get("code", "")

                # 5060 감사관 검수
                review_res = ollama.chat(model='llama3', messages=[
                    {'role': 'system', 'content': self.critic_prompt},
                    {'role': 'user', 'content': f"검수할 코드:\n{draft_code}"}
                ])
                review = review_res['message']['content']
                
                if "PASS" in review.upper():
                    st.success("✅ 5060 감사관 검수 통과! (무결성 확보)")
                    final_code = draft_code
                    break
                else:
                    st.warning(f"⚠️ 감사관 지적 사항 반영 중 ({i+1}/{max_critic_retries}): {review}")
                    final_prompt_for_4060 += f"\n\n[수정 지시]: {review}"

        return final_code if final_code else None

    def render_ui(self):
        st.title("🤖 ROS2 단계별 자율 제어 센터 (Step-by-Step)")

        start_background_server()

        st.subheader("👁️ 감각 PC (1650) 데이터 수신부")
        
        # 새로고침과 초기화 버튼
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("🔄 데이터 새로고침"):
                st.rerun()
        with col2:
            if st.button("🛑 전체 작업 초기화"):
                st.session_state['task_list'] = []
                st.session_state['current_step_idx'] = 0
                st.session_state['current_step_code'] = None
                st.session_state['yolo_data'] = None
                st.rerun()
                
        auto_refresh = st.toggle("🔄 실시간 자동 동기화 켜기 (Auto-Sync)", value=True)

        buf_command, buf_yolo = global_sensor_buffer.get_data()
        
        # ==========================================
        # 💡 [변경됨] 음성 명령 입력 UI (버튼형)
        # ==========================================
        st.divider()
        st.markdown("#### 🎙️ 로봇 음성 제어")
        
        col_mic, col_txt = st.columns([1, 4])
        with col_mic:
            if st.button("🎤 음성 명령 듣기"):
                with st.spinner("듣고 있습니다... 말씀해주세요!"):
                    try:
                        text = run_single_stt()
                        if text:
                            st.session_state['stt_command'] = text
                            st.success("인식 완료!")
                        else:
                            st.warning("목소리가 인식되지 않았습니다.")
                    except sr.WaitTimeoutError:
                        st.error("입력 시간이 초과되었습니다.")
                    except Exception as e:
                        st.error(f"마이크 에러: {e}")
                        
        # 텍스트 박스 기본값을 방금 인식한 STT 텍스트로 채움
        default_cmd = st.session_state.get('stt_command', buf_command)
        user_command = col_txt.text_input("현재 명령:", value=default_cmd)
        
        # ==========================================
        
        current_yolo = st.session_state.get('yolo_data') or buf_yolo
        default_yolo_str = json.dumps(current_yolo, indent=4, ensure_ascii=False) if current_yolo else "{}"
        
        yolo_input_str = st.text_area(
            "📷 현재 카메라 인식 상태 (1650 PC 실시간 수신 데이터):", 
            value=default_yolo_str,
            height=200
        )

        try:
            yolo_status = json.loads(yolo_input_str)
        except json.JSONDecodeError:
            st.error("⚠️ 올바른 JSON 형식이 아닙니다.")
            yolo_status = {}
            
        st.divider()

        # ==========================================
        # 💡 [핵심] 상태 기억(Session State) 변수 초기화
        # ==========================================
        if 'yolo_data' not in st.session_state:
            st.session_state['yolo_data'] = None
        if 'task_list' not in st.session_state:
            st.session_state['task_list'] = []
        if 'current_step_idx' not in st.session_state:
            st.session_state['current_step_idx'] = 0
        if 'current_step_code' not in st.session_state:
            st.session_state['current_step_code'] = None

        # ------------------------------------------
        # 1단계: 전체 작업 기획 (Macro) - 한 번만 실행됨
        # ------------------------------------------
        if not st.session_state['task_list']:
            if st.button("▶️ 1단계: 사용자 의도 분석 및 전체 Task 기획"):
                with st.spinner("🧠 총괄 디렉터가 큰 작업 순서를 기획 중..."):
                    try:
                        macro_res = ollama.chat(model='llama3', messages=[
                            {'role': 'system', 'content': self.macro_prompt},
                            {'role': 'user', 'content': f"명령: {user_command}\nYOLO 데이터: {yolo_status}"}
                        ])
                        
                        macro_output = macro_res['message']['content'].strip()
                        
                        match = re.search(r'\[.*\]', macro_output, re.DOTALL)
                        if not match:
                            raise ValueError("AI 출력에서 JSON 배열을 찾을 수 없습니다.")
                            
                        json_str = match.group(0)
                        json_str = json_str.replace('"type": [Task]', '"type": "[Task]"')
                        
                        task_list = json.loads(json_str)
                        
                        # 💡 기획된 리스트를 메모리에 저장하고 화면 새로고침
                        st.session_state['task_list'] = task_list
                        st.session_state['current_step_idx'] = 0
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"🚨 기획 데이터 파싱 에러: {e}")
                        st.warning(f"원본 출력 데이터:\n{macro_output}")
        
        # ------------------------------------------
        # 2단계: 스텝 바이 스텝 (Micro ➔ 4060 ➔ 인간 승인)
        # ------------------------------------------
        else:
            task_list = st.session_state['task_list']
            current_idx = st.session_state['current_step_idx']

            st.success(f"✅ 총 {len(task_list)}개의 세부 작업 기획 완료!")
            st.json(task_list)
            st.divider()

            # 아직 완료되지 않은 스텝이 남아있다면
            if current_idx < len(task_list):
                current_task = task_list[current_idx]
                st.subheader(f"📍 현재 진행 스텝: {current_idx + 1} / {len(task_list)}")
                st.info(f"작업 유형: {current_task.get('type')} | 액션: {current_task.get('action')} | 대상: {current_task.get('target')}")

                if current_task.get('type') == "[Bring-1]":
                    if st.button("👁️ 로봇 스캔 시작"):
                        payload = {"action": "generate", "prompt": "[Bring-1]", "target": current_task.get('target')}
                        result = self._send_to_4060(payload)
                        if result and result.get("status") == "scan_result":
                            # 4060에서 받은 데이터를 yolo 데이터로 갱신
                            st.session_state['yolo_data'] = result.get("data")
                            st.success("✅ 스캔 완료!")
                            st.session_state['current_step_idx'] += 1
                            st.rerun()

                elif current_task.get('type') == "[Task]":
                    # 2-1. 해당 스텝에 대한 코드가 아직 안 만들어졌을 때
                    if st.session_state['current_step_code'] is None:
                        if st.button(f"⚙️ 스텝 {current_idx + 1} 모션 플래닝 및 4060 코드 생성"):
                            
                            action = current_task.get('action')
                            target = current_task.get('target')
                            dest = current_task.get('destination')
                            target_coord = yolo_status.get(target, "좌표 없음")
                            dest_coord = yolo_status.get(dest, "좌표 없음") if dest else None
                            
                            with st.spinner(f"🔍 [Micro] 스텝 {current_idx + 1} 세부 궤적 계산 및 코드 생성 중..."):
                                # 👇 2. LLM이 ㄷ자 무빙을 완벽하게 이해할 수 있도록 전달 메시지를 강화합니다.
                                user_msg = f"작업타입: {current_task.get('type')}, 작업: {action}, 대상: {target}\n"
                                user_msg += f"대상 좌표 정보(원 좌표 및 오프셋 포함): {target_coord}\n"
                                
                                if dest_coord and dest_coord != "좌표 없음":
                                    user_msg += f"목적지: {dest}, 목적지 좌표 정보: {dest_coord}"
                                    
                                micro_res = ollama.chat(model='llama3', messages=[
                                    {'role': 'system', 'content': self.micro_prompt},
                                    {'role': 'user', 'content': user_msg}
                                ])
                                
                                micro_output = micro_res['message']['content'].strip()
                                st.text_area("생성된 단일 모션 스케줄", micro_output, height=150)
                                
                                # 2. 4060에 코드 생성 요청 및 검수
                                final_prompt = f"다음 단일 스텝의 궤적을 파이썬 코드로 변환해라.\n\n{micro_output}"
                                final_code = self._communicate_with_4060(final_prompt)
                                
                                if final_code:
                                    # 💡 생성된 코드를 저장하고 화면 새로고침
                                    st.session_state['current_step_code'] = final_code
                                    st.rerun()
                                else:
                                    st.error("🚨 4060 코드 생성/검수 실패")

                    # 2-2. 코드가 생성되어 인간의 승인을 기다릴 때
                    else:
                        st.success("✅ 5060 검수 완료! 아래 코드를 확인해 주세요.")
                        st.code(st.session_state['current_step_code'], language='python')
                        
                        if st.button(f"▶️ [승인] 실로봇 구동 (스텝 {current_idx + 1} 실행)"):
                            with st.spinner("📡 4060으로 실행 명령 전송 중..."):
                                try:
                                    payload = {"action": "execute", "code": st.session_state['current_step_code']}
                                    response = self._send_to_4060(payload)
                                    
                                    if response:
                                        # 💡 만약 응답에 YOLO 업데이트 데이터가 있다면?
                                        if response.get("status") == "scan_result":
                                            new_yolo = response.get("data")
                                            # 전역 버퍼를 업데이트해서 GUI에 좌표가 바로 뜨게 함
                                            global_sensor_buffer.update(command=None, yolo=new_yolo)
                                            st.success("✅ 4060으로부터 새 좌표를 수신했습니다!")
                                            st.rerun() # 새로고침해서 좌표 업데이트 반영
                                        
                                        elif response.get("exec_status") == "SUCCESS":
                                            st.success(f"스텝 {current_idx + 1} 실행 성공!")
                                            
                                            # 💡 [가장 중요] 성공 시 다음 스텝으로 넘어가기 위해 상태 업데이트
                                            st.session_state['current_step_idx'] += 1
                                            st.session_state['current_step_code'] = None # 코드 초기화
                                            st.rerun() 
                                            
                                        else:
                                            st.error(f"❌ 4060 실행 에러: {response.get('message')}")
                                except Exception as e:
                                    st.error(f"❌ 통신 에러: {e}")

            # 모든 스텝이 완료되었을 때
            else:
                st.balloons()
                st.success("🎉 모든 작업(Sub-tasks)이 성공적으로 완료되었습니다!")
                if st.button("🔄 새로운 명령 받기 (초기화)"):
                    st.session_state['task_list'] = []
                    st.session_state['current_step_idx'] = 0
                    st.session_state['current_step_code'] = None
                    st.session_state['yolo_data'] = None
                    st.rerun()


# 2. 메인 웹 UI 렌더링
app = DualAgentControlCenter()
app.render_ui()
