import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import queue
import time
import json
import os
import sys
import hmac
import hashlib
import base64
import requests
import google.generativeai as genai
from datetime import datetime, timedelta
from collections import deque
import openpyxl
import urllib.parse
import re

# --- [Selenium 라이브러리] ---
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    import pyperclip
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# --- [설정] 네이버 API ---
NAVER_AD_API_BASE_URL = "https://api.naver.com"
NAVER_DATALAB_API_URL = "https://openapi.naver.com/v1/datalab/search"

# --- [데이터] 시즌/캘린더 ---
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
    "IT/테크": ["추천", "사용법", "후기", "꿀팁", "비교", "할인"],
    "육아/교육": ["준비물", "놀이", "체험", "간식", "등원룩"],
    "경제/비즈니스": ["전망", "혜택", "절세", "신청방법", "지원금"],
    "맛집/여행": ["맛집", "데이트", "가볼만한곳", "숙소", "핫플"],
    "리빙/생활": ["인테리어", "청소", "레시피", "정리", "식단"],
    "자기계발": ["동기부여", "루틴", "책추천", "자격증", "공부법"]
}

# --- [NEW] 카테고리별 AI 페르소나 설정 ---
CATEGORY_PROMPTS = {
    "IT/테크": "IT/테크 전문 리뷰어로서, 스펙/기능/효율성/혁신성을 중심으로 분석적이고 전문적인 톤으로",
    "육아/교육": "육아/교육 멘토로서, 아이의 성장/공감/양육 팁/교육 정보를 중심으로 따뜻하고 격려하는 톤으로",
    "경제/비즈니스": "경제/비즈니스 분석가로서, 수익성/전망/절세 전략/트렌드를 중심으로 논리적이고 신뢰감 있는 톤으로",
    "맛집/여행": "맛집/여행 에디터로서, 맛/분위기/위치/포토스팟/경험을 중심으로 생생하고 감성적인 톤으로",
    "리빙/생활": "리빙/살림 전문가로서, 인테리어/정리수납/살림 꿀팁/가성비를 중심으로 실용적이고 친근한 톤으로",
    "자기계발": "동기부여 코치로서, 루틴/마인드셋/성장/성공 습관을 중심으로 열정적이고 설득력 있는 톤으로"
}

