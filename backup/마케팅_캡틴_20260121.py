import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import ToastNotification
import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
import threading
import time
from google import genai
from google.genai import types
from PIL import Image, ImageTk, ImageDraw, ImageFont
import io
from datetime import datetime, timedelta
import json
import os
import subprocess
import hmac
import hashlib
import base64
import urllib.parse
import requests
from collections import deque
from dotenv import load_dotenv
from ttkbootstrap.widgets.tableview import Tableview

# Configure Gemini Client - Initially None, will be set after loading config
client = None
CONFIG_FILE = "config.json"
SESSION_FILE = "session_data.json"

# --- [데이터] 시즌/캘린더 및 카테고리 (from 커맨드센터) ---
SEASONAL_DATA = {
    1: ["새해", "신년운세", "다이어트", "설날", "연말정산", "해돋이", "겨울방학"],
    2: ["발렌타인데이", "졸업식", "입학준비", "봄코디", "정월대보름"],
    3: ["삼일절", "입학식", "화이트데이", "벚꽃", "미세먼지", "공채"],
    4: ["식목일", "중간고사", "벚꽃축제", "피크닉", "결혼식하객룩"],
    5: ["어린이날", "어버이날", "스승의날", "성년의날", "종합소득세"],
    6: ["현충일", "기말고사", "여름휴가", "장마", "제습기", "다이어트"],
    7: ["초복", "중복", "여름방학", "해수욕장", "장마철", "호캉스"],
    8: ["말복", "광복절", "휴가", "계곡", "개학", "수강신청"],
    9: ["추석", "추석선물", "가을코디", "독서", "환절기", "대하축제"],
    10: ["개천절", "한글날", "할로윈", "단풍놀이", "등산", "축제"],
    11: ["빼빼로데이", "수능", "블랙프라이데이", "김장", "첫눈", "난방"],
    12: ["크리스마스", "연말파티", "송년회", "다이어리", "해넘이"]
}

CALENDAR_EVENTS = {
    1: ["세계 내향인의 날", "소한", "대한", "연말정산 간소화", "1월1일"],
    2: ["입춘", "우수", "밸런타인데이", "정월대보름", "졸업식"],
    3: ["삼일절", "경칩", "춘분", "화이트데이", "상공의 날", "납세자의 날"],
    4: ["만우절", "식목일", "청명", "곡우", "과학의 날", "지구의 날"],
    5: ["근로자의 날", "어린이날", "어버이날", "입하", "스승의 날", "성년의 날", "부부의 날", "소만"],
    6: ["현충일", "망종", "하지", "단오", "환경의 날"],
    7: ["소서", "대서", "제헌절", "초복", "중복", "정보보호의 날"],
    8: ["입추", "말복", "광복절", "처서", "칠석"],
    9: ["백로", "추분", "철도의 날", "관광의 날"],
    10: ["국군의 날", "개천절", "한글날", "한로", "상강", "할로윈", "임산부의 날"],
    11: ["입동", "소설", "빼빼로데이", "농업인의 날", "소방의 날"],
    12: ["대설", "동지", "크리스마스", "성탄절", "무역의 날", "소비자의 날"]
}

