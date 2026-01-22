import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import ToastNotification
from tkinter import messagebox, scrolledtext, filedialog
import threading
import time
from google import genai
from google.genai import types
from PIL import Image, ImageTk, ImageDraw, ImageFont
import io
from datetime import datetime
import json
import os
import requests
import hmac
import hashlib
import base64
import urllib.parse
from collections import deque
import openpyxl
import re
import queue

# Configure Gemini Client - Initially None, will be set after loading config
client = None
CONFIG_FILE = "config.json"
NAVER_API_BASE_URL = "https://api.naver.com"

class MarketingWizardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("마케팅 캡틴 (Marketing Captain AI) - Premium")
        self.root.geometry("1100x900")
        
        # API Key management
        config = self.load_config()
        self.api_key = config.get("api_key", "") if isinstance(config, dict) else ""
        self.init_genai_client()
        
        self.data = {
            "customer": "",
            "character": "",
            "synopsis": "",
            "draft": "",
            "final_script": "",
            "persona_style": "Friendly",
            "story_strategy": "Standard",
            "naver_search_access_license_key": "",
            "naver_search_secret_key": "",
            "naver_search_customer_id": "",
            "naver_blog_client_id": "",
            "naver_blog_client_secret": ""
        }
        
        # Keyword Mining specific data
        self.stop_event = threading.Event()
        self.current_thread = None
        self.all_keyword_data = []
        self.log_queue = [] # Thread-safe log queue
        
        self.create_widgets()
        
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
            "0단계: 골든 키워드 채굴", 
            "나의 고객들이 검색하는 '팔리는' 키워드를 발굴합니다.",
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
            "Gemini 및 Naver API 키를 설정하고 저장합니다.",
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


    # --- Step 0: Keyword Mining UI ---
    def build_step0_ui(self, parent):
        self.create_question_block(parent, 
            "Q1. 검색할 초기 키워드 (쉼표로 구분)", 
            "예: 여행, 제주도 맛집, 캠핑", 
            "entry_seed_keywords")
        
        container = tb.Frame(parent)
        container.pack(fill=X, pady=(0, 20))
        tb.Label(container, text="Q2. 몇 개의 키워드를 조회하시겠습니까? (최대 10000)", font=("Segoe UI", 12, "bold"), bootstyle="inverse-dark", padding=5).pack(anchor="w")
        self.entry_max_keywords = tb.Entry(container, font=("Segoe UI", 11))
        self.entry_max_keywords.insert(0, "100")
        self.entry_max_keywords.pack(fill=X, pady=(5, 0))

        # Buttons
        btn_frame = tb.Frame(parent)
        btn_frame.pack(fill=X, pady=10)
        
        self.btn_start_mine = tb.Button(btn_frame, text="🚀 검색 시작", command=self.start_mining, bootstyle="primary", padding=10)
        self.btn_start_mine.pack(side=LEFT, expand=True, fill=X, padx=5)
        
        self.btn_stop_mine = tb.Button(btn_frame, text="🛑 중지", command=self.stop_mining, bootstyle="danger-outline", state=DISABLED, padding=10)
        self.btn_stop_mine.pack(side=LEFT, expand=True, fill=X, padx=5)
        
        self.btn_export_excelSource = tb.Button(btn_frame, text="💾 엑셀 저장", command=self.export_keywords_excel, bootstyle="success-outline", state=DISABLED, padding=10)
        self.btn_export_excelSource.pack(side=LEFT, expand=True, fill=X, padx=5)

        # Progress & Status
        self.mine_status_var = tb.StringVar(value="대기 중")
        tb.Label(parent, textvariable=self.mine_status_var, font=("Segoe UI", 10)).pack(anchor="w", pady=(10, 0))
        
        self.mine_progress_var = tb.DoubleVar(value=0)
        self.mine_progress_bar = tb.Floodgauge(parent, variable=self.mine_progress_var, mask="진행률: {}%", bootstyle="info")
        self.mine_progress_bar.pack(fill=X, pady=5)

        # Log Area
        tb.Label(parent, text="▼ 연관 키워드 분석 로그", font=("Segoe UI", 11, "bold"), bootstyle="secondary").pack(anchor="w", pady=(20, 5))
        self.txt_mine_log = scrolledtext.ScrolledText(parent, height=15, font=("Consolas", 10))
        self.txt_mine_log.pack(fill=BOTH, expand=True)
        self.txt_mine_log.configure(state=DISABLED)

        # Log monitoring
        self.root.after(100, self._check_log_queue)

    def _check_log_queue(self):
        if hasattr(self, 'log_queue') and self.log_queue:
            self.txt_mine_log.configure(state=NORMAL)
            while self.log_queue:
                msg = self.log_queue.pop(0)
                self.txt_mine_log.insert(END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
                self.txt_mine_log.see(END)
            self.txt_mine_log.configure(state=DISABLED)
        self.root.after(100, self._check_log_queue)

    def log_mine(self, message):
        self.log_queue.append(message)
        print(f"MINER: {message}")

    def _generate_signature(self, secret_key: str, timestamp: str, method: str, request_uri: str) -> str:
        message = f"{timestamp}.{method}.{request_uri}"
        h = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
        return base64.b64encode(h.digest()).decode('utf-8')

    def _get_keyword_stats(self, access_key, secret_key, customer_id, hint_keywords):
        request_uri = "/keywordstool"
        method = "GET"
        timestamp = str(int(time.time() * 1000))
        try:
            signature = self._generate_signature(secret_key, timestamp, method, request_uri)
            headers = {
                "X-Timestamp": timestamp,
                "X-API-KEY": access_key,
                "X-Customer": customer_id,
                "X-Signature": signature
            }
            params = {"hintKeywords": ",".join(hint_keywords), "showDetail": "1"}
            url = f"{NAVER_API_BASE_URL}{request_uri}"
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log_mine(f"API 요청 오류: {e}")
            return {}

    def _get_document_count(self, keyword, client_id, client_secret):
        encText = urllib.parse.quote(keyword)
        url = f"https://openapi.naver.com/v1/search/blog?query={encText}&display=1"
        headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
        try:
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            return response.json().get("total", 0)
        except:
            return 0

    def start_mining(self):
        config = self.load_config()
        if not config.get("naver_search_access_license_key"):
            messagebox.showwarning("설정 필요", "먼저 '설정' 탭에서 네이버 API 키를 입력해주세요.")
            self.notebook.select(self.tab_settings)
            return

        seeds = [k.strip() for k in self.entry_seed_keywords.get().split(",") if k.strip()]
        if not seeds:
            messagebox.showwarning("입력 필요", "검색할 초기 키워드를 입력해주세요.")
            return

        try:
            max_k = int(self.entry_max_keywords.get())
        except:
            max_k = 100

        self.all_keyword_data = []
        self.stop_event.clear()
        self.btn_start_mine.configure(state=DISABLED)
        self.btn_stop_mine.configure(state=NORMAL)
        self.btn_export_excelSource.configure(state=DISABLED)
        self.mine_status_var.set("분석 중...")
        
        def task():
            self._process_keywords(config, seeds, max_k)
            self.root.after(0, self._finish_mining)

        threading.Thread(target=task, daemon=True).start()

    def stop_mining(self):
        self.stop_event.set()
        self.log_mine("🛑 중지 요청됨...")

    def _process_keywords(self, config, initial_keywords, max_keywords):
        keyword_queue = deque(initial_keywords)
        searched_keywords = set()
        recorded_keywords = set()
        count = 0

        while keyword_queue and count < max_keywords:
            if self.stop_event.is_set(): break
            
            cur = keyword_queue.popleft()
            if cur in searched_keywords: continue
            searched_keywords.add(cur)
            
            self.log_mine(f"'{cur}' 관련어 검색 중...")
            stats = self._get_keyword_stats(
                config["naver_search_access_license_key"],
                config["naver_search_secret_key"],
                config["naver_search_customer_id"],
                [cur]
            )
            
            if stats and "keywordList" in stats:
                for item in stats["keywordList"]:
                    if self.stop_event.is_set() or count >= max_keywords: break
                    
                    rel = item.get("relKeyword", "")
                    if rel in recorded_keywords: continue
                    
                    pc = item.get("monthlyPcQcCnt", 0)
                    mo = item.get("monthlyMobileQcCnt", 0)
                    
                    # Convert <10 to 5 for calculation
                    def to_int(v):
                        if v == "<10": return 5
                        try: return int(v)
                        except: return 0
                    
                    total_vol = to_int(pc) + to_int(mo)
                    docs = self._get_document_count(rel, config["naver_blog_client_id"], config["naver_blog_client_secret"])
                    comp = round(docs / total_vol, 2) if total_vol > 0 else 0
                    
                    row = [rel, pc, mo, total_vol, docs, comp]
                    self.all_keyword_data.append(row)
                    recorded_keywords.add(rel)
                    count += 1
                    
                    self.log_mine(f"✅ {rel} | 총검색: {total_vol}, 문서: {docs}, 경쟁률: {comp}")
                    self.mine_progress_var.set(round((count / max_keywords) * 100, 1))
                    
                    if rel not in searched_keywords and rel not in keyword_queue:
                        keyword_queue.append(rel)

    def _finish_mining(self):
        self.btn_start_mine.configure(state=NORMAL)
        self.btn_stop_mine.configure(state=DISABLED)
        if self.all_keyword_data:
            self.btn_export_excelSource.configure(state=NORMAL)
            self.mine_status_var.set(f"완료 ({len(self.all_keyword_data)}개 발굴)")
        else:
            self.mine_status_var.set("데이터 없음")

    def export_keywords_excel(self):
        if not self.all_keyword_data: return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            title="키워드 결과 저장"
        )
        if filename:
            try:
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.append(["키워드", "PC 검색량", "모바일 검색량", "총 검색량", "문서수", "경쟁률"])
                for row in self.all_keyword_data:
                    ws.append(row)
                wb.save(filename)
                messagebox.showinfo("저장 완료", f"파일이 저장되었습니다: {filename}")
            except Exception as e:
                messagebox.showerror("오류", f"저장 중 오류: {e}")

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
        tb.Label(parent, text="★ 마지막 단계입니다! 캡틴이 직접 출동합니다.", font=("Segoe UI", 12, "bold"), bootstyle="danger").pack(anchor="w", pady=(0, 20))
        
        self.create_question_block(parent,
            "★ 블로그 닉네임 (필수)",
            "이 글을 쓰는 사람의 이름은? (예: 육아대장, 테크요정)",
            "entry_nickname")
            
        self.create_question_block(parent,
            "★ 검색으로 얻은 팩트/뉴스/통계 (있으면 좋음)",
            "예: '2025년 통계청 자료에 따르면...', '요즘 인스타에서 유행하는...'",
            "entry_facts")
            
        self.create_action_button(parent, "🚀 마케팅 캡틴: 최종 완성본 출력",
            lambda: self.run_gemini(self.prompt_step5, self.txt_out5, "final_script"), "dark")
            
        self.create_output_area(parent, "▼ [최종] 블로그 글 & 섹션별 이미지", "txt_out5")

        # Image Grid for Step 5
        tb.Label(parent, text="▼ [Nano Banana] 섹션별 블로그 이미지 (Pixar Style)", font=("Segoe UI", 11, "bold"), bootstyle="secondary").pack(anchor="w", pady=(20, 5))
        
        img_container = tb.Frame(parent)
        img_container.pack(fill=X, pady=10)
        
        # 2x2 Grid for 4 images
        self.lbl_img_step5_intro = tb.Label(img_container, text="[1. Intro]", bootstyle="inverse-light", width=40)
        self.lbl_img_step5_intro.grid(row=0, column=0, padx=5, pady=5)
        
        self.lbl_img_step5_wall = tb.Label(img_container, text="[2. Wall]", bootstyle="inverse-light", width=40)
        self.lbl_img_step5_wall.grid(row=0, column=1, padx=5, pady=5)
        
        self.lbl_img_step5_epiphany = tb.Label(img_container, text="[3. Epiphany]", bootstyle="inverse-light", width=40)
        self.lbl_img_step5_epiphany.grid(row=1, column=0, padx=5, pady=5)
        
        self.lbl_img_step5_offer = tb.Label(img_container, text="[4. Offer]", bootstyle="inverse-light", width=40)
        self.lbl_img_step5_offer.grid(row=1, column=1, padx=5, pady=5)
        
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
        
        # Gemini API Section
        tb.Label(container, text="🔑 Google Gemini API Key", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(anchor="w", pady=(0, 10))
        self.entry_api_key = tb.Entry(container, font=("Segoe UI", 12), show="*")
        self.entry_api_key.pack(fill=X, pady=5)
        
        # Naver Search Ad API Section
        tb.Label(container, text="🕵️ Naver Search Ad API (키워드 조회)", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(anchor="w", pady=(20, 10))
        
        tb.Label(container, text="Access License Key", font=("Segoe UI", 10)).pack(anchor="w")
        self.entry_naver_access = tb.Entry(container, font=("Segoe UI", 11))
        self.entry_naver_access.pack(fill=X, pady=(0, 10))
        
        tb.Label(container, text="Secret Key", font=("Segoe UI", 10)).pack(anchor="w")
        self.entry_naver_secret = tb.Entry(container, font=("Segoe UI", 11), show="*")
        self.entry_naver_secret.pack(fill=X, pady=(0, 10))
        
        tb.Label(container, text="Customer ID", font=("Segoe UI", 10)).pack(anchor="w")
        self.entry_naver_customer = tb.Entry(container, font=("Segoe UI", 11))
        self.entry_naver_customer.pack(fill=X, pady=(0, 10))
        
        # Naver Blog Search API Section
        tb.Label(container, text="📝 Naver Blog Search API (문서 수 조회)", font=("Segoe UI", 14, "bold"), bootstyle="primary").pack(anchor="w", pady=(20, 10))
        
        tb.Label(container, text="Client ID", font=("Segoe UI", 10)).pack(anchor="w")
        self.entry_naver_blog_id = tb.Entry(container, font=("Segoe UI", 11))
        self.entry_naver_blog_id.pack(fill=X, pady=(0, 10))
        
        tb.Label(container, text="Client Secret", font=("Segoe UI", 10)).pack(anchor="w")
        self.entry_naver_blog_secret = tb.Entry(container, font=("Segoe UI", 11), show="*")
        self.entry_naver_blog_secret.pack(fill=X, pady=(0, 10))

        # Save Button
        tb.Button(container, text="💾 모든 API Key 저장하기", command=self.save_all_api_keys, bootstyle="success", padding=10).pack(pady=20)
        
        # Load values
        config = self.load_config()
        if config:
            self.entry_api_key.insert(0, config.get("api_key", ""))
            self.entry_naver_access.insert(0, config.get("naver_search_access_license_key", ""))
            self.entry_naver_secret.insert(0, config.get("naver_search_secret_key", ""))
            self.entry_naver_customer.insert(0, config.get("naver_search_customer_id", ""))
            self.entry_naver_blog_id.insert(0, config.get("naver_blog_client_id", ""))
            self.entry_naver_blog_secret.insert(0, config.get("naver_blog_client_secret", ""))

        tb.Label(container, text="* API 키는 로컬 파일(config.json)에 안전하게 저장됩니다.", font=("Segoe UI", 9), bootstyle="secondary").pack(anchor="w", pady=(20, 0))
        
    def save_all_api_keys(self):
        new_config = {
            "api_key": self.entry_api_key.get().strip(),
            "naver_search_access_license_key": self.entry_naver_access.get().strip(),
            "naver_search_secret_key": self.entry_naver_secret.get().strip(),
            "naver_search_customer_id": self.entry_naver_customer.get().strip(),
            "naver_blog_client_id": self.entry_naver_blog_id.get().strip(),
            "naver_blog_client_secret": self.entry_naver_blog_secret.get().strip()
        }
        
        self.api_key = new_config["api_key"]
        self.save_config(new_config)
        self.init_genai_client()
        messagebox.showinfo("설정 완료", "API 키가 성공적으로 저장되었습니다.")

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                 pass
        return {}

    def save_config(self, config_dict):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=4)

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

                if key:
                    self.data[key] = result
                    
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: widget.insert(END, f"\n\n[Error]: {error_msg}"))
        
        threading.Thread(target=task, daemon=True).start()

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
                            
                            self.root.after(0, lambda: self.update_image_label(label_widget, photo))
                            image_found = True
                            break
                
                if not image_found:
                     self.root.after(0, lambda: label_widget.configure(text="이미지 생성 실패: 결과 없음"))

            except Exception as e:
                error_msg = str(e)
                print(f"Image Gen Error: {error_msg}")
                # Fallback on error
                self.root.after(0, lambda: self.create_placeholder_image(label_widget, f"Error:\n{error_msg[:50]}..."))

        threading.Thread(target=task, daemon=True).start()

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
        synopsis = self.txt_out3.get("1.0", END).strip() 
        draft = self.txt_out4.get("1.0", END).strip()
        
        # UI 입력값
        product = self.entry_product.get() 
        nickname = self.get_input(self.entry_nickname, "신뢰감 있는 마케팅 전문가 닉네임")
        facts = self.get_input(self.entry_facts, "관련된 최신 통계나 트렌드를 하나 가상으로 인용해주세요")
        
        # Persona & Strategy from data store
        persona_style = self.data.get("persona_style", "Friendly")
        story_strategy = self.data.get("story_strategy", "Standard")
        
        return f"""
        # Role: Marketing Captain (Storytelling & Visual Director)
        # Goal: Write a High-Retention Blog Post with Image Prompts for Each Section
        
        # Identity (Persona):
        - Name: {nickname}
        - Selected Style: {persona_style} (STRICTLY match this tone)
        - Voice: Use the tone of '{persona_style}'.
        - Rule: NEVER mention you are an AI. Act strictly as the human expert '{nickname}'.
        
        # Context Data (Integrate these naturally):
        - Story Strategy: {story_strategy}
        - Product/Topic: {product}
        - Target Customer: {customer} (Address them as 'you')
        - Key Fact/Trend: {facts} (Use this to validate the problem in 'The Wall' section)
        - Story Draft: {draft} (Expand this into the full narrative)
        - Synopsis: {synopsis}
        
        # [Writing Guidelines]
        1. **Mobile First**: Short paragraphs (2-3 sentences max). Use line breaks frequently.
        2. **Visual Thinking**: For every section, provide a specific image prompt for 'Nano Banana' (AI Artist).
        3. **SEO**: Mention '{product}' naturally 5+ times.
        
        ---
        # [Output Format - Strictly Follow This Structure]
        
        ## 1. Title Options
        - Provide 3 viral titles. (Mix curiosity & benefit).
        
        ## 2. Blog Post Body
        
        **[TL;DR Summary]**
        - Start with "요약:" followed by 2 sentences summarizing the problem and solution.
        
        **(Line Break)**
        
        **[Intro: The Hook]**
        - Start with a strong immersive scene or question from the draft.
        - Empathize with the customer's pain immediately.
        - **[Image Prompt for Nano Banana]**: Describe a high-quality 3D Pixar-style image depicting the tension or hook scene. (English description)
        
        **[Body 1: The Wall (Problem Deep Dive)]**
        - Describe the failure of the 'Old Way'. Why didn't it work?
        - Use '{facts}' here to show this is a common problem.
        - **[Image Prompt for Nano Banana]**: Describe a 3D Pixar-style image showing the frustration or the specific problem situation. (English description)
        
        **[Body 2: The Epiphany (The Solution)]**
        - The turning point. How did you discover the solution?
        - Focus on the 'Aha!' moment and the new perspective.
        - **[Image Prompt for Nano Banana]**: Describe a 3D Pixar-style image showing the moment of discovery, the 'magic tool', or the solution in action. (English description)
        
        **[Body 3: The Offer (Benefit & Result)]**
        - How '{product}' solves the problem specifically.
        - Focus on the user's benefit and the happy result.
        - **[Image Prompt for Nano Banana]**: Describe a 3D Pixar-style image showing the happy result, success, or the character enjoying the benefit. (English description)
        
        **[Conclusion & CTA]**
        - Summarize the main value.
        - **Strong Call To Action**: Tell them exactly what to do next (e.g., "Click the link", "Add neighbor").
        
        ## 3. Recommended Hashtags (10 Tags)
        - Extract essential morphemes/keywords from:
          1. Main Topic ({product})
          2. Subheadings used above
          3. Key content words
        - Format: #Keyword1 #Keyword2 ... (Total 10)
        
        ---
        **Language:** Korean for the blog post. **English** for the Image Prompts.
        """


if __name__ == "__main__":
    # Theme: Cosmo (Modern Blue/White)
    root = tb.Window(themename="cosmo") 
    app = MarketingWizardApp(root)
    root.mainloop()