class CommandCenterApp(ctk.CTk):
    CONFIG_FILE = "config_unified.json"
    MAX_KEYWORDS = 10000
    
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("20기 마케팅 커맨드 센터 (v11.0 Fair Miner)")
        self.geometry("1300x950")

        self.log_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.current_thread = None
        self.api_entries = {}
        self.chat_session = None
        self.all_keyword_data = []
        
        self.auto_move_to_stage2 = ctk.BooleanVar(value=True) 
        
        self.config_data = self._load_config()
        self._create_layout()
        self.after(100, self._check_log_queue)

        if not SELENIUM_AVAILABLE:
            messagebox.showwarning("설치 필요", "pip install selenium webdriver_manager pyperclip")

    def _create_layout(self):
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        
        ctk.CTkLabel(self.sidebar, text="⚙️ 시스템 설정", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)
        
        ctk.CTkLabel(self.sidebar, text="[네이버 로그인]", text_color="#2ECC71").pack(anchor="w", padx=10)
        self._create_sidebar_entry("네이버 ID", "NAVER_LOGIN_ID")
        self._create_sidebar_entry("네이버 PW", "NAVER_LOGIN_PW", show="*")
        
        ctk.CTkFrame(self.sidebar, height=2, fg_color="gray").pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(self.sidebar, text="[네이버 검색 API]", text_color="cyan").pack(anchor="w", padx=10)
        self._create_sidebar_entry("Cust. ID", "NAVER_SEARCH_CUSTOMER_ID")
        self._create_sidebar_entry("License", "NAVER_SEARCH_ACCESS_LICENSE_KEY", show="*")
        self._create_sidebar_entry("Secret", "NAVER_SEARCH_SECRET_KEY", show="*")
        self._create_sidebar_entry("Client ID", "NAVER_BLOG_CLIENT_ID")
        self._create_sidebar_entry("Cli. Secret", "NAVER_BLOG_CLIENT_SECRET", show="*")
        
        ctk.CTkFrame(self.sidebar, height=2, fg_color="gray").pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(self.sidebar, text="[Gemini API]", text_color="yellow").pack(anchor="w", padx=10)
        self._create_sidebar_entry("API Key", "GEMINI_API_KEY", show="*")
        
        ctk.CTkButton(self.sidebar, text="설정 저장", command=self._save_config_btn, fg_color="#555").pack(pady=20)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(side="right", fill="both", expand=True, padx=20, pady=10)
        
        self.tab_miner = self.tabview.add("1단계: 기획 (채굴)")
        self.tab_interview = self.tabview.add("2단계: 설계 (인터뷰)")
        self.tab_writer = self.tabview.add("3단계: 생산 (글쓰기)")
        self.tab_publisher = self.tabview.add("4단계: 발행 (자동화)")
        
        self._setup_miner_tab()
        self._setup_interview_tab()
        self._setup_writer_tab()
        self._setup_publisher_tab()

    def _create_sidebar_entry(self, label, key, show=None):
        ctk.CTkLabel(self.sidebar, text=label, font=("Arial", 12)).pack(anchor="w", padx=15, pady=(5,0))
        entry = ctk.CTkEntry(self.sidebar, height=30, show=show)
        entry.pack(fill="x", padx=15, pady=(0, 5))
        if saved_val := self.config_data.get(key, ""): entry.insert(0, saved_val)
        self.api_entries[key] = entry

    # =========================================================================
    # [Tab 1] 키워드 채굴
    # =========================================================================
    def _setup_miner_tab(self):
        rec_frame = ctk.CTkFrame(self.tab_miner, fg_color="#2b2b2b", border_color="#3a7ebf", border_width=2)
        rec_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(rec_frame, text="✨ AI 트렌드 & 기념일 추천", font=("Malgun Gothic", 16, "bold")).pack(anchor="w", padx=15, pady=10)
        inner = ctk.CTkFrame(rec_frame, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=(0, 10))
        
        self.month_combo = ctk.CTkComboBox(inner, values=[str(i) for i in range(1, 13)], width=70)
        self.month_combo.set(str(datetime.now().month))
        self.month_combo.pack(side="left", padx=5)
        self.cat_combo = ctk.CTkComboBox(inner, values=list(CATEGORY_MAPPING.keys()), width=130)
        self.cat_combo.set("IT/테크")
        self.cat_combo.pack(side="left", padx=5)
        
        self.magic_btn = ctk.CTkButton(inner, text="⚡ 키워드 자동 생성", command=self._generate_smart_keywords_threaded, fg_color="#D35400", width=150)
        self.magic_btn.pack(side="left", padx=10)

        input_frame = ctk.CTkFrame(self.tab_miner, fg_color="transparent")
        input_frame.pack(fill="x", padx=10)
        
        self.miner_keyword_entry = ctk.CTkEntry(input_frame, placeholder_text="검색할 키워드 (쉼표 구분)", height=40)
        self.miner_keyword_entry.pack(fill="x", pady=(5, 10))
        
        ctk.CTkCheckBox(input_frame, text="완료 시 황금 키워드로 2단계 자동 이동", variable=self.auto_move_to_stage2).pack(anchor="w", padx=10, pady=(0, 10))
        
        btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_frame.pack(fill="x")
        
        self.miner_count = ctk.CTkEntry(btn_frame, width=80)
        self.miner_count.insert(0, "30")
        self.miner_count.pack(side="left", padx=(0, 10))
        ctk.CTkLabel(btn_frame, text="개 조회").pack(side="left", padx=(0, 10))
        
        self.start_btn = ctk.CTkButton(btn_frame, text="데이터 채굴 시작", command=self._start_mining)
        self.start_btn.pack(side="left", padx=5)
        self.stop_btn = ctk.CTkButton(btn_frame, text="중지", command=self._stop_mining, fg_color="#8b1a1a", state="disabled")
        self.stop_btn.pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="👉 인터뷰 연결", command=self._transfer_to_interview, fg_color="#2E8B57").pack(side="right", padx=5)

        self.miner_log = ctk.CTkTextbox(self.tab_miner, height=300)
        self.miner_log.pack(fill="both", expand=True, padx=10, pady=10)

    # --- 트렌드 생성 (기념일 우선) ---
    def _generate_smart_keywords_threaded(self): threading.Thread(target=self._generate_smart_keywords, daemon=True).start()
    def _generate_smart_keywords(self):
        try:
            self.magic_btn.configure(state="disabled", text="분석 중...")
            self._log_miner("🔄 캘린더 기념일 최우선 분석 중...")
            m = int(self.month_combo.get()); c = self.cat_combo.get()
            
            calendar_seeds = CALENDAR_EVENTS.get(m, [])
            seasonal_seeds = SEASONAL_DATA.get(m, [])
            suffixes = CATEGORY_MAPPING.get(c, [])
            
            candidates = []
            for evt in calendar_seeds:
                for suff in suffixes[:2]: candidates.append(f"{evt}{suff}")
                candidates.append(evt)
            for seed in seasonal_seeds[:3]:
                for suff in suffixes[:2]: candidates.append(f"{seed}{suff}")
            
            candidates = list(set([k.replace(" ","") for k in candidates]))
            trend_candidates = candidates[:5]
            
            client_id = self.api_entries["NAVER_BLOG_CLIENT_ID"].get().strip()
            client_secret = self.api_entries["NAVER_BLOG_CLIENT_SECRET"].get().strip()
            
            final_keywords = candidates
            if client_id and client_secret:
                trend_data = self._get_datalab_trend(client_id, client_secret, trend_candidates)
                if trend_data:
                    scores = {item['title']: (item['data'][-1]['ratio'] if item['data'] else 0) for item in trend_data.get('results', [])}
                    sorted_kws = sorted(scores.items(), key=lambda x:x[1], reverse=True)
                    final_keywords = [f"🔥{k}" if score > 30 else k for k, score in sorted_kws]
                    remaining = [k for k in candidates if k not in trend_candidates]
                    final_keywords.extend(remaining)
                    self._log_miner("✅ 트렌드 반영 완료 (기념일 우선)")
            
            self.after(0, lambda: self._update_entry(self.miner_keyword_entry, ", ".join(final_keywords[:10])))
        except Exception as e: self._log_miner(f"오류: {e}")
        finally: self.after(0, lambda: self.magic_btn.configure(state="normal", text="⚡ 키워드 자동 생성"))

    def _get_datalab_trend(self, cid, csec, kws):
        try:
            body = {
                "startDate": (datetime.now()-timedelta(days=30)).strftime("%Y-%m-%d"),
                "endDate": datetime.now().strftime("%Y-%m-%d"),
                "timeUnit": "date",
                "keywordGroups": [{"groupName": k, "keywords": [k]} for k in kws]
            }
            res = requests.post(NAVER_DATALAB_API_URL, headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": csec, "Content-Type": "application/json"}, data=json.dumps(body))
            return res.json() if res.status_code == 200 else None
        except: return None

    def _transfer_to_interview(self):
        raw = self.miner_keyword_entry.get()
        if not raw: return
        first = raw.split(',')[0].strip().replace("🔥", "")
        self.tabview.set("2단계: 설계 (인터뷰)")
        self.interview_topic_entry.delete(0, "end")
        self.interview_topic_entry.insert(0, first)

    # =========================================================================
    # [Tab 2] 인터뷰 & 원스톱 발행 (Context AI 적용)
    # =========================================================================
    def _setup_interview_tab(self):
        top_frame = ctk.CTkFrame(self.tab_interview, fg_color="transparent")
        top_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(top_frame, text="오늘의 글감:", font=("Arial", 14, "bold")).pack(side="left")
        self.interview_topic_entry = ctk.CTkEntry(top_frame, width=300)
        self.interview_topic_entry.pack(side="left", padx=10)
        
        self.btn_start_interview = ctk.CTkButton(top_frame, text="🎤 인터뷰 시작", command=self._start_interview)
        self.btn_start_interview.pack(side="left")
        
        self.curation_mode = ctk.CTkCheckBox(top_frame, text="외부 사례 큐레이션", variable=ctk.BooleanVar(value=False))
        self.curation_mode.pack(side="left", padx=10)
        
        ctk.CTkButton(top_frame, text="🚀 인터뷰 종료 & 원스톱 발행", 
                     command=self._start_one_stop_process, fg_color="#8E44AD", hover_color="#9B59B6").pack(side="right")
        
        self.chat_area = ctk.CTkTextbox(self.tab_interview, font=("맑은 고딕", 12))
        self.chat_area.pack(fill="both", expand=True, padx=10, pady=10)
        self.chat_area.configure(state="disabled")
        
        input_frame = ctk.CTkFrame(self.tab_interview, height=50)
        input_frame.pack(fill="x", padx=10, pady=10)
        self.user_input = ctk.CTkEntry(input_frame)
        self.user_input.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.user_input.bind("<Return>", self._send_message)
        self.btn_send = ctk.CTkButton(input_frame, text="전송", width=80, command=self._send_message, state="disabled")
        self.btn_send.pack(side="right")

    def _start_interview(self):
        api_key = self.api_entries["GEMINI_API_KEY"].get().strip()
        topic = self.interview_topic_entry.get().strip()
        
        if not api_key:
            messagebox.showerror("오류", "Gemini API 키가 필요합니다.")
            return
        
        # [설정값 가져오기]
        current_cat = self.cat_combo.get()
        is_curation = self.curation_mode.get() # 큐레이션 모드 체크 여부
        
        # 1. [러셀 브런슨 스타일] 카테고리별 설득 전략 (Old vs New Opportunity)
        # 각 카테고리 독자들이 느끼는 '기존 방식의 한계'와 '새로운 기회에 대한 갈망'을 정의합니다.
        category_guide = {
            "IT/테크": "기존 장비/기술(Old)의 비효율과 답답함을 강조하고, 이 제품(New)이 가져다준 압도적 속도와 '스마트한 얼리어답터'로서의 정체성 변화를 이끌어내세요.",
            "육아/교육": "기존 훈육/교육법(Old)의 실패로 인한 죄책감을 건드리고, 이 방법(New)을 통해 찾은 아이와의 유대감과 '현명한 부모'라는 자부심을 강조하세요.",
            "경제/비즈니스": "단순 노동/저축(Old)의 한계와 불안감을 지적하고, 이 투자/사업(New)이 가져다준 경제적 자유와 '통찰력 있는 투자자'로서의 변화를 강조하세요.",
            "맛집/여행": "뻔하고 지루한 데이트/여행(Old)의 식상함을 언급하고, 이곳(New)에서 느낀 특별한 감동과 '센스 있는 사람'으로 인정받은 경험을 강조하세요.",
            "리빙/생활": "반복되는 집안일/불편함(Old)의 스트레스를 공감하고, 이 살림템/노하우(New)가 선물한 여유 시간과 '살림 고수'로서의 만족감을 강조하세요.",
            "자기계발": "의지박약으로 매번 실패했던 과거(Old)를 위로하고, 이 마인드셋/습관(New)이 만들어낸 성취와 '성장하는 사람'으로의 정체성 변화를 강조하세요."
        }
        
        direction_hint = category_guide.get(current_cat, "기존 방식의 한계를 깨닫고 새로운 기회를 통해 변화된 모습을 강조하세요.")

        # --- 프롬프트 분기 시작 ---

        # [CASE A] 큐레이션 모드 (외부 사례 분석)
        # 내 경험이 없을 때, 뉴스나 타인의 성공 사례를 분석하여 내 인사이트로 만드는 과정
        if is_curation:
            system_prompt = f"""
# Role: Expert Curator & Analyst (Case Study Mode)
주제 '{topic}'와 관련하여 **내 경험이 아닌, 외부 사례(뉴스, 유명인, 트렌드)**를 분석하여 인사이트를 도출하는 인터뷰입니다.
사용자가 검색이나 조사를 통해 알게 된 내용을 '{current_cat}' 관점에서 재해석하도록 유도하세요.

[질문 4단계] (한 번에 하나씩 질문)
1. **Context (현황/이슈)**: "{topic}"와 관련하여 사람들이 흔히 겪는 문제나, 최근 인터넷/뉴스에서 본 흥미로운 이슈(사례)는 무엇인가요? (사례를 모른다면 추천을 제안하세요)
2. **Problem (분석)**: 그 사례 속 사람들은 왜 **기존 방식(Old Opportunity)**으로는 문제를 해결하지 못했나요? 무엇이 문제였나요?
3. **Solution (발견)**: 그 사례의 주인공은 어떤 **특별한 방법(New Opportunity)**이나 기술을 사용하여 문제를 해결했나요? 우리가 벤치마킹할 핵심 포인트는 무엇인가요?
4. **Application (적용)**: 이 사례를 **'{current_cat}'** 분야인 우리에게 적용한다면, 구체적으로 어떻게 활용하여 이득을 볼 수 있을까요?

[주의사항]
- 질문은 분석적이고 통찰력 있게 하세요.
- 답변을 들은 후 "{current_cat}" 전문가 시각에서 코멘트를 덧붙여 질문하세요.

종료 포맷:
---DATA_START---
[TOPIC]: {topic}
[TYPE]: Curation
[CAT]: {current_cat}
[CONTENT]: (요약)
---DATA_END---
"""

        # [CASE B] 에피파니 브릿지 모드 (내 경험)
        # 러셀 브런슨의 스토리텔링 공식 적용
        else:
            system_prompt = f"""
# Role: Russell Brunson Style Epiphany Bridge Interviewer
당신은 러셀 브런슨의 '에피파니 브릿지' 기법을 사용하는 전문 작가입니다.
주제 '{topic}'에 대해 사용자의 경험을 인터뷰하되, 단순 정보 전달이 아닌 **"감정적 전이"와 "설득"**이 일어나는 스토리를 만드세요.

[전략 가이드: {current_cat}]
* {direction_hint}

[인터뷰 4단계 흐름] (한 번에 하나씩 질문)

1. **Backstory (배경 & 욕망)**: 
   - "그 당시 가장 간절히 원했던 목표는 무엇이었나요?" 
   - 외부적 목표(돈, 성공)와 내부적 욕망(인정, 평화)을 함께 물어보세요.

2. **Wall (장벽 & 갈등)**: 
   - "목표를 이루기 위해 **기존에 시도했던 방식(Old Opportunity)**은 무엇이었나요?"
   - "그 방식이 왜 실패했고, 그때 어떤 좌절감을 느꼈나요?" (독자가 '이건 내 얘기야'라고 느끼게 유도)

3. **Epiphany (깨달음 & 새로운 기회)**: 
   - "기존 방식으로는 안 된다는 걸 깨닫고, **새로운 방법(New Opportunity)**을 발견한 결정적 순간('아하!' 모먼트)은 언제였나요?"
   - "그것이 단순한 개선이 아니라, 완전히 새로운 기회라고 느낀 이유는 무엇인가요?"

4. **Result (결과 & 정체성 변화)**: 
   - "그 결과 구체적으로 무엇이 달라졌나요?"
   - "이제 당신은 어떤 사람이 되었나요? (정체성의 변화)"

종료 포맷:
---DATA_START---
[TOPIC]: {topic}
[TYPE]: Experience
[CAT]: {current_cat}
[CONTENT]: (요약)
---DATA_END---
"""

        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=system_prompt)
            self.chat_session = self.model.start_chat(history=[])
            
            # UI 활성화
            self.user_input.configure(state="normal")
            self.btn_send.configure(state="normal")
            self.btn_start_interview.configure(state="disabled")
            self.chat_area.configure(state="normal")
            self.chat_area.delete("1.0", "end")
            self.chat_area.configure(state="disabled")
            
            mode_msg = "🔍 큐레이션 모드 (사례 분석)" if is_curation else "📖 에피파니 모드 (내 경험)"
            self._log_chat("System", f"인터뷰 시작\n- 주제: {topic}\n- 모드: {mode_msg}\n- 전략: {current_cat} 맞춤형")
            
            threading.Thread(target=self._get_ai_response, args=("시작",), daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("오류", f"Gemini 연결 실패: {e}")

    def _send_message(self, event=None):
        text = self.user_input.get().strip()
        if not text: return
        self.user_input.delete(0, "end"); self._log_chat("나", text)
        threading.Thread(target=self._get_ai_response, args=(text,), daemon=True).start()

    def _get_ai_response(self, text):
        try:
            res = self.chat_session.send_message(text)
            if "---DATA_START---" in res.text:
                display = res.text.split("---DATA_START---")[0]
                self._log_chat("루카스봇", display)
                self._save_interview_data(res.text)
            else: self._log_chat("루카스봇", res.text)
        except: self._log_chat("System", "오류 발생")

    def _save_interview_data(self, content):
        try:
            data = content.split("---DATA_START---")[1].split("---DATA_END---")[0].strip()
            with open("daily_post_data.txt", "w", encoding="utf-8") as f: f.write(data)
            self._log_chat("System", "✅ 인터뷰 저장 완료!")
        except: pass

    def _log_chat(self, role, msg):
        self.chat_area.configure(state="normal")
        self.chat_area.insert("end", f"[{role}] {msg}\n\n"); self.chat_area.see("end")
        self.chat_area.configure(state="disabled")

    def _start_one_stop_process(self):
        if not os.path.exists("daily_post_data.txt"):
            if not messagebox.askyesno("경고", "저장된 데이터가 없습니다. 계속할까요?"): return
        self.tabview.set("3단계: 생산 (글쓰기)")
        self._writer_log("🚀 원스톱 프로세스 시작! 글 작성을 요청합니다...")
        threading.Thread(target=self._generate_post, args=(True,), daemon=True).start()

    # =========================================================================
    # [Tab 3] AI 글쓰기 (Context AI 적용)
    # =========================================================================
    def _setup_writer_tab(self):
        top = ctk.CTkFrame(self.tab_writer, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(top, text="AI 원고 작성기", font=("Malgun Gothic", 16, "bold")).pack(side="left")
        self.writer_status = ctk.CTkLabel(top, text="대기 중", text_color="gray")
        self.writer_status.pack(side="left", padx=10)
        
        self.post_title = ctk.CTkEntry(self.tab_writer)
        self.post_title.pack(fill="x", padx=10, pady=5)
        self.post_content = ctk.CTkTextbox(self.tab_writer, height=400)
        self.post_content.pack(fill="both", expand=True, padx=10, pady=5)

    def _generate_post(self, auto_next=False):
        api_key = self.api_entries["GEMINI_API_KEY"].get().strip()
        if not api_key: self._writer_log("❌ Gemini API 키 없음"); return
        
        context = ""
        if os.path.exists("daily_post_data.txt"):
            with open("daily_post_data.txt", "r", encoding="utf-8") as f: context = f.read()
        else: context = "주제: " + self.interview_topic_entry.get()
        
        # [NEW] 카테고리 스타일 적용
        current_cat = self.cat_combo.get()
        style_guide = CATEGORY_PROMPTS.get(current_cat, "블로그 작가처럼")
            
        self._writer_log("⏳ AI 글 작성 중...")
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            prompt = f"""
당신은 {style_guide} 글을 작성합니다.
[기초 데이터]
{context}
[요청사항]
1. 제목은 첫 줄에 'TITLE:'로 시작
2. 본문은 줄글 형식 (마크다운 제목 # 사용 금지)
3. {current_cat} 카테고리에 맞는 전문 용어와 말투 사용
4. 가독성 좋게 문단 나누기
"""
            res = model.generate_content(prompt)
            lines = res.text.split('\n')
            title = "제목 없음"; body = []
            for line in lines:
                if line.startswith("TITLE:"): title = line.replace("TITLE:", "").strip()
                else: body.append(line)
            
            self.after(0, lambda: self._update_entry(self.post_title, title))
            self.after(0, lambda: self.post_content.delete("1.0", "end"))
            self.after(0, lambda: self.post_content.insert("1.0", "\n".join(body).strip()))
            self._writer_log("✅ 작성 완료.")
            
            if auto_next:
                time.sleep(1)
                self.after(0, self._start_selenium_from_chain)
        except Exception as e: self._writer_log(f"오류: {e}")

    def _writer_log(self, msg): self.writer_status.configure(text=msg)
    def _update_entry(self, entry, text): entry.delete(0, "end"); entry.insert(0, text)

    def _start_selenium_from_chain(self):
        title = self.post_title.get()
        content = self.post_content.get("1.0", "end")
        self.tabview.set("4단계: 발행 (자동화)")
        self._update_entry(self.pub_title, title)
        self.pub_content.delete("1.0", "end")
        self.pub_content.insert("1.0", content)
        self._pub_log("🚀 원스톱 발행 시작")
        self._run_selenium_thread()

    # =========================================================================
    # [Tab 4] 발행 (Selenium)
    # =========================================================================
    def _setup_publisher_tab(self):
        top = ctk.CTkFrame(self.tab_publisher, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(top, text="🚀 네이버 자동 발행 (Selenium)", font=("Malgun Gothic", 16, "bold")).pack(side="left")
        ctk.CTkButton(top, text="🤖 브라우저 열고 작성", command=self._run_selenium_thread, fg_color="#E74C3C").pack(side="right")
        self.pub_status = ctk.CTkLabel(top, text="대기 중", text_color="gray")
        self.pub_status.pack(side="right", padx=10)
        self.pub_title = ctk.CTkEntry(self.tab_publisher); self.pub_title.pack(fill="x", padx=10, pady=5)
        self.pub_content = ctk.CTkTextbox(self.tab_publisher, height=350); self.pub_content.pack(fill="both", expand=True, padx=10, pady=5)

    def _run_selenium_thread(self):
        if not SELENIUM_AVAILABLE: messagebox.showerror("오류", "Selenium 설치 필요"); return
        threading.Thread(target=self._run_naver_automation, daemon=True).start()

    def _run_naver_automation(self):
        nid = self.api_entries["NAVER_LOGIN_ID"].get().strip()
        npw = self.api_entries["NAVER_LOGIN_PW"].get().strip()
        if not nid or not npw: self._pub_log("❌ ID/PW 필요"); return
        
        title = self.pub_title.get(); content = self.pub_content.get("1.0", "end")
        self._pub_log("⏳ 브라우저 실행 중...")
        PASTE_KEY = Keys.COMMAND if sys.platform == "darwin" else Keys.CONTROL
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            driver.implicitly_wait(30)
            
            driver.get("https://nid.naver.com/nidlogin.login")
            elem_id = driver.find_element(By.ID, "id"); pyperclip.copy(nid); elem_id.click(); elem_id.send_keys(PASTE_KEY, 'v'); time.sleep(1)
            elem_pw = driver.find_element(By.ID, "pw"); pyperclip.copy(npw); elem_pw.click(); elem_pw.send_keys(PASTE_KEY, 'v'); time.sleep(1)
            driver.find_element(By.ID, "log.login").click()
            self._pub_log("로그인 대기..."); time.sleep(5)
            
            driver.get("https://blog.naver.com/GoBlogWrite.naver")
            WebDriverWait(driver, 30).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "mainFrame")))
            time.sleep(5)
            try: WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.se-popup-button-cancel'))).click(); time.sleep(1)
            except: pass
            try: WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.se-help-panel-close-button'))).click(); time.sleep(1)
            except: pass
            
            actions = ActionChains(driver)
            title_input = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.se-section-documentTitle')))
            title_input.click()
            for char in title: actions.send_keys(char); actions.pause(0.01)
            actions.perform(); time.sleep(1)
            
            content_input = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.se-section-text')))
            content_input.click()
            for line in content.splitlines():
                for char in line: actions.send_keys(char); actions.pause(0.005)
                actions.send_keys(Keys.ENTER); actions.perform()
            time.sleep(2)
            
            save_btn = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.se-save-button'))); save_btn.click(); time.sleep(1)
            real_save = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CLASS_NAME, "se-popup-button-save"))); real_save.click()
            self._pub_log("✅ 임시 저장 완료!"); messagebox.showinfo("완료", "임시 저장이 완료되었습니다.")
            while True:
                time.sleep(1); 
                if not driver.service.is_connectable(): break
        except Exception as e: self._pub_log(f"오류: {e}")

    def _pub_log(self, msg): self.pub_status.configure(text=msg)

    # --- 공통 로직 (채굴) ---
    def _generate_signature(self, sk, ts, m, uri):
        msg = f"{ts}.{m}.{uri}"; h = hmac.new(sk.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256)
        return base64.b64encode(h.digest()).decode('utf-8')

    def _get_keyword_stats(self, ak, sk, cid, hints):
        uri = "/keywordstool"; ts = str(int(time.time()*1000))
        try:
            sig = self._generate_signature(sk, ts, "GET", uri)
            headers = {"X-Timestamp":ts, "X-API-KEY":ak, "X-Customer":cid, "X-Signature":sig}
            url = f"{NAVER_AD_API_BASE_URL}{uri}"
            res = requests.get(url, headers=headers, params={"hintKeywords":",".join(hints),"showDetail":"1"}, timeout=10)
            if res.status_code == 429: time.sleep(2); return None
            return res.json()
        except: return {}

    def _get_document_count(self, kw, cid, csec):
        try:
            url = f"https://openapi.naver.com/v1/search/blog?query={urllib.parse.quote(kw)}&display=1"
            res = requests.get(url, headers={"X-Naver-Client-Id":cid, "X-Naver-Client-Secret":csec}, timeout=5)
            if res.status_code == 200: return res.json().get("total", 0)
        except: pass
        return 0

    def _start_mining(self):
        conf = {k: self.api_entries[k].get().strip() for k in ["NAVER_SEARCH_CUSTOMER_ID", "NAVER_SEARCH_ACCESS_LICENSE_KEY", "NAVER_SEARCH_SECRET_KEY", "NAVER_BLOG_CLIENT_ID", "NAVER_BLOG_CLIENT_SECRET"]}
        if not all(conf.values()): messagebox.showerror("오류", "네이버 API 정보 필요"); return
        
        raw = [k.strip().replace("🔥","") for k in self.miner_keyword_entry.get().split(',') if k.strip()]
        kws = [k.replace(" ","") for k in raw]
        if not kws: return

        self.stop_event.clear(); self.start_btn.configure(state="disabled"); self.stop_btn.configure(state="normal")
        self.miner_log.delete("1.0", "end"); self.all_keyword_data = []
        threading.Thread(target=self._mining_process, args=(conf, kws, int(self.miner_count.get())), daemon=True).start()

    def _stop_mining(self): self.stop_event.set(); self._log_miner("중지 요청...")

    def _mining_process(self, conf, kws, max_cnt):
        self._log_miner("🚀 균형 채굴 시작 (Fair Mining)...")
        # [NEW] 공평 분배 로직
        limit_per_kw = max(1, max_cnt // len(kws))
        processed = set(); recorded = set()
        
        for curr in kws:
            if self.stop_event.is_set(): break
            curr = curr.replace(" ", "")
            if curr in processed: continue
            
            processed.add(curr)
            self._log_miner(f"🔍 '{curr}' 분석 중 (할당량: {limit_per_kw}개)...")
            time.sleep(1)
            
            stats = self._get_keyword_stats(conf["NAVER_SEARCH_ACCESS_LICENSE_KEY"], conf["NAVER_SEARCH_SECRET_KEY"], conf["NAVER_SEARCH_CUSTOMER_ID"], [curr])
            if stats and "keywordList" in stats:
                local_count = 0
                for item in stats["keywordList"]:
                    if local_count >= limit_per_kw: break
                    if self.stop_event.is_set(): break
                    
                    rel = item["relKeyword"].replace(" ", ""); disp = item["relKeyword"]
                    if rel in recorded: continue
                    
                    doc = self._get_document_count(rel, conf["NAVER_BLOG_CLIENT_ID"], conf["NAVER_BLOG_CLIENT_SECRET"])
                    pc = item["monthlyPcQcCnt"]; mo = item["monthlyMobileQcCnt"]
                    try: total = (int(pc) if str(pc).isdigit() else 0) + (int(mo) if str(mo).isdigit() else 0)
                    except: total = 0
                    if total == 0 and ("<10" in str(pc) or "<10" in str(mo)): total = 5
                    
                    comp = round(doc/total, 2) if total > 0 else 999.0
                    icon = "👑" if comp < 0.5 and total > 1000 else "✨" if comp < 1.0 else "🔥" if comp > 10 else "📄"
                    self._log_miner(f"{icon} {disp} | 검색:{total} 문서:{doc} 경쟁:{comp}")
                    
                    self.all_keyword_data.append([disp, pc, mo, total, doc, comp])
                    recorded.add(rel); local_count += 1
            else: self._log_miner("⚠️ 데이터 없음")
        
        self._finish_mining()

    def _finish_mining(self):
        self.start_btn.configure(state="normal"); self.stop_btn.configure(state="disabled")
        self._log_miner(f"✅ 완료! 총 {len(self.all_keyword_data)}개 수집.")
        if self.all_keyword_data:
            self._save_excel()
            if self.auto_move_to_stage2.get():
                best = min(self.all_keyword_data, key=lambda x: x[5])
                if best[3] > 50:
                    self._log_miner(f"🚀 최적 키워드 '{best[0]}' 발견! 2단계 자동 이동.")
                    self.after(1000, lambda: self._move_to_stage2_auto(best[0]))

    def _move_to_stage2_auto(self, keyword):
        self.tabview.set("2단계: 설계 (인터뷰)")
        self.interview_topic_entry.delete(0, "end")
        self.interview_topic_entry.insert(0, keyword)

    def _save_excel(self):
        try:
            wb = openpyxl.Workbook(); ws = wb.active; ws.append(["키워드", "PC", "Mobile", "Total", "문서수", "경쟁률"])
            for row in self.all_keyword_data: ws.append(row)
            wb.save(f"result_{int(time.time())}.xlsx"); self._log_miner("📂 엑셀 저장 완료")
        except: pass

    def _log_miner(self, msg): self.log_queue.put(f"[Miner] {msg}")
    def _check_log_queue(self):
        try:
            while not self.log_queue.empty(): self.miner_log.insert("end", f"{self.log_queue.get_nowait()}\n"); self.miner_log.see("end")
        except: pass
        self.after(100, self._check_log_queue)
    def _load_config(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, "r") as f:
                    return json.load(f)
            except: pass
        return {}
    def _save_config_btn(self):
        data = {k: v.get().strip() for k, v in self.api_entries.items()}
        with open(self.CONFIG_FILE, "w") as f: json.dump(data, f)
        messagebox.showinfo("저장", "설정 저장 완료")

if __name__ == "__main__":
    app = CommandCenterApp()
    app.mainloop()