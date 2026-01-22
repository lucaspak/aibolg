import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import ToastNotification
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
import subprocess
import os
import sys
import json
import threading
import time
import requests
import hmac
import hashlib
import base64
import urllib.parse
import re
from collections import deque
from datetime import datetime
from PIL import Image, ImageTk, ImageDraw
import io
from collections import deque
from dotenv import load_dotenv
from ttkbootstrap.widgets.tableview import Tableview

# Configure Gemini Client - Initially None, will be set after loading config
client = None
CONFIG_FILE = "config.json"
SESSION_FILE = "session_data.json"

# --- [데이터] UI용 카테고리 ---
APP_CATEGORIES = [
    "문학·책", "영화", "미술·디자인", "공연·전시", "음악", "드라마", "스타·연예인",
    "만화·애니", "방송", "일상·생각", "육아·결혼", "반려동물", "좋은글·이미지", "패션·미용",
    "인테리어·DIY", "요리·레시피", "상품리뷰", "원예·재배", "게임", "스포츠", "사진",
    "자동차", "취미", "국내여행", "세계여행", "맛집", "IT·컴퓨터", "사회·정치",
    "IT/테크", "육아/교육", "경제/비즈니스", "자기계발",
]

# --- 네이버 API 실시간 통신 유틸리티 (골든키워드채굴기_0121 참조) ---
def generate_naver_signature(secret_key, timestamp, method, request_uri):
    message = f"{timestamp}.{method}.{request_uri}"
    h = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
    return base64.b64encode(h.digest()).decode('utf-8')

def get_naver_keyword_stats(access_key, secret_key, customer_id, hint_keywords):
    request_uri = "/keywordstool"
    method = "GET"
    timestamp = str(int(time.time() * 1000))
    signature = generate_naver_signature(secret_key, timestamp, method, request_uri)
    headers = {
        "X-Timestamp": timestamp,
        "X-API-KEY": access_key,
        "X-Customer": customer_id,
        "X-Signature": signature
    }
    params = {"hintKeywords": ",".join(hint_keywords), "showDetail": "1"}
    url = f"https://api.naver.com{request_uri}"
    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

def get_naver_document_count(keyword, client_id, client_secret):
    encText = urllib.parse.quote(keyword)
    url = f"https://openapi.naver.com/v1/search/blog?query={encText}&display=1"
    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json().get("total", 0)


class MarketingWizardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("마케팅 캡틴 (Marketing Captain AI) - Premium")
        self.root.geometry("1100x900")
        
        # Shared Data Store (Initialize before loading config)
        self.data = {
            "customer": "",
            "character": "",
            "synopsis": "",
            "draft": "",
            "final_script": "",
            "persona_style": "Friendly",
            "story_strategy": "Standard",
            "naver_api": {}, # Naver API credentials
            "target_topic": "", # Step 0에서 넘어온 핵심 주제
            "series_parts": {
                "1": {"topic": "", "content": "", "image_prompts": []},
                "2": {"topic": "", "content": "", "image_prompts": []},
                "3": {"topic": "", "content": "", "image_prompts": []},
                "4": {"topic": "", "content": "", "image_prompts": []}
            },
            "current_part": "1"
        }

        # API Key management
        self.api_key = self.load_config()
        self.load_session() # Load previous session if exists
        
        self.create_widgets()
        self.restore_ui_from_data() # Restore data into widgets
        self.setup_auto_save()      # Setup triggers
        
    def create_widgets(self):
        # 1. Main Header Area
        header_frame = tb.Frame(self.root, padding="20 20 20 10")
        header_frame.pack(fill=X)
        
        title = tb.Label(header_frame, text="✨ 마케팅 캡틴 (Marketing Captain)", font=("Segoe UI", 24, "bold"), bootstyle="primary")
        title.pack(anchor="w")
        
        subtitle = tb.Label(header_frame, text="초등학생도 따라하는 '무자동' 블로그/스피치 완성 시스템 (빈칸으로 두면 AI가 알아서 해줍니다)", font=("Segoe UI", 11), bootstyle="secondary")
        subtitle.pack(anchor="w", pady=(5, 0))

        # 2. Notebook (Tabs)
        self.notebook = tb.Notebook(self.root, bootstyle="primary")
        self.notebook.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Create Tabs
        self.tab0 = self.create_step_tab(
            "Step 0. 황금 키워드 채굴",
            "포스팅 기획 전, 시장성이 있는 키워드를 발굴합니다.",
            self.build_step0_ui
        )
        self.tab1 = self.create_step_tab(
            "1단계: 꿈의 고객 찾기", 
            "내가 도와줄 '단 한 사람'은 누구일까요?",
            self.build_step1_ui
        )
        self.tab2 = self.create_step_tab(
            "2단계: 매력적인 캐릭터", 
            "사람들이 나를 왜 좋아할까요? 나의 '역할'을 정해봅시다.",
            self.build_step2_ui
        )
        self.tab3 = self.create_step_tab(
            "3단계: 4부작 드라마", 
            "고객과 내가 만나는 이야기를 넷플릭스 드라마처럼 짜봅시다.",
            self.build_step3_ui
        )
        self.tab4 = self.create_step_tab(
            "4단계: 스토리 연금술", 
            "장면 하나하나에 생생한 숨결을 불어넣습니다.",
            self.build_step4_ui
        )
        self.tab5 = self.create_step_tab(
            "5단계: 마케팅 캡틴 (최종)", 
            "모든 조각을 모아, 고객의 마음을 훔치는 편지를 완성합니다.",
            self.build_step5_ui
        )
        self.tab_settings = self.create_step_tab(
            "설정: API Key 관리",
            "네이버 및 Google API 키를 설정하고 저장합니다.",
            self.build_settings_ui
        )

        self.notebook.add(self.tab0, text="Step 0. 키워드 채굴")
        self.notebook.add(self.tab1, text="Step 1. 꿈의 고객")
        self.notebook.add(self.tab2, text="Step 2. 캐릭터")
        self.notebook.add(self.tab3, text="Step 3. 드라마")
        self.notebook.add(self.tab4, text="Step 4. 연금술")
        self.notebook.add(self.tab5, text="Step 5. 최종완성")
        self.notebook.add(self.tab_settings, text="⚙️ 설정")

    def create_step_tab(self, title, subtitle, build_func):
        frame = tb.Frame(self.notebook)
        
        canvas = tb.Canvas(frame)
        scrollbar = tb.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scroll_frame = tb.Frame(canvas, padding=20)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=1020)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        card = tb.Labelframe(scroll_frame, text=title, padding=20, bootstyle="default")
        card.pack(fill=BOTH, expand=True)
        
        tb.Label(card, text=subtitle, font=("Segoe UI", 11), bootstyle="secondary").pack(anchor="w", pady=(0, 20))
        
        build_func(card)
        
        return frame

    def decode_bytes(self, data):
        if not data: return ""
        if isinstance(data, str): return data
        for enc in ['utf-8', 'cp949', 'euc-kr']:
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
        return data.decode('utf-8', errors='replace')

    def run_skill(self, skill_path, args, callback, stream_callback=None):
        """외부 스킬(Python)을 실행하고 결과를 콜백으로 전달"""
        def task():
            try:
                # Use sys.executable -u to ensure unbuffered output for real-time logs
                cmd = [sys.executable, "-u", skill_path] + args
                
                # Use Popen for real-time output
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=False, # Use bytes to detect encoding
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                # Thread for stderr (real-time logs/data)
                def watch_output(pipe):
                    try:
                        for line in iter(pipe.readline, b''):
                            if not line: break
                            decoded = self.decode_bytes(line).strip()
                            if decoded and stream_callback:
                                # Split multiple messages if they come in one chunk
                                for msg in decoded.split('\n'):
                                    if msg.strip():
                                        self.root.after(0, lambda m=msg.strip(): stream_callback(m))
                    except (ValueError, OSError):
                        pass
                
                stderr_thread = threading.Thread(target=watch_output, args=(process.stderr,), daemon=True)
                stderr_thread.start()
                
                # Capture stdout
                stdout_bytes, _ = process.communicate()
                stdout = self.decode_bytes(stdout_bytes)
                
                if process.returncode == 0:
                    if callback and stdout is not None: 
                        self.root.after(0, lambda: callback(stdout.strip()))
                else:
                    self.root.after(0, lambda: self.update_log(f"❌ 스킬 실행 실패 (Exit Code {process.returncode})"))
                    if callback: self.root.after(0, lambda: callback(None)) # Notify failure to caller
            except Exception as e:
                self.root.after(0, lambda m=str(e): self.update_log(f"❌ 스킬 호출 오류: {m}"))
                if callback: self.root.after(0, lambda: callback(None))

        threading.Thread(target=task, daemon=True).start()

    # --- UI Builders ---

    def create_question_block(self, parent, question, guide, variable_name):
        container = tb.Frame(parent)
        container.pack(fill=X, pady=(0, 20))
        
        tb.Label(container, text=question, font=("Segoe UI", 12, "bold"), bootstyle="inverse-dark", padding=5).pack(anchor="w")
        tb.Label(container, text=f"💡 {guide}", font=("Segoe UI", 10, "bold"), bootstyle="dark", padding=(5, 5)).pack(anchor="w")
        
        entry = tb.Entry(container, font=("Segoe UI", 11))
        entry.pack(fill=X, pady=(5, 0))
        
        setattr(self, variable_name, entry)

    def create_action_button(self, parent, text, command, style="primary"):
        btn = tb.Button(parent, text=text, command=command, bootstyle=f"{style}-outline", cursor="hand2", padding=15)
        btn.pack(fill=X, pady=20)
        
    def create_output_area(self, parent, label_text, var_name):
        tb.Label(parent, text=label_text, font=("Segoe UI", 11, "bold"), bootstyle="secondary").pack(anchor="w", pady=(10, 5))
        
        # Increased font size to 12
        txt = scrolledtext.ScrolledText(parent, height=12, font=("Segoe UI", 12))
        txt.pack(fill=BOTH, expand=True)
        setattr(self, var_name, txt)
        
        btn_frame = tb.Frame(parent)
        btn_frame.pack(fill=X, pady=5)
        
        tb.Button(btn_frame, text="💾 저장하기", command=lambda: self.save_to_file(txt), bootstyle="info-outline").pack(side="right", padx=5)
        tb.Button(btn_frame, text="📋 복사하기", command=lambda: self.copy_to_clip(txt), bootstyle="secondary-link").pack(side="right")

    # --- Step 0: UI (Keyword Mining) ---
    def build_step0_ui(self, parent):
        # --- [NEW] 스마트 추천 섹션 ---
        # ttkbootstrap에서는 Labelframe (소문자 f)을 사용해야 bootstyle이 정상 작동합니다.
        rec_frame = tb.Labelframe(parent, text="✨ AI 트렌드 글감 추천 (시즌/기념일 기반)", bootstyle="primary")
        rec_frame.pack(fill=X, pady=(0, 20), padx=5)
        
        inner_rec = tb.Frame(rec_frame, padding=15)
        inner_rec.pack(fill=X)
        
        tb.Label(inner_rec, text="📅 월 선택:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 5))
        self.combo_month = tb.Combobox(inner_rec, values=[str(i) for i in range(1, 13)], width=5)
        self.combo_month.set(str(datetime.now().month))
        self.combo_month.pack(side="left", padx=(0, 15))
        
        tb.Label(inner_rec, text="📁 카테고리:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 5))
        self.combo_cat = tb.Combobox(inner_rec, values=APP_CATEGORIES, width=15)
        self.combo_cat.set("IT/테크")
        self.combo_cat.pack(side="left", padx=(0, 15))
        
        self.btn_smart_rec = tb.Button(inner_rec, text="⚡ 스마트 글감 제안", 
                                       command=self.run_smart_recommendation, bootstyle="info")
        self.btn_smart_rec.pack(side="left")
        
        tb.Label(rec_frame, text="* 커맨드센터의 분석 로직을 사용하여 현재 가장 핫한 글감을 추천합니다.", 
                 font=("Segoe UI", 8), bootstyle="secondary").pack(anchor="w", pady=(10, 0))

        # --- 기존 키워드 입력 섹션 ---
        self.create_question_block(parent,
            "Q1. 분석하고 싶은 핵심 키워드를 입력하세요 (쉼표 구분)",
            "예: 제주도 여행, 캠핑, 다이어트 음식...",
            "entry_keywords")
        
        limit_frame = tb.Frame(parent)
        limit_frame.pack(fill=X, pady=(0, 10))
        tb.Label(limit_frame, text="🔢 최대 채굴 키워드 수:", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.entry_limit = tb.Entry(limit_frame, width=10)
        self.entry_limit.insert(0, "30")
        self.entry_limit.pack(side="left", padx=10)

        self.create_action_button(parent, "⛏️ 황금 키워드 채굴 시작", 
            self.run_keyword_mining, "warning")

        # Result Table using Tableview
        tb.Label(parent, text="▼ 키워드 채굴 결과 (경쟁률 낮은 순 추천)", font=("Segoe UI", 11, "bold"), bootstyle="secondary").pack(anchor="w", pady=(10, 5))
        
        coldata = [
            {"text": "키워드", "stretch": True},
            {"text": "PC 검색량", "stretch": False},
            {"text": "모바일 검색량", "stretch": False},
            {"text": "총 검색량", "stretch": False},
            {"text": "문서수", "stretch": False},
            {"text": "경쟁률", "stretch": False},
        ]
        
        self.keyword_table = Tableview(
            master=parent,
            coldata=coldata,
            rowdata=[],
            paginated=True,
            searchable=True,
            bootstyle="primary",
            height=10
        )
        self.keyword_table.pack(fill=BOTH, expand=True, pady=5)
        
        # LOG Area (Adding 0121 version style log)
        tb.Label(parent, text="📝 채굴 진행 로그", font=("Segoe UI", 9, "bold"), bootstyle="secondary").pack(anchor="w", pady=(5, 0))
        from tkinter.scrolledtext import ScrolledText
        self.log_display = ScrolledText(parent, height=5, font=("Consolas", 9), state="disabled", bg="#f8f9fa")
        self.log_display.pack(fill=X, pady=(2, 10))

        btn_frame = tb.Frame(parent)
        btn_frame.pack(fill=X, pady=5)
        tb.Button(btn_frame, text="📋 선택한 키워드 Step 1로 보내기", command=self.send_keyword_to_step1, bootstyle="success-outline").pack(side="right")


    # --- Step 1: UI ---
    def build_step1_ui(self, parent):
        self.create_question_block(parent, 
            "Q0. 분석 핵심 주제 (Step 0에서 전송됨)", 
            "이곳은 자동으로 채워집니다. 필요시 위주로 수정 가능합니다.", 
            "entry_topic")

        self.create_question_block(parent, 
            "Q1. 누구를 도와주고 싶나요? (상품/서비스) *필수", 
            "예: '블로그 강의', '다이어트 도시락'... (이 항목은 꼭 적어주세요!)", 
            "entry_product")
        
        self.create_question_block(parent, 
            "Q2. 그 사람의 가장 큰 고민은 무엇인가요?", 
            "예: '살이 안 빠져서 우울하다', '월급이 적어서 힘들다'...", 
            "entry_pain")

        self.create_action_button(parent, "🔮 AI 캡틴에게 '꿈의 고객' 찾아달라고 하기", 
            lambda: self.run_step1(), "primary")
        
        self.create_output_area(parent, "▼ AI가 분석한 '꿈의 고객 프로필'", "txt_out1")
        
        # Image Area for Step 1
        tb.Label(parent, text="▼ [Nano Banana] 꿈의 고객 상상도", font=("Segoe UI", 11, "bold"), bootstyle="secondary").pack(anchor="w", pady=(20, 5))
        self.lbl_img_step1 = tb.Label(parent, text=" (이미지가 여기에 생성됩니다) ", bootstyle="inverse-light")
        self.lbl_img_step1.pack(pady=10)

    # --- Step 2: UI ---
    def build_step2_ui(self, parent):
        self.create_question_block(parent,
            "Q1. 나는 어떤 역할인가요? (하고 싶은 역할)",
            "예: '정글을 헤쳐나가는 모험가', '이미 성공한 리더', '같이 배우는 친구'...",
            "entry_role")
            
        self.create_question_block(parent,
            "Q2. 솔직히 고백할 나만의 약점이나 실수는?",
            "예: '기계치라서 컴퓨터를 못한다', '다이어트에 10번 실패했었다'...",
            "entry_flaw")
            
        self.create_question_block(parent,
            "Q3. 과거의 흑역사나 힘들었던 옛날 이야기 (Backstory)",
            "예: '카드값이 연체되어 독촉 전화를 받았던 날'... (짧게 써주셔도 돼요)",
            "entry_backstory")

        # Persona Style Selection
        tb.Label(parent, text="🎭 어떤 분위기의 캐릭터를 원하시나요?", font=("Segoe UI", 12, "bold"), bootstyle="inverse-dark", padding=5).pack(anchor="w", pady=(10, 0))
        self.combo_persona = tb.Combobox(parent, values=["옵션 A: 친절한 옆집 언니 (부드러운 공감)", "옵션 B: 냉철한 데이터 분석가 (팩트와 숫자)", "옵션 C: 열정적인 동기부여가 (에너지와 확신)"], state="readonly")
        self.combo_persona.current(0)
        self.combo_persona.pack(fill=X, pady=5)
            
        self.create_action_button(parent, "🎭 매력적인 캐릭터 조각하기", 
            lambda: self.run_gemini(self.txt_out2, "character"), "info")
            
        self.create_output_area(parent, "▼ AI가 만든 '캐릭터 프로필'", "txt_out2")

    # --- Step 3: UI ---
    def build_step3_ui(self, parent):
        self.create_question_block(parent,
            "Q1. 독자들이 모르는 '새로운 기회(비밀)'는 무엇인가요?",
            "예: '사실 블로그는 글솜씨가 아니라 시스템입니다', '다이어트의 핵심은 칼로리가 아니었습니다'...",
            "entry_secret")
            
        self.create_question_block(parent,
            "Q2. 과거에 겪었던 가장 처절했던 실패담(벽)은?",
            "예: '통장 잔고 0원일 때 기저귀 값을 걱정하며 울었습니다', '100번 넘게 거절당했습니다'...",
            "entry_wall")
            
        self.create_question_block(parent,
            "Q3. 그 문제를 해결해 준 '단 하나의 열쇠(유레카)'는?",
            "예: 'OOO 기법을 발견했습니다', '생각의 틀을 바꿨더니 모든 게 풀렸습니다'...",
            "entry_epiphany")

        self.create_question_block(parent,
            "Q4. 해결 후 변화된 삶과 독자에게 줄 선물(CTA)은?",
            "예: '이제 월 1000만원을 벌게 되었습니다. 여러분께 무료 전자책을 드립니다'...",
            "entry_cta")

        # Story Strategy Selection
        tb.Label(parent, text="🎬 어떤 방식의 이야기를 원하시나요?", font=("Segoe UI", 12, "bold"), bootstyle="inverse-dark", padding=5).pack(anchor="w", pady=(10, 0))
        self.story_var = tb.StringVar(value="Standard")
        tb.Radiobutton(parent, text="기존 4부작 시놉시스 (전형적인 기승전결)", variable=self.story_var, value="Standard", bootstyle="warning").pack(anchor="w", pady=2)
        tb.Radiobutton(parent, text="연속적 솝 오페라 (미끄럼틀 설계: 매회 새로운 문제 발견)", variable=self.story_var, value="Soap", bootstyle="warning").pack(anchor="w", pady=2)
            
        self.create_action_button(parent, "🎬 4부작 드라마 기획안 & 포스터 만들기",
            lambda: self.run_gemini(self.txt_out3, "synopsis"), "warning")
            
        self.create_output_area(parent, "▼ [드라마 작가] 4부작 시리즈 기획안", "txt_out3")

        # Image Area for Step 3
        tb.Label(parent, text="▼ [Nano Banana] 시리즈 공식 포스터 (Netflix Style)", font=("Segoe UI", 11, "bold"), bootstyle="secondary").pack(anchor="w", pady=(20, 5))
        self.lbl_img_step3 = tb.Label(parent, text=" (포스터가 여기에 생성됩니다) ", bootstyle="inverse-light")
        self.lbl_img_step3.pack(pady=10)


    # --- Step 4: UI ---
    def build_step4_ui(self, parent):
        self.create_question_block(parent,
            "Q1. 몇 화를 글로 쓰고 싶나요?",
            "예: '제1화', '전체 요약'...",
            "entry_episode")
            
        self.create_question_block(parent,
            "Q2. [장면] 그때 주변 소리, 냄새, 날씨는 어땠나요?",
            "예: '장마철이라 눅눅한 냄새가 났다', '시계 초침 소리만 들렸다'...",
            "entry_detail_scene")
            
        self.create_question_block(parent,
            "Q3. [속마음] 그때 혼자 속으로 무슨 생각을 했나요?",
            "예: '아, 여기서 끝이구나', '도망가고 싶다'...",
            "entry_detail_inner")
            
        self.create_action_button(parent, "🧪 글 짓는 연금술 실행",
            lambda: self.run_gemini(self.txt_out4, "draft"), "success")
            
        self.create_output_area(parent, "▼ 작성된 초안", "txt_out4")

    # --- Step 5: UI ---
    def build_step5_ui(self, parent):
        tb.Label(parent, text="🎬 4부작 마케팅 시리즈 완성", font=("Segoe UI", 14, "bold"), bootstyle="danger").pack(anchor="w", pady=(0, 20))
        
        # 회차 선택 섹션
        part_frame = tb.Labelframe(parent, text="📅 회차 선택", padding=15, bootstyle="danger")
        part_frame.pack(fill=X, pady=(0, 20))
        
        self.part_var = tk.StringVar(value="1")
        for i in range(1, 5):
            btn = tb.Radiobutton(part_frame, text=f"{i}회차", variable=self.part_var, value=str(i), 
                                 bootstyle="danger-toolbutton", command=self.on_part_change)
            btn.pack(side="left", padx=5)
            
        tb.Label(parent, text="★ 블로그 닉네임 (필수)", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 0))
        self.entry_nickname = tb.Entry(parent, font=("Segoe UI", 10))
        self.entry_nickname.pack(fill=X, pady=(5, 15))
        
        # 주제 영역
        topic_frame = tb.Frame(parent)
        topic_frame.pack(fill=X, pady=5)
        tb.Label(topic_frame, text="📌 이번 회차 주제:", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.lbl_current_topic = tb.Label(topic_frame, text="주제를 생성해주세요.", font=("Segoe UI", 10), bootstyle="info")
        self.lbl_current_topic.pack(side="left", padx=10)
        
        self.btn_re_topic = tb.Button(topic_frame, text="🎲 주제 다시 추천", command=self.recommend_part_topic, bootstyle="info-outline")
        self.btn_re_topic.pack(side="right")

        self.create_action_button(parent, "🚀 현재 회차 원고 & 이미지 생성",
            lambda: self.run_series_generation(), "dark")
            
        self.create_output_area(parent, "▼ [최종] 블로그 글", "txt_out5")

        # Image Grid with Download
        tb.Label(parent, text="▼ [Nano Banana] 생성된 이미지", font=("Segoe UI", 11, "bold"), bootstyle="secondary").pack(anchor="w", pady=(20, 5))
        
        img_scroll = tb.Scrollbar(parent, orient="horizontal")
        img_container = tb.Frame(parent)
        img_container.pack(fill=X, pady=10)
        
        self.step5_img_labels = []
        for i in range(4):
            f = tb.Frame(img_container)
            f.pack(side="left", padx=5)
            lbl = tb.Label(f, text=f"[이미지 {i+1}]", bootstyle="inverse-light", width=30)
            lbl.pack()
            self.step5_img_labels.append(lbl)
            tb.Button(f, text="📥 저장", command=lambda idx=i: self.download_image(idx), bootstyle="secondary-outline").pack(pady=5)

    def on_part_change(self):
        part = self.part_var.get()
        self.data["current_part"] = part
        topic = self.data["series_parts"].get(part, {}).get("topic", "주제를 생성해주세요.")
        content = self.data["series_parts"].get(part, {}).get("content", "")
        self.lbl_current_topic.configure(text=topic)
        self.txt_out5.delete("1.0", END)
        self.txt_out5.insert("1.0", content)
        self.save_session()

    def recommend_part_topic(self):
        """스킬을 통한 주제 추천"""
        part = self.part_var.get()
        if not self.api_key: return
        
        self.update_log(f"🤖 AI가 {part}회차에 적합한 주제를 분석 중...")
        
        skill_path = os.path.join(".agent", "skills", "step5-production", "logic.py")
        args = [
            "--mode", "recommend_topic",
            "--api_key", self.api_key,
            "--data_json", json.dumps(self.data),
            "--part", part
        ]
        
        def callback(new_topic):
            if new_topic:
                self.data["series_parts"][part]["topic"] = new_topic
                self.lbl_current_topic.configure(text=new_topic)
                self.save_session()
            else:
                self.update_log("⚠️ 주제 추천 실패")

        self.run_skill(skill_path, args, callback, stream_callback=None)

    def run_series_generation(self):
        part = self.part_var.get()
        self.run_gemini(self.txt_out5, f"part_{part}")

    def download_image(self, idx):
        """특정 인덱스의 이미지를 파일로 저장"""
        if idx < len(self.step5_img_labels):
            lbl = self.step5_img_labels[idx]
            if hasattr(lbl, 'pil_image'):
                filename = filedialog.asksaveasfilename(
                    defaultextension=".png",
                    filetypes=[("PNG Files", "*.png"), ("All Files", "*.*")],
                    title=f"이미지 {idx+1} 저장"
                )
                if filename:
                    try:
                        lbl.pil_image.save(filename)
                        messagebox.showinfo("저장 완료", f"이미지가 저장되었습니다: {filename}")
                    except Exception as e:
                        messagebox.showerror("오류", f"저장 중 오류 발생: {e}")
            else:
                messagebox.showwarning("경고", "먼저 이미지를 생성해주세요.")

        pass

    # --- Settings UI ---
    def build_settings_ui(self, parent):
        container = tb.Frame(parent)
        container.pack(fill=X, pady=20)
        
        # Google Section
        tb.Label(container, text="🔑 Google Gemini API 설정", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(anchor="w", pady=(0, 10))
        self.entry_api_key = tb.Entry(container, font=("Segoe UI", 12), show="*")
        self.entry_api_key.pack(fill=X, pady=5)
        if self.api_key:
            self.entry_api_key.insert(0, self.api_key)
        tb.Button(container, text="🔗 API 키 발급받기 (Google AI Studio)", command=lambda: os.startfile("https://aistudio.google.com/app/apikey"), bootstyle="link").pack(anchor="w")

        tb.Separator(container, bootstyle="secondary").pack(fill=X, pady=30)

        # Naver Section
        tb.Label(container, text="🔑 Naver API 설정 (키워드 채굴용)", font=("Segoe UI", 14, "bold"), bootstyle="info").pack(anchor="w", pady=(0, 10))
        
        # Naver Search AD
        tb.Label(container, text="[네이버 검색광고 API]", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.entry_nav_access = self.create_setting_field(container, "Access License Key", "naver_access_key")
        self.entry_nav_secret = self.create_setting_field(container, "Secret Key", "naver_secret_key", is_password=True)
        self.entry_nav_customer = self.create_setting_field(container, "Customer ID", "naver_customer_id")
        
        # Naver Blog Search
        tb.Label(container, text="\n[네이버 블로그 검색 API]", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.entry_blog_id = self.create_setting_field(container, "Client ID", "naver_client_id")
        self.entry_blog_secret = self.create_setting_field(container, "Client Secret", "naver_client_secret", is_password=True)

        tb.Button(container, text="💾 모든 API Key 저장하기", command=self.save_api_key, bootstyle="success", padding=10).pack(pady=30)
        tb.Label(container, text="* 모든 키는 config.json에 안전하게 저장됩니다.", font=("Segoe UI", 9), bootstyle="secondary").pack(anchor="w")

    def create_setting_field(self, parent, label, config_key, is_password=False):
        frame = tb.Frame(parent)
        frame.pack(fill=X, pady=5)
        tb.Label(frame, text=label, width=20, anchor="w").pack(side="left")
        entry = tb.Entry(frame, font=("Segoe UI", 10), show="*" if is_password else "")
        entry.pack(side="left", fill=X, expand=True)
        
        # Load initial value
        val = self.data.get("naver_api", {}).get(config_key, "")
        if val:
            entry.insert(0, val)
        return entry

    def save_api_key(self):
        new_gemini_key = self.entry_api_key.get().strip()
        
        naver_config = {
            "naver_access_key": self.entry_nav_access.get().strip(),
            "naver_secret_key": self.entry_nav_secret.get().strip(),
            "naver_customer_id": self.entry_nav_customer.get().strip(),
            "naver_client_id": self.entry_blog_id.get().strip(),
            "naver_client_secret": self.entry_blog_secret.get().strip()
        }
        
        config_data = {
            "api_key": new_gemini_key,
            "NAVER_SEARCH_ACCESS_LICENSE_KEY": naver_config["naver_access_key"],
            "NAVER_SEARCH_SECRET_KEY": naver_config["naver_secret_key"],
            "NAVER_SEARCH_CUSTOMER_ID": naver_config["naver_customer_id"],
            "NAVER_BLOG_CLIENT_ID": naver_config["naver_client_id"],
            "NAVER_BLOG_CLIENT_SECRET": naver_config["naver_client_secret"]
        }
        
        self.api_key = new_gemini_key
        self.data["naver_api"] = naver_config
        
        self.save_config(config_data)
        messagebox.showinfo("설정 완료", "모든 API 키가 성공적으로 저장되었습니다.")

    def load_config(self):
        load_dotenv() # Load from .env file
        
        config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except:
                 pass
        
        # Load Naver API - Prioritize config.json, fallback to .env
        self.data["naver_api"] = {
            "naver_access_key": config.get("NAVER_SEARCH_ACCESS_LICENSE_KEY") or os.getenv("NAVER_SEARCH_ACCESS_LICENSE_KEY", ""),
            "naver_secret_key": config.get("NAVER_SEARCH_SECRET_KEY") or os.getenv("NAVER_SEARCH_SECRET_KEY", ""),
            "naver_customer_id": config.get("NAVER_SEARCH_CUSTOMER_ID") or os.getenv("NAVER_SEARCH_CUSTOMER_ID", ""),
            "naver_client_id": config.get("NAVER_BLOG_CLIENT_ID") or os.getenv("NAVER_BLOG_CLIENT_ID", ""),
            "naver_client_secret": config.get("NAVER_BLOG_CLIENT_SECRET") or os.getenv("NAVER_BLOG_CLIENT_SECRET", "")
        }
        
        # API Key (Google Gemini) - Prioritize config.json, fallback to .env/GEMINI_API_KEY
        return config.get("api_key") or os.getenv("GEMINI_API_KEY", "")

    def save_config(self, config_dict):
        with open(CONFIG_FILE, "w", encoding='utf-8') as f:
            json.dump(config_dict, f, ensure_ascii=False, indent=4)

    def load_session(self):
        """이전 세션 데이터 불러오기 및 UI 복원"""
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, "r", encoding='utf-8') as f:
                    session_data = json.load(f)
                    self.data.update(session_data)
                    # UI 복원은 create_widgets 이후에 각 위젯에 값 세팅 필요
            except Exception as e:
                print(f"Session load error: {e}")

    def save_session(self, event=None):
        """현재 데이터 저장 (비동식 호출 권장)"""
        # UI의 입력값들을 self.data에 동기화
        self.sync_data_from_ui()
        try:
            with open(SESSION_FILE, "w", encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Session save error: {e}")

    def sync_data_from_ui(self):
        """UI 위젯의 값들을 self.data 딕셔너리에 동기화"""
        try:
            # Step 1
            if hasattr(self, 'entry_product'): self.data['product'] = self.entry_product.get()
            if hasattr(self, 'entry_pain'): self.data['pain'] = self.entry_pain.get()
            if hasattr(self, 'entry_solution'): self.data['solution'] = self.entry_solution.get()
            if hasattr(self, 'entry_topic'): self.data['target_topic'] = self.entry_topic.get()
            
            # Step 2
            if hasattr(self, 'entry_role'): self.data['role'] = self.entry_role.get()
            if hasattr(self, 'entry_values'): self.data['values'] = self.entry_values.get()
            if hasattr(self, 'combo_persona'): self.data['persona_style'] = self.combo_persona.get()
            
            # Step 3
            if hasattr(self, 'entry_enemy'): self.data['enemy'] = self.entry_enemy.get()
            if hasattr(self, 'entry_inciting'): self.data['inciting'] = self.entry_inciting.get()
            if hasattr(self, 'entry_epiphany_moment'): self.data['epiphany_moment'] = self.entry_epiphany_moment.get()
            if hasattr(self, 'combo_strategy'): self.data['story_strategy'] = self.combo_strategy.get()
            
            # Step 4
            if hasattr(self, 'entry_hook'): self.data['hook'] = self.entry_hook.get()
            if hasattr(self, 'entry_call_to_action'): self.data['call_to_action'] = self.entry_call_to_action.get()
            
            # Step 5
            if hasattr(self, 'entry_nickname'): self.data['nickname'] = self.entry_nickname.get()
            
            # Text contents (Backup for Part 5 or current part)
            if hasattr(self, 'txt_out5'): self.data['final_script'] = self.txt_out5.get("1.0", END)
        except:
            pass

    def restore_ui_from_data(self):
        """저장된 self.data를 기반으로 UI 위젯 초기값 설정"""
        try:
            # Step 1
            if hasattr(self, 'entry_product'): 
                self.entry_product.delete(0, END)
                self.entry_product.insert(0, self.data.get('product', ''))
            if hasattr(self, 'entry_pain'): 
                self.entry_pain.delete(0, END)
                self.entry_pain.insert(0, self.data.get('pain', ''))
            if hasattr(self, 'entry_solution'): 
                self.entry_solution.delete(0, END)
                self.entry_solution.insert(0, self.data.get('solution', ''))
            if hasattr(self, 'entry_topic'): 
                self.entry_topic.delete(0, END)
                self.entry_topic.insert(0, self.data.get('target_topic', ''))
            
            # Step 2
            if hasattr(self, 'entry_role'): 
                self.entry_role.delete(0, END)
                self.entry_role.insert(0, self.data.get('role', ''))
            if hasattr(self, 'entry_values'): 
                self.entry_values.delete(0, END)
                self.entry_values.insert(0, self.data.get('values', ''))
            if hasattr(self, 'combo_persona'): 
                self.combo_persona.set(self.data.get('persona_style', 'Friendly'))
            
            # Step 3
            if hasattr(self, 'entry_enemy'): 
                self.entry_enemy.delete(0, END)
                self.entry_enemy.insert(0, self.data.get('enemy', ''))
            if hasattr(self, 'entry_inciting'): 
                self.entry_inciting.delete(0, END)
                self.entry_inciting.insert(0, self.data.get('inciting', ''))
            if hasattr(self, 'entry_epiphany_moment'): 
                self.entry_epiphany_moment.delete(0, END)
                self.entry_epiphany_moment.insert(0, self.data.get('epiphany_moment', ''))
            if hasattr(self, 'combo_strategy'): 
                self.combo_strategy.set(self.data.get('story_strategy', 'Standard'))
            
            # Step 4
            if hasattr(self, 'entry_hook'): 
                self.entry_hook.delete(0, END)
                self.entry_hook.insert(0, self.data.get('hook', ''))
            if hasattr(self, 'entry_call_to_action'): 
                self.entry_call_to_action.delete(0, END)
                self.entry_call_to_action.insert(0, self.data.get('call_to_action', ''))
            
            # Step 5
            if hasattr(self, 'part_var'):
                self.part_var.set(self.data.get('current_part', '1'))
                self.on_part_change() # This will update topic and text area
            
            if hasattr(self, 'entry_nickname'):
                self.entry_nickname.delete(0, END)
                self.entry_nickname.insert(0, self.data.get('nickname', ''))
        except Exception as e:
            print(f"Restore UI error: {e}")

    def setup_auto_save(self):
        """입력창 값이 변할 때마다 자동 저장되도록 바인딩"""
        for attr in ['entry_product', 'entry_pain', 'entry_solution', 'entry_topic', 
                     'entry_role', 'entry_values', 'entry_enemy', 'entry_inciting', 
                     'entry_epiphany_moment', 'entry_hook', 'entry_call_to_action',
                     'entry_nickname']:
            if hasattr(self, attr):
                getattr(self, attr).bind("<FocusOut>", self.save_session)
                getattr(self, attr).bind("<Return>", self.save_session)
        
        # Comboboxes
        for attr in ['combo_persona', 'combo_strategy']:
            if hasattr(self, attr):
                getattr(self, attr).bind("<<ComboboxSelected>>", self.save_session)

    def init_genai_client(self):
        global client
        if self.api_key:
            try:
                client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Client Init Error: {e}")
                client = None
        else:
            client = None

    # --- Logic ---
    
    def get_input(self, entry_widget, default_msg):
        val = entry_widget.get().strip()
        if not val:
            return f"(User Skipped: AI MUST invent a creative, specific detail for this based on context. {default_msg})"
        return val

    # --- Typewriter Animation ---
    def stream_text(self, widget, text, index=0):
        # 3000 chars is a safeguard limit to prevent UI freezing on super long texts during animation
        # But we want to show everything. We can speed up for longer text.
        
        if index == 0:
            widget.delete("1.0", END)
        
        if index < len(text):
            chunk = text[index:index+5] # Detailed speed control: +5 chars per tick
            widget.insert(END, chunk)
            widget.see(END)
            # Dynamic speed: faster for long texts
            speed = 10 if len(text) < 500 else 2 
            self.root.after(speed, self.stream_text, widget, text, index+5)
        else:
            # Animation Done
            pass

        # 2. Image Generation (Chained)
        product = self.entry_product.get()
        pain = self.entry_pain.get()
        # Added instruction for English text only
        img_prompt = f"A photorealistic portrait of a korean person who is worrying about {pain} related to {product}. High quality, emotional, detailed face, cinematic lighting, 8k. (Important: If there is any text in the image, it must be in English only. Do NOT use Korean text.)"
        self.run_image_gen(img_prompt, self.lbl_img_step1)

    def run_step1(self):
        if not self.entry_product.get().strip():
            messagebox.showwarning("필수 입력", "Q1. 누구를 도와주고 싶나요? (상품/서비스) 항목은 필수입니다.")
            return
        self.run_gemini(self.txt_out1, "customer")

    def run_gemini(self, widget, key):
        if not self.api_key:
            messagebox.showwarning("설정 필요", "먼저 '설정' 탭에서 API Key를 입력하고 저장해주세요.")
            self.notebook.select(self.tab_settings)
            return

        # Mapping key to skill folder
        skill_map = {
            "customer": "step1-planning",
            "character": "step2-character",
            "synopsis": "step3-strategy",
            "draft": "step4-draft"
        }
        
        # Step 5 special handling (part_1, part_2, etc.)
        skill_folder = skill_map.get(key)
        if not skill_folder and key.startswith("part_"):
            skill_folder = "step5-production"

        if not skill_folder:
            self.update_log(f"⚠️ 매핑된 스킬을 찾을 수 없습니다: {key}")
            return

        skill_path = os.path.join(".agent", "skills", skill_folder, "logic.py")
        
        # Argument collection based on step
        args = ["--api_key", self.api_key]
        
        if skill_folder == "step1-planning":
            args += ["--product", self.entry_product.get(), "--pain", self.entry_pain.get(), "--target_topic", self.entry_topic.get()]
        elif skill_folder == "step2-character":
            args += ["--customer_profile", self.txt_out1.get("1.0", END).strip(), 
                     "--role", self.entry_role.get(), "--flaw", self.entry_flaw.get(), 
                     "--backstory", self.entry_backstory.get(), "--persona_style", self.combo_persona.get()]
        elif skill_folder == "step3-strategy":
            args += ["--customer", self.txt_out1.get("1.0", END).strip(), "--character", self.txt_out2.get("1.0", END).strip(),
                     "--secret", self.entry_secret.get(), "--wall", self.entry_wall.get(), "--epiphany", self.entry_epiphany.get(),
                     "--cta", self.entry_cta.get(), "--strategy", self.story_var.get()]
        elif skill_folder == "step4-draft":
            args += ["--synopsis", self.txt_out3.get("1.0", END).strip(), "--character", self.txt_out2.get("1.0", END).strip(),
                     "--episode", self.entry_episode.get(), "--scene", self.entry_detail_scene.get(), "--inner", self.entry_detail_inner.get()]
        elif skill_folder == "step5-production":
            curr_part = key.split("_")[1]
            args += ["--data_json", json.dumps(self.data), "--part", curr_part]

        widget.delete("1.0", END)
        widget.insert("1.0", "⏳ AI 캡틴이 스킬을 가동 중입니다... (잠시만 기다려주세요)")
        
        def callback(result):
            try:
                if skill_folder == "step5-production":
                    res_data = json.loads(result)
                    text_content = res_data.get("content", result)
                    self.stream_text(widget, text_content)
                    
                    # Store result in session
                    p_num = key.split("_")[1]
                    self.data["series_parts"][p_num]["content"] = text_content
                    
                    # Extract prompts and gen images
                    import re
                    prompts = re.findall(r"Prompt \d+:\s*(.*?)(?:\n|$)", text_content)
                    for i, p in enumerate(prompts[:4]):
                        self.run_image_gen(p, self.step5_img_labels[i])
                else:
                    self.stream_text(widget, result)
                    self.data[key] = result
                
                # Additional logic for imagery
                if key == "customer":
                    p = self.entry_product.get(); pa = self.entry_pain.get()
                    ip = f"A photorealistic portrait of a korean person who is worrying about {pa} related to {p}. High quality, emotional, detailed face, cinematic lighting, 8k. (NO KOREAN TEXT)"
                    self.run_image_gen(ip, self.lbl_img_step1)
                elif key == "synopsis":
                    ip = f"A dramatic Netflix movie poster for a series titled '{self.entry_product.get()}'. Cinematic lighting, high quality 8k, emotional, text-free."
                    self.run_image_gen(ip, self.lbl_img_step3)
                
                self.save_session()
            except Exception as e:
                self.update_log(f"⚠️ 콜백 처리 오류: {e}")

        self.run_skill(skill_path, args, callback, stream_callback=None)

    # --- Keyword Mining Logic (골든키워드채굴기_0121 로직 직접 이식) ---
    def run_keyword_mining(self):
        keywords_str = self.entry_keywords.get().strip()
        if not keywords_str:
            messagebox.showwarning("입력 필요", "분석할 키워드를 입력해주세요.")
            return
        
        limit_val = self.entry_limit.get().strip() or "30"
        try:
            limit = int(limit_val)
        except: limit = 30

        nav = self.data.get("naver_api", {})
        ak = nav.get("naver_access_key")
        sk = nav.get("naver_secret_key")
        cid = nav.get("naver_customer_id")
        bl_id = nav.get("naver_client_id")
        bl_sk = nav.get("naver_client_secret")
        
        if not all([ak, sk, cid, bl_id, bl_sk]):
            messagebox.showwarning("설정 필요", "먼저 '설정' 탭에서 모든 네이버 API 정보를 입력하고 저장해주세요.")
            self.notebook.select(self.tab_settings)
            return

        self.keyword_table.delete_rows()
        self.update_log("🚀 실시간 키워드 채굴 엔진 가동 중...", clear=True)
        
        def worker():
            initial_keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
            keyword_queue = deque(initial_keywords)
            searched_keywords = set()
            recorded_keywords = set()
            all_results = []
            count = 0

            try:
                while keyword_queue and count < limit:
                    current = keyword_queue.popleft()
                    if current in searched_keywords: continue
                    searched_keywords.add(current)

                    self.update_log(f"LOG: '{current}' 분석을 위해 네이버 API 호출 중...")
                    
                    try:
                        # 1단계: 연관 키워드 목록 수집
                        stats = get_naver_keyword_stats(ak, sk, cid, [current])
                        if stats and "keywordList" in stats:
                            items = stats["keywordList"]
                            self.update_log(f"LOG: '{current}'에서 {len(items)}개의 후보를 찾았습니다.")
                            
                            for item in items:
                                if count >= limit: break
                                rel = item.get("relKeyword", "N/A")
                                if rel in recorded_keywords: continue

                                # 정량 데이터 추출
                                pc = item.get("monthlyPcQcCnt", "N/A")
                                mo = item.get("monthlyMobileQcCnt", "N/A")
                                
                                try:
                                    pc_val = int(pc) if pc not in ["<10", "N/A"] else 0
                                    mo_val = int(mo) if mo not in ["<10", "N/A"] else 0
                                    total = pc_val + mo_val
                                    if total == 0 and ("<10" in [pc, mo]): total = "<10"
                                except: total = "N/A"
                                
                                # 2단계: 문서 수 수집 (실시간 시각화의 핵심)
                                self.update_log(f"DEBUG: [{count+1}/{limit}] '{rel}' 데이터 수집 중...")
                                
                                doc_count = 0
                                try:
                                    doc_count = get_naver_document_count(rel, bl_id, bl_sk)
                                except Exception as api_err:
                                    self.update_log(f"DEBUG: '{rel}' 문서수 조회 건너뜀")
                                
                                comp = "N/A"
                                try:
                                    calc_total = total if isinstance(total, int) else (5 if total == "<10" else 0)
                                    if calc_total > 0: comp = round(doc_count / calc_total, 2)
                                except: pass
                                
                                row_data = (rel, pc, mo, total, doc_count, comp)
                                res_item = {"keyword": rel, "pc": pc, "mo": mo, "total": total, "docs": doc_count, "comp": comp}
                                all_results.append(res_item)
                                recorded_keywords.add(rel)
                                count += 1
                                
                                # GUI 테이블에 즉시 한 줄 삽입 (실시간 시각화)
                                self.root.after(0, lambda r=row_data: self.append_keyword_row(r))
                                
                                # 키워드 확장을 위해 큐에 추가
                                if count < limit and rel not in searched_keywords and rel not in keyword_queue:
                                    keyword_queue.append(rel)
                                    
                                # API 속도 제한 준수 및 UI 응답성 확보를 위한 미세 지연
                                time.sleep(0.05)
                        else:
                            self.update_log(f"LOG: '{current}'에 대한 연관 키워드가 없습니다.")
                    except Exception as e:
                        self.update_log(f"❌ '{current}' 분석 중 오류: {e}")

                # 3단계: 최종 정렬 (경쟁률 낮은 순)
                self.update_log("📊 모든 분석 완료! 최적의 순서로 정렬합니다...")
                all_results.sort(key=lambda x: (x["comp"] if isinstance(x["comp"], (int, float)) else 999999))
                
                final_rows = []
                for r in all_results:
                    final_rows.append((r['keyword'], r['pc'], r['mo'], r['total'], r['docs'], r['comp']))
                
                # 정렬된 데이터로 테이블 일괄 갱신
                self.root.after(0, lambda data=final_rows: self.keyword_table.build_table_data(self.keyword_table.coldata, data))
                self.update_log(f"✅ 채굴 완료! 총 {len(all_results)}개의 키워드가 준비되었습니다.")
                
            except Exception as e:
                self.root.after(0, lambda m=str(e): messagebox.showerror("치명적 오류", f"분석 중 치명적 오류가 발생했습니다: {m}"))

        # 별도 스레드에서 백그라운드 작업 실행 시작
        threading.Thread(target=worker, daemon=True).start()

    def append_keyword_row(self, row):
        # 실시간으로 화면에 즉시 보이기 위해 Treeview에 직접 삽입
        # Tableview가 내부적으로 관리하는 리스트(tablerows)에도 추가 (나중에 build_table_data로 덮어쓰기 전까지 유지)
        self.keyword_table.insert_row(END, row)
        self.keyword_table.view.see(END) # 최신 데이터로 스크롤
        self.root.update_idletasks() # UI 강제 갱신

    def update_log(self, message, clear=False):
        msg_clean = message.strip()
        if not msg_clean: return

        # ROW: 형식의 데이터가 오면 테이블에 즉시 추가
        if msg_clean.startswith("ROW:"):
            try:
                import json
                r = json.loads(msg_clean[4:])
                row = (r['keyword'], r['pc'], r['mo'], r['total'], r['docs'], r['comp'])
                self.append_keyword_row(row)
                return
            except:
                pass
        
        # LOG 디스플레이 업데이트 (DEBUG 나 LOG 접두사 처리)
        display_msg = msg_clean
        if msg_clean.startswith("DEBUG:"): display_msg = msg_clean[6:].strip()
        elif msg_clean.startswith("LOG:"): display_msg = msg_clean[4:].strip()
            
        self.log_display.configure(state="normal")
        if clear: self.log_display.delete("1.0", "end")
        self.log_display.insert("end", f"[{time.strftime('%H:%M:%S')}] {display_msg}\n")
        self.log_display.see("end")
        self.log_display.configure(state="disabled")
        # 즉시 UI 강제 갱신으로 실시간성 확보
        self.root.update_idletasks()

    # --- 스마트 추천 로직 (2단계 고도화 버전) ---
    def run_smart_recommendation(self):
        """스킬을 통한 스마트 키워드 추천 (All-in-One 자동화)"""
        m = self.combo_month.get()
        c = self.combo_cat.get()
        current_kws = self.entry_keywords.get().strip()
        nav = self.data.get("naver_api", {})
        gemini_key = self.api_key
        
        self.update_log("🔍 지능형 추천 엔진 가동 (Naver Auto + DataLab + Gemini)...")
        self.btn_smart_rec.configure(state="disabled")
        
        args = [
            "--mode", "recommend",
            "--config", json.dumps(nav),
            "--month", m,
            "--category", c,
            "--keywords", current_kws,
            "--gemini_key", gemini_key
        ]
        
        def callback(result_raw):
            try:
                # Expecting a flat list of keywords now
                import re
                match = re.search(r'(\[.*\])', result_raw, re.DOTALL)
                if match:
                    keywords = json.loads(match.group(1))
                    if keywords:
                        self.update_log(f"✅ {len(keywords)}개의 황금 키워드 후보를 발굴했습니다.")
                        # Bypass Selector -> Auto Start Mining
                        self.run_batch_mining(keywords)
                    else:
                        self.update_log("⚠️ 추천 결과가 비어있습니다.")
                else:
                    self.update_log(f"❌ 데이터 형식이 올바르지 않습니다. (RAW: {result_raw[:50]}...)")
            except Exception as e:
                self.update_log(f"❌ 처리 중 오류: {e}")
            finally:
                self.btn_smart_rec.configure(state="normal")

        skill_path = os.path.join(".agent", "skills", "step0-keyword-miner", "logic.py")
        self.run_skill(skill_path, args, callback, stream_callback=self.update_log)

    def run_batch_mining(self, keywords):
        """추천된 키워드 리스트를 받아 즉시 분석 시작"""
        limit = len(keywords)
        self.entry_limit.delete(0, END)
        self.entry_limit.insert(0, str(limit))
        
        # Populate entry for visual feedback
        self.entry_keywords.delete(0, END)
        self.entry_keywords.insert(0, ", ".join(keywords))
        
        # Start Mining Logic (Reusing run_keyword_mining logic but with list)
        nav = self.data.get("naver_api", {})
        ak = nav.get("naver_access_key")
        sk = nav.get("naver_secret_key")
        cid = nav.get("naver_customer_id")
        bl_id = nav.get("naver_client_id")
        bl_sk = nav.get("naver_client_secret")
        
        if not all([ak, sk, cid, bl_id, bl_sk]):
            messagebox.showwarning("설정 필요", "네이버 API 키 설정이 필요합니다.")
            return

        self.keyword_table.delete_rows()
        self.update_log(f"🚀 {len(keywords)}개 키워드에 대한 심층 분석(문서수/경쟁률)을 시작합니다...", clear=True)
        
        def worker():
            from collections import deque
            keyword_queue = deque(keywords)
            processed_count = 0
            all_results = []
            
            # Using existing mining helper logic structure
            # (Ideally refactor run_mining in logic.py to support batch analysis mode without expanding, 
            # but here we can just assume run_mining logic or invoke logic.py in 'mining' mode with the full list)
            # Actually, easiest is to call logic.py in 'mining' mode with these keywords as initial list.
            
            # We call logic.py --mode mining --keywords "..." --limit N
            # But the command line might be too long. 
            pass # We will use run_skill for this.
            
        # Re-using run_skill to run mining mode on these keywords
        # We need to chunk them if too many? args string limit.
        # Python subprocess argument limit on Windows is 32k chars. 50 keywords is fine.
        
        k_str = ", ".join(keywords)
        skill_path = os.path.join(".agent", "skills", "step0-keyword-miner", "logic.py")
        mining_args = [
            "--mode", "mining",
            "--config", json.dumps(nav),
            "--keywords", k_str,
            "--limit", str(limit) # Analyze exactly these
        ]
        
        def mining_callback(res):
            self.update_log("✅ 모든 분석이 완료되었습니다!")

        self.run_skill(skill_path, mining_args, mining_callback, stream_callback=self.update_log)

    def show_recommendation_selector(self, groups):
        """추천된 키워드를 카테고리별로 보여주고 선택하는 팝업창"""
        win = tk.Toplevel(self.root)
        win.title("✨ 스마트 글감 선택기")
        win.geometry("650x700")
        win.lift()
        win.focus_force()
        win.grab_set() # 모달 창으로 설정
        
        main_frame = tb.Frame(win, padding=20)
        main_frame.pack(fill=BOTH, expand=True)
        
        tb.Label(main_frame, text="💡 채굴하고 싶은 키워드를 선택하세요", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(anchor="w", pady=(0, 15))
        
        # Scrollable area for keywords
        canvas = tb.Canvas(main_frame)
        scrollbar = tb.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scroll_frame = tb.Frame(canvas)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=580)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.check_vars = [] # Store (keyword, var) pairs

        for group in groups:
            group_frame = tb.Labelframe(scroll_frame, text=group["title"], padding=15, bootstyle="secondary")
            group_frame.pack(fill=X, pady=10)
            
            # Grid layout for checkboxes (3 columns)
            items = group.get("items", [])
            for i, item in enumerate(items):
                kw = item["keyword"]
                trend = item.get("trend", 0)
                
                display_text = kw
                if trend > 0: display_text += f" (🔥{trend})"
                
                var = tk.BooleanVar(value=False)
                cb = tb.Checkbutton(group_frame, text=display_text, variable=var, bootstyle="round-toggle")
                cb.grid(row=i // 3, column=i % 3, sticky="w", padx=10, pady=5)
                self.check_vars.append((kw, var))

        # Bottom Buttons
        btn_frame = tb.Frame(main_frame, padding=(0, 20, 0, 0))
        btn_frame.pack(fill=X)
        
        def apply_selection():
            selected = [kw for kw, var in self.check_vars if var.get()]
            if not selected:
                messagebox.showwarning("선택 필요", "최소 하나 이상의 키워드를 선택해주세요.")
                return
            
            current = self.entry_keywords.get().strip()
            if current:
                new_val = current + ", " + ", ".join(selected)
            else:
                new_val = ", ".join(selected)
            
            self.entry_keywords.delete(0, END)
            self.entry_keywords.insert(0, new_val)
            win.destroy()
            self.update_log(f"✅ {len(selected)}개의 키워드가 입력창에 추가되었습니다.")

        tb.Button(btn_frame, text="✅ 선택 완료 및 키워드 추가", command=apply_selection, bootstyle="success", padding=10).pack(side="right", padx=5)
        tb.Button(btn_frame, text="❌ 취소", command=win.destroy, bootstyle="secondary-outline", padding=10).pack(side="right")

    def send_keyword_to_step1(self):
        selected = self.keyword_table.view.selection()
        if not selected:
            messagebox.showwarning("선택 필요", "Step 1로 보낼 키워드를 표에서 선택해주세요.")
            return
        
        # Get the first selected row's keyword
        item = self.keyword_table.view.item(selected[0])
        keyword = item['values'][0]
        
        # Set to the new Target Topic field instead of Product
        self.entry_topic.delete(0, END)
        self.entry_topic.insert(0, keyword)
        
        messagebox.showinfo("이동 완료", f"'{keyword}' 키워드가 Step 1의 분석 핵심 주제로 전달되었습니다.\n(Q1 항목은 별도로 입력해주세요.)")
        self.notebook.select(self.tab1)
        self.save_session()

    def run_image_gen(self, prompt, label_widget):
        if not self.api_key:
             return

        label_widget.configure(text="🎨 Nano Banana가 그림을 그리고 있습니다...", image="")
        
        # Save to a temporary file
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_out = os.path.join(temp_dir, f"gen_img_{int(time.time())}_{id(label_widget)}.png")
        
        skill_path = os.path.join(".agent", "skills", "step5-production", "logic.py")
        args = [
            "--mode", "image",
            "--api_key", self.api_key,
            "--prompt", prompt,
            "--out", temp_out
        ]
        
        def callback(out_path):
            if out_path and os.path.exists(out_path):
                try:
                    from PIL import Image, ImageTk
                    image = Image.open(out_path)
                    image.thumbnail((400, 400))
                    photo = ImageTk.PhotoImage(image)
                    label_widget.pil_image = Image.open(out_path) # Cache full size for download
                    self.update_image_label(label_widget, photo)
                except Exception as e:
                    self.update_log(f"❌ 이미지 로드 오류: {e}")
            else:
                label_widget.configure(text="이미지 생성 실패")

        self.run_skill(skill_path, args, callback, stream_callback=None)


if __name__ == "__main__":
    # Theme: Cosmo (Modern Blue/White)
    root = tb.Window(themename="cosmo") 
    app = MarketingWizardApp(root)
    root.mainloop()