CATEGORY_MAPPING = {
    "IT/테크": ["성능", "후기", "꿀팁", "비교", "할인", "출시", "구매"],
    "육아/교육": ["준비물", "놀이", "체험", "간식", "등원룩", "필수템", "선물"],
    "경제/비즈니스": ["전망", "혜택", "절세", "신청방법", "지원금", "수익", "트렌드"],
    "맛집/여행": ["맛집", "데이트", "가볼만한곳", "숙소", "핫플", "카페", "코스"],
    "리빙/생활": ["인테리어", "청소", "레시피", "정리", "식단", "살림템", "리모델링"],
    "자기계발": ["동기부여", "루틴", "책추천", "자격증", "공부법", "성공", "습관"]
}

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
        self.init_genai_client()
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
        self.combo_cat = tb.Combobox(inner_rec, values=list(CATEGORY_MAPPING.keys()), width=15)
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
            lambda: self.run_gemini(self.prompt_step2, self.txt_out2, "character"), "info")
            
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
            lambda: self.run_gemini(self.prompt_step3, self.txt_out3, "synopsis"), "warning")
            
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
            lambda: self.run_gemini(self.prompt_step4, self.txt_out4, "draft"), "success")
            
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
        # AI to recommend topic for the selected part based on prev info
        threading.Thread(target=self._recommend_topic_task, daemon=True).start()

    def _recommend_topic_task(self):
        part = self.part_var.get()
        # Mock logic or Gemini call
        self.root.after(0, lambda: self.update_log(f"{part}회차 주제를 구상 중..."))
        # (Gemini call logic here...)
        new_topic = f"{self.data.get('target_topic', '정보')}에 관한 {part}차 특별 전략"
        self.data["series_parts"][part]["topic"] = new_topic
        self.root.after(0, lambda t=new_topic: self.lbl_current_topic.configure(text=t))
        self.save_session()

    def run_series_generation(self):
        part = self.part_var.get()
        self.run_gemini(self.prompt_step5, self.txt_out5, f"part_{part}")

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

    def _recommend_topic_task(self):
        part = self.part_var.get()
        self.root.after(0, lambda: self.update_log(f"🤖 AI가 {part}회차에 적합한 주제를 분석 중..."))
        
        # Build prompt for re-recommending topic
        topic_context = f"""
        # Context:
        - Target Topic: {self.data.get('target_topic', '')}
        - Product: {self.data.get('product', '')}
        - Synopsis: {self.txt_out3.get("1.0", END)[:500]}
        # Task:
        Recommend a catchy blog title/topic for Part {part} of 4.
        It must be curiosity-driven and related to the context.
        Output ONLY the title in Korean.
        """
        
        try:
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=topic_context
            )
            new_topic = response.text.strip().replace('"', '')
            self.data["series_parts"][part]["topic"] = new_topic
            self.root.after(0, lambda t=new_topic: self.lbl_current_topic.configure(text=t))
            self.save_session()
        except Exception as e:
            self.root.after(0, lambda: self.update_log(f"⚠️ 주제 추천 오류: {e}"))
        
        # Reference for extraction
        self.step5_img_labels = [
            self.lbl_img_step5_intro,
            self.lbl_img_step5_wall,
            self.lbl_img_step5_epiphany,
            self.lbl_img_step5_offer
        ]

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
        self.init_genai_client()
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

    def run_step1(self):
        # Validation
        if not self.entry_product.get().strip():
            messagebox.showwarning("필수 입력", "Q1. 누구를 도와주고 싶나요? (상품/서비스) 항목은 필수입니다.")
            return
        
        # 1. Text Generation
        self.run_gemini(self.prompt_step1, self.txt_out1, "customer")
        
        # 2. Image Generation (Chained)
        product = self.entry_product.get()
        pain = self.entry_pain.get()
        # Added instruction for English text only
        img_prompt = f"A photorealistic portrait of a korean person who is worrying about {pain} related to {product}. High quality, emotional, detailed face, cinematic lighting, 8k. (Important: If there is any text in the image, it must be in English only. Do NOT use Korean text.)"
        self.run_image_gen(img_prompt, self.lbl_img_step1)

    def run_gemini(self, prompt_func, widget, key):
        if not client:
            messagebox.showwarning("설정 필요", "먼저 '설정' 탭에서 API Key를 입력하고 저장해주세요.")
            self.notebook.select(self.tab_settings)
            return

        # Hook for Step 5 Image Generation
        if key == "synopsis":
             # Step 3 Series Poster Logic
             product = self.entry_product.get()
             # Build a descriptive prompt for the poster
             img_prompt = f"A dramatic Netflix movie poster for a series titled '{product}'. Cinematic lighting, high quality 8k, emotional atmosphere, professional design, text-free. (Important: The image MUST NOT contain any text or letters.)"
             self.run_image_gen(img_prompt, self.lbl_img_step3)

        if key == "final_script":
             # We will extract prompts from the generated text instead of a single fixed prompt
             pass

        prompt = prompt_func()
        widget.delete("1.0", END)
        widget.insert("1.0", "⏳ AI 캡틴이 열심히 글을 쓰고 있습니다... (잠시만 기다려주세요)")
        
        def task():
            try:
                # NEW SDK usage: client.models.generate_content
                print(f"DEBUG: Calling Gemini for {key}...")
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        max_output_tokens=8000, # Increased limit to prevent truncation while stopping infinite loops
                        temperature=0.7
                    )
                )
                print(f"DEBUG: Gemini Response received for {key}")
                result = response.text
                if not result:
                     print("DEBUG: Result is empty/None")
                     result = "(AI가 반환한 내용이 없습니다. 안전 필터나 기타 이유일 수 있습니다.)"
                
                print(f"DEBUG: Streaming result len={len(result)}")
                self.root.after(0, lambda: self.stream_text(widget, result))
                
                if key == "final_script":
                    # Extraction logic for sectional images
                    import re
                    # Look for markers like **[Image Prompt for Nano Banana]**: ...
                    prompts = re.findall(r"\*\*\[Image Prompt for Nano Banana\]\*\*:\s*(.*?)(?:\n|$)", result)
                    
                    for i, p in enumerate(prompts):
                        if i < len(self.step5_img_labels):
                            # Clean prompt and run
                            clean_p = p.strip()
                            if clean_p:
                                # Add base styling if not present to ensure quality
                                if "Pixar" not in clean_p:
                                     clean_p += ", 3D Pixar animation style, high quality render"
                                
                                print(f"DEBUG: Triggering image gen for Step 5 section {i+1}: {clean_p[:50]}...")
                                self.run_image_gen(clean_p, self.step5_img_labels[i])

                if key.startswith("part_"):
                    p_num = key.split("_")[1]
                    self.data["series_parts"][p_num]["content"] = result
                    self.save_session()

                if key:
                    self.data[key] = result
                    self.save_session()
                    
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda m=error_msg: widget.insert(END, f"\n\n[Error]: {m}"))
        
        threading.Thread(target=task, daemon=True).start()

    # --- Keyword Mining Logic ---
    def run_keyword_mining(self):
        keywords_str = self.entry_keywords.get().strip()
        if not keywords_str:
            messagebox.showwarning("입력 필요", "분석할 키워드를 입력해주세요.")
            return
        
        limit = int(self.entry_limit.get().strip() or "30")
        nav = self.data.get("naver_api", {})
        
        if not all([nav.get("naver_access_key"), nav.get("naver_secret_key"), nav.get("naver_customer_id")]):
            messagebox.showwarning("설정 필요", "먼저 '설정' 탭에서 네이버 API 키를 입력해주세요.")
            self.notebook.select(self.tab_settings)
            return

        self.keyword_table.delete_rows()
        self.update_log("채굴을 시작합니다 (0121 버전 로직)...", clear=True)
        
        initial_keywords = [k.strip().replace(" ", "") for k in keywords_str.split(",") if k.strip()]
        
        def mining_task():
            try:
                keyword_queue = deque(initial_keywords)
                searched_keywords = set()
                recorded_keywords = set()
                all_results = []
                count = 0
                
                while keyword_queue and count < limit:
                    current = keyword_queue.popleft()
                    if current in searched_keywords: continue
                    
                    searched_keywords.add(current)
                    self.root.after(0, lambda k=current: self.update_log(f"🔍 '{k}' 분석 중..."))
                    
                    stats = self.get_naver_keyword_stats(
                        nav["naver_access_key"], nav["naver_secret_key"], nav["naver_customer_id"], [current]
                    )
                    
                    if stats and "keywordList" in stats:
                        for item in stats["keywordList"]:
                            if count >= limit: break
                            rel = item.get("relKeyword", "N/A")
                            if rel in recorded_keywords: continue
                            
                            pc = item.get("monthlyPcQcCnt", "N/A")
                            mo = item.get("monthlyMobileQcCnt", "N/A")
                            
                            try:
                                pc_val = int(pc) if pc not in ["<10", "N/A"] else 0
                                mo_val = int(mo) if mo not in ["<10", "N/A"] else 0
                                total = pc_val + mo_val
                                if total == 0 and ("<10" in [pc, mo]): total = "<10"
                            except: total = "N/A"
                            
                            doc_count = self.get_naver_document_count(rel, nav["naver_client_id"], nav["naver_client_secret"])
                            comp = "N/A"
                            try:
                                calc_total = total if isinstance(total, int) else (5 if total == "<10" else 0)
                                if calc_total > 0: comp = round(doc_count / calc_total, 2)
                            except: pass
                            
                            row = (rel, pc, mo, total, doc_count, comp)
                            all_results.append(row)
                            recorded_keywords.add(rel)
                            count += 1
                            self.root.after(0, lambda r=row: self.append_keyword_row(r))
                            
                            if count < limit and rel not in searched_keywords and rel not in keyword_queue:
                                keyword_queue.append(rel)
                                
                all_results.sort(key=lambda x: (x[5] if isinstance(x[5], (int, float)) else 999999))
                self.root.after(0, lambda: self.keyword_table.delete_rows())
                for r in all_results:
                    self.root.after(0, lambda row=r: self.append_keyword_row(row))
                
                self.root.after(0, lambda: self.update_log(f"✅ 채굴 완료! 총 {count}개 발굴 (경쟁률순 정렬됨)."))
                self.save_session()
                
            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda m=err_msg: self.update_log(f"❌ 치명적 오류: {m}"))
                self.root.after(0, lambda m=err_msg: messagebox.showerror("채굴 중단", m))

        threading.Thread(target=mining_task, daemon=True).start()

    def generate_naver_signature(self, secret_key, timestamp, method, request_uri):
        message = f"{timestamp}.{method}.{request_uri}"
        h = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
        return base64.b64encode(h.digest()).decode('utf-8')

    def get_naver_keyword_stats(self, access_key, secret_key, customer_id, hint_keywords):
        request_uri = "/keywordstool"
        method = "GET"
        timestamp = str(int(time.time() * 1000))
        try:
            signature = self.generate_naver_signature(secret_key, timestamp, method, request_uri)
            headers = {
                "X-Timestamp": timestamp,
                "X-API-KEY": access_key,
                "X-Customer": customer_id,
                "X-Signature": signature
            }
            params = {"hintKeywords": ",".join(hint_keywords), "showDetail": "1"}
            url = f"https://api.naver.com{request_uri}"
            import requests
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda m=err_msg: self.update_log(f"⚠️ 검색광고 API 오류: {m}"))
            return {}

    def get_naver_document_count(self, keyword, client_id, client_secret):
        encText = urllib.parse.quote(keyword)
        url = f"https://openapi.naver.com/v1/search/blog?query={encText}&display=1"
        headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
        try:
            import requests
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            return response.json().get("total", 0)
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda m=err_msg: self.update_log(f"⚠️ 블로그 API 오류({keyword}): {m}"))
            return 0

    def run_keyword_mining(self):
        keywords_str = self.entry_keywords.get().strip()
        if not keywords_str:
            messagebox.showwarning("입력 필요", "분석할 키워드를 입력해주세요.")
            return
        
        limit = int(self.entry_limit.get().strip() or "30")
        nav = self.data.get("naver_api", {})
        
        if not all([nav.get("naver_access_key"), nav.get("naver_secret_key"), nav.get("naver_customer_id")]):
            messagebox.showwarning("설정 필요", "먼저 '설정' 탭에서 네이버 API 키를 입력해주세요.")
            self.notebook.select(self.tab_settings)
            return

        self.keyword_table.delete_rows()
        self.update_log("채굴을 시작합니다 (0121 버전 로직)...", clear=True)
        
        initial_keywords = [k.strip().replace(" ", "") for k in keywords_str.split(",") if k.strip()]
        
        def mining_task():
            try:
                keyword_queue = deque(initial_keywords)
                searched_keywords = set()
                recorded_keywords = set()
                all_results = []
                count = 0
                
                while keyword_queue and count < limit:
                    current = keyword_queue.popleft()
                    if current in searched_keywords: continue
                    
                    searched_keywords.add(current)
                    self.root.after(0, lambda k=current: self.update_log(f"🔍 '{k}' 분석 중..."))
                    
                    stats = self.get_naver_keyword_stats(
                        nav["naver_access_key"], nav["naver_secret_key"], nav["naver_customer_id"], [current]
                    )
                    
                    if stats and "keywordList" in stats:
                        for item in stats["keywordList"]:
                            if count >= limit: break
                            rel = item.get("relKeyword", "N/A")
                            if rel in recorded_keywords: continue
                            
                            pc = item.get("monthlyPcQcCnt", "N/A")
                            mo = item.get("monthlyMobileQcCnt", "N/A")
                            
                            # Calculate Total
                            try:
                                pc_val = int(pc) if pc not in ["<10", "N/A"] else 0
                                mo_val = int(mo) if mo not in ["<10", "N/A"] else 0
                                total = pc_val + mo_val
                                if total == 0 and ("<10" in [pc, mo]): total = "<10"
                            except: total = "N/A"
                            
                            doc_count = self.get_naver_document_count(rel, nav["naver_client_id"], nav["naver_client_secret"])
                            
                            # Comp Rate
                            comp = "N/A"
                            try:
                                calc_total = total if isinstance(total, int) else (5 if total == "<10" else 0)
                                if calc_total > 0: comp = round(doc_count / calc_total, 2)
                            except: pass
                            
                            row = (rel, pc, mo, total, doc_count, comp)
                            all_results.append(row)
                            recorded_keywords.add(rel)
                            count += 1
                            
                            # Update UI Real-time
                            self.root.after(0, lambda r=row: self.append_keyword_row(r))
                            
                            # BFS Expansion
                            if count < limit and rel not in searched_keywords and rel not in keyword_queue:
                                keyword_queue.append(rel)
                                
                # Sort by Comp Rate (ascending)
                all_results.sort(key=lambda x: (x[5] if isinstance(x[5], (int, float)) else 999999))
                
                # Update UI with sorted results
                self.root.after(0, lambda: self.keyword_table.delete_rows())
                for r in all_results:
                    self.root.after(0, lambda row=r: self.append_keyword_row(row))
                
                self.root.after(0, lambda: self.update_log(f"✅ 채굴 완료! 총 {count}개 발굴 (경쟁률순 정렬됨)."))
                self.save_session()
                
            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda m=err_msg: self.update_log(f"❌ 치명적 오류: {m}"))
                self.root.after(0, lambda m=err_msg: messagebox.showerror("채굴 중단", m))

        threading.Thread(target=mining_task, daemon=True).start()

    def append_keyword_row(self, row):
        # Tableview build_table_data is more stable for bulk, but for real-time we use insert
        # Tableview.view is the underlying Treeview
        self.keyword_table.view.insert('', END, values=row)

    def update_log(self, message, clear=False):
        self.log_display.configure(state="normal")
        if clear: self.log_display.delete("1.0", "end")
        self.log_display.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_display.see("end")
        self.log_display.configure(state="disabled")

    # --- 스마트 추천 로직 (2단계 고도화 버전) ---
    def run_smart_recommendation(self):
        """1차 기념일 + 2차 카테고리 융합 스마트 키워드 추천"""
        threading.Thread(target=self._generate_smart_keywords_task, daemon=True).start()

    def _generate_smart_keywords_task(self):
        try:
            self.root.after(0, lambda: self.btn_smart_rec.configure(state="disabled", text="⚡ 도킹 분석 중..."))
            self.root.after(0, lambda: self.update_log("🚀 2단계 지능형 추천 엔진 가동 중..."))
            
            m = int(self.combo_month.get())
            c = self.combo_cat.get()
            
            # [1단계] 씨앗(Seed) 키워드 도출
            calendar_seeds = CALENDAR_EVENTS.get(m, [])
            seasonal_seeds = SEASONAL_DATA.get(m, [])
            suffixes = CATEGORY_MAPPING.get(c, [])
            
            seeds = list(set(calendar_seeds + seasonal_seeds))
            
            # [2단계] 카테고리 융합(Fusion) 키워드 도출 (띄어쓰기 없이)
            niche_candidates = []
            for seed in seeds:
                for suff in suffixes[:3]: # 상위 3개 속성 융합
                    niche_candidates.append(f"{seed}{suff}")
            
            self.root.after(0, lambda: self.update_log(f"🔍 1차 씨앗({len(seeds)}개)에서 2차 파생 키워드({len(niche_candidates)}개)를 생성했습니다."))
            
            nav = self.data.get("naver_api", {})
            ak, sk, cid = nav.get("naver_access_key"), nav.get("naver_secret_key"), nav.get("naver_customer_id")
            client_id, client_secret = nav.get("naver_client_id"), nav.get("naver_client_secret")
            
            final_keywords = []

            # 네이버 검색광고 API 연동 가능 시 실제 유의미한 키워드 필터링
            if ak and sk and cid:
                self.root.after(0, lambda: self.update_log("📊 네이버 API를 통해 실제 검색 데이터를 매칭 중..."))
                # 상위 5개 조합에 대해 연관 키워드 추출
                sub_samples = seeds[:2] + niche_candidates[:3]
                stats = self.get_naver_keyword_stats(ak, sk, cid, sub_samples)
                
                if stats and "keywordList" in stats:
                    # 실제 존재하는 연관 키워드들 수집
                    for item in stats["keywordList"][:15]:
                        kw = item.get("relKeyword", "").replace(" ", "")
                        if not kw: continue
                        # 불필요 단어 필터링
                        if any(bad in kw for bad in ["추천", "사용법"]): continue
                        final_keywords.append(kw)
            
            # API 데이터가 없거나 보조용으로 1, 2차 키워드 섞기
            combined_raw = niche_candidates[:5] + seeds[:5]
            for kw in combined_raw:
                if kw not in final_keywords:
                    final_keywords.append(kw.replace(" ", ""))
            
            # 중복 제거 및 최종 정제
            final_keywords = list(dict.fromkeys(final_keywords))[:10]
            
            # 네이버 데이터랩 트렌드 이슈 확인 (상위 5개)
            if client_id and client_secret:
                self.root.after(0, lambda: self.update_log("🔥 급상승 트렌드 검증 중..."))
                trend_data = self.get_datalab_trend(client_id, client_secret, final_keywords[:5])
                if trend_data and 'results' in trend_data:
                    scores = {item['title']: (item['data'][-1]['ratio'] if item['data'] else 0) for item in trend_data['results']}
                    final_keywords = [f"🔥{k}" if scores.get(k, 0) > 30 else k for k in final_keywords]
            
            # UI 반영
            result_str = ", ".join(final_keywords)
            self.root.after(0, lambda: self.entry_keywords.delete(0, END))
            self.root.after(0, lambda: self.entry_keywords.insert(0, result_str))
            
            self.root.after(0, lambda: self.update_log(f"✅ 완성! {c} 카테고리에 최적화된 2단계 추천 키워드 10개를 선별했습니다."))
            
        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda m=err_msg: self.update_log(f"⚠️ 추천 엔진 오류: {m}"))
        finally:
            self.root.after(0, lambda: self.btn_smart_rec.configure(state="normal", text="⚡ 스마트 글감 제안"))

    def get_datalab_trend(self, client_id, client_secret, keywords):
        """네이버 데이터랩 통합검색어 트렌드 조회"""
        url = "https://openapi.naver.com/v1/datalab/search"
        headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
            "Content-Type": "application/json"
        }
        
        # 최근 30일 데이터 조회
        body = {
            "startDate": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
            "endDate": datetime.now().strftime("%Y-%m-%d"),
            "timeUnit": "date",
            "keywordGroups": [{"groupName": k, "keywords": [k]} for k in keywords]
        }
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(body))
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except:
            return None
        self.keyword_table.goto_first_page()

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
        if not client:
             # run_gemini will catch this first, but for direct calls:
             return

        label_widget.configure(text="🎨 Nano Banana가 그림을 그리고 있습니다...", image="")
        
        def task():
            try:
                # User-provided pattern for 'gemini-2.5-flash-image'
                response = client.models.generate_content(
                    model='gemini-2.5-flash-image',
                    contents=[prompt]
                )
                
                image_found = False
                if response.parts:
                    for part in response.parts:
                        if part.inline_data:
                            # Direct bytes approach to ensure PIL Image compatibility
                            try:
                                img_data = part.inline_data.data
                                image = Image.open(io.BytesIO(img_data))
                            except:
                                # Fallback if direct data access fails, try saving to buffer if as_image returns wrapper
                                # But standard genai parts usually have inline_data.data as bytes
                                g_image = part.as_image()
                                buffer = io.BytesIO()
                                g_image.save(buffer, format="PNG")
                                buffer.seek(0)
                                image = Image.open(buffer)
                            
                            # Resize for UI
                            image.thumbnail((400, 400))
                            photo = ImageTk.PhotoImage(image)
                            
                            # Cache PIL image for download
                            label_widget.pil_image = image 
                            
                            self.root.after(0, lambda p=photo, lw=label_widget: self.update_image_label(lw, p))
                            image_found = True
                            break
                
                if not image_found:
                      self.root.after(0, lambda lw=label_widget: lw.configure(text="이미지 생성 실패: 결과 없음"))

            except Exception as e:
                error_msg = str(e)
                print(f"Image Gen Error: {error_msg}")
                # Fallback on error
                self.root.after(0, lambda m=error_msg, lw=label_widget: self.update_placeholder_image_safe(lw, m))

        threading.Thread(target=task, daemon=True).start()

    def update_placeholder_image_safe(self, label, error_text):
        self.create_placeholder_image(label, f"Error:\n{error_text[:50]}...")

    def create_placeholder_image(self, label, text):
        img = Image.new('RGB', (400, 300), color=(52, 152, 219))
        d = ImageDraw.Draw(img)
        try:
            d.text((10, 150), text, fill=(255, 255, 255))
        except:
            pass
        photo = ImageTk.PhotoImage(img)
        self.update_image_label(label, photo)

    def update_image_label(self, label, photo):
        label.configure(image=photo, text="")
        label.image = photo 

    def copy_to_clip(self, widget):
        text = widget.get("1.0", END).strip()
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        
        toast = ToastNotification(
            title="복사 완료!",
            message="클립보드에 저장되었습니다.\n원하는 곳에 붙여넣기(Ctrl+V) 하세요.",
            duration=3000,
            bootstyle="success"
        )
        toast.show_toast()

    def save_to_file(self, widget):
        text = widget.get("1.0", END).strip()
        if not text:
            messagebox.showwarning("경고", "저장할 내용이 없습니다.")
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="결과물 저장하기"
        )
        
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(text)
                messagebox.showinfo("저장 완료", f"파일이 성공적으로 저장되었습니다.\n{filename}")
            except Exception as e:
                messagebox.showerror("오류", f"저장 중 오류가 발생했습니다: {e}")

    # --- Prompts ---
    def prompt_step1(self):
        product = self.get_input(self.entry_product, "판매할 상품을 상상해서 제안해주세요")
        pain = self.get_input(self.entry_pain, "이 상품을 필요로 하는 사람의 고통을 상상해주세요")
        return f"""
        # Goal: Step 1. Define Dream Customer
        # Input Data:
        - Product: {product}
        - Pain: {pain}
        # Task:
        1. Identify the most desperate target audience.
        2. Define their Persona (Age, Job, Situation, Deepest Desire).
        3. Write in Korean, friendly and clear.
        
        **Output strictly in Markdown.**
        Structure:
        - **Target Audience**: ...
        - **Demographics**: ...
        - **Psychographics (Desire/Pain)**: ...
        """

    def prompt_step2(self):
        # Link Logic: Read Step 1 output
        customer_profile = self.txt_out1.get("1.0", END).strip()
        
        role = self.get_input(self.entry_role, "고객에게 신뢰를 줄 수 있는 역할을 추천해주세요")
        flaw = self.get_input(self.entry_flaw, "인간미가 느껴지는 작은 결점을 만들어주세요")
        back = self.get_input(self.entry_backstory, "공감을 얻을 수 있는 실패 경험담을 만들어주세요")
        
        persona = self.combo_persona.get()
        self.data["persona_style"] = persona
        
        return f"""
        # Goal: Step 2. Define Attractive Character
        # Context (Target Audience):
        {customer_profile}
        
        # Identity Style (Strictly Follow This):
        - Style: {persona}
        
        # Input Data:
        - Role: {role}
        - Flaw: {flaw}
        - Backstory: {back}
        # Task:
        1. Create a character profile that is the PERFECT GUIDE for the Target Audience above.
        2. Body tone and voice must perfectly match the chosen Style: '{persona}'.
        3. Format clearly. Language: Korean.
        
        **Output strictly in Markdown.**
        Structure:
        - **Name/Title**: ...
        - **Style/Vibe**: ...
        - **Role (Identity)**: ...
        - **Flaw (Vulnerability)**: ...
        - **Backstory**: ...
        """

    def prompt_step3(self):
        customer = self.txt_out1.get("1.0", END).strip()
        character = self.txt_out2.get("1.0", END).strip()
        
        secret = self.get_input(self.entry_secret, "사람들이 아직 모르는 특별한 기회나 비밀을 상상해주세요")
        wall = self.get_input(self.entry_wall, "가장 좌절했던 순간의 구체적인 감정을 묘사해주세요")
        epiphany = self.get_input(self.entry_epiphany, "모든 상황을 반전시킨 결정적 깨달음을 상상해주세요")
        cta = self.get_input(self.entry_cta, "삶의 변화와 독자에게 줄 가치 있는 제안을 만들어주세요")
        
        strategy = self.story_var.get()
        self.data["story_strategy"] = strategy
        
        strategy_instruction = ""
        if strategy == "Soap":
            strategy_instruction = """
            [Strategy: Sequential Soap Opera (The Slide)]
            - Each episode must follow Russell Brunson's Slide strategy.
            - Ep 1 leads to Problem A, solved by epiphany, but discovers New Problem B.
            - Ep 2 solves Problem B, but discovers New Problem C.
            - Ep 3 solves Problem C, leading to the grand vision.
            - Ep 4 presents the Final Offer as the ultimate solution for everything.
            - High tension and constant 'What's next?' hooks.
            """
        else:
            strategy_instruction = """
            [Strategy: Standard 4-part Synopsis]
            - Classic narrative arc: Hook -> Struggle -> Epiphany -> Result.
            - Focus on a single coherent story divided into 4 parts.
            """

        return f"""
        # Role: Series Planning Lead Author (Soap Opera Specialist)
        # Goal: Plan a 4-part Blog Series using Russell Brunson's Sequence & 2026 Naver SEO logic.
        
        # Context Data:
        - Hero (Character): {character}
        - Audience (Dream Customer): {customer}
        
        # Strategy Choice:
        {strategy_instruction}
        
        # Input Data:
        1. Secret/Opportunity: {secret}
        2. The Wall (Failure): {wall}
        3. The Epiphany (Solution): {epiphany}
        4. Transformation/CTA: {cta}
            
        # [Strategy Guidelines - 2026 Naver SEO]
        1. **Avoid AI Summary**: Focus on unique human 'Experience' and emotional narrative.
        2. **Home Feed Strategy**: Use curiosity-driven titles and strong hooks.
        3. **Maximize Dwell Time**: Use 'Open Loops' at the end of each episode to encourage reading the next one.
        
        # [Task]
        Create a 4-part synopsis based on the '{strategy}' strategy.
        
        # [Output Format]
        Create a **[4-part Series Planning Table]** in Markdown:
        - [Episode #]
        - [Naver Home Feed Title] (Keyword + Clickable Copy)
        - [Core Content] (Experience-focused summary)
        - [Open Loop] (Ending sentence to hook into next episode)
        
        Language: Korean.
        """

        
    def prompt_step4(self):
        synopsis = self.txt_out3.get("1.0", END).strip()
        character = self.txt_out2.get("1.0", END).strip()
        episode = self.get_input(self.entry_episode, "제1화를 작성해주세요")
        scene = self.get_input(self.entry_detail_scene, "비참하거나 극적인 현장 분위기를 묘사해주세요")
        inner = self.get_input(self.entry_detail_inner, "절망적이거나 간절한 속마음을 묘사해주세요")
        
        return f"""
        # Goal: Step 4. Write Content Draft (Story Alchemist)
        # Target Episode: {episode}
        # Deep Details:
        - Scene Sensory: {scene}
        - Inner Voice: {inner}
        # Context:
        - Synopsis: {synopsis}
        - Character: {character}
        # Task:
        # Task:
        Write a high-immersion blog post draft.
        **Output strictly in Markdown.**
        
        Structure:
        - **Scene Setting**: (Sensory details)
        - **Inner Monologue**: (Character's thoughts)
        - **Dialogue**: (Conversation)
        - **Action**: (What happens)
        """

    def prompt_step5(self):
        # 데이터 수집 (Step 1~4 결과물)
        customer = self.txt_out1.get("1.0", END).strip() 
        topic = self.lbl_current_topic.cget("text")
        part = self.part_var.get()
        
        # UI 입력값
        product = self.data.get("product", "")
        nickname = self.get_input(self.entry_nickname, "마케팅 캡틴")
        target_topic = self.data.get("target_topic", "")
        
        persona_style = self.data.get("persona_style", "Friendly")

        # Part-specific guidance
        part_guide = ""
        if part == "1":
            part_guide = "1회차: 주인공의 현재 상황과 결핍, 그리고 새로운 기회(씨앗) 발견. 독자의 호기심 극대화."
        elif part == "2":
            part_guide = "2회차: 기회를 잡으려다 마주친 예상치 못한 장벽과 실패, 절망감 묘사."
        elif part == "3":
            part_guide = "3회차: 장벽을 허무는 결정적인 '깨달음(Epiphany)'과 새로운 시각."
        elif part == "4":
            part_guide = f"4회차: 완벽한 해결책인 '{product}' 제시 및 상업적 행동(CTA) 촉구."

        return f"""
        # Role: 마케팅 캡틴 (시리즈 작가)
        # Goal: 4부작 중 {part}회차 포스팅 원고 작성
        
        # 현 회차 가이드: {part_guide}
        
        # 맥락 정보:
        - 시리즈 전체 주제: {target_topic}
        - 이번 회차 제목(주제): {topic}
        - 최종 판매 상품: {product}
        - 타겟 고객: {customer}
        - 작가 페르소나 스타일: {persona_style}
        - 닉네임: {nickname}
        
        # [작성 지침]
        1. 네이버 2026 알고리즘 최적화: '직접 경험한 스토리' 형식.
        2. 몰입도: Sensory & Inner Voice 활용.
        3. 이미지 프롬프트: '[Image Prompt for Nano Banana]: (English Prompt)' 형식을 본문 중간에 4번 반드시 포함 (Pixar 3D style).
        4. 말투: '{persona_style}' 대화체.
        
        ---
        # [출력 구성]
        - **Viral 제목 (3가지)**
        - **본문 원고** (가독성 있게 작성)
        - **4개의 이미지 프롬프트** (본문 중간중간 배치)
        """


if __name__ == "__main__":
    # Theme: Cosmo (Modern Blue/White)
    root = tb.Window(themename="cosmo") 
    app = MarketingWizardApp(root)
    root.mainloop()
