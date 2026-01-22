import requests
import hmac
import hashlib
import base64
import time
import json
import urllib.parse
import threading
import os
import sys
import queue
from collections import deque

import customtkinter as ctk  # type: ignore
import openpyxl
from tkinter import messagebox


import traceback

import re

# 네이버 검색광고 API 정보 (기본값, 실제 사용은 GUI 입력값)
NAVER_API_BASE_URL = "https://api.naver.com"

class KeywordApp(ctk.CTk):
    CONFIG_FILE = "config.json"
    MAX_KEYWORDS = 10000

    def __init__(self):
        print("초기화 시작...")
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("네이버 키워드 검색 도우미")
        self.geometry("1024x850")
        self.resizable(True, True)

        self.stop_event = threading.Event()
        self.current_thread = None
        self.all_keyword_data = []
        self.last_saved_file = None  # 마지막 저장된 파일 경로
        self.log_queue = queue.Queue()  # 스레드 안전한 로깅을 위한 큐

        self.api_entries = {}
        self.status_var = ctk.StringVar(value="대기 중")
        self.progress_var = ctk.StringVar(value="진행 상황: 0/0")

        if getattr(sys, 'frozen', False):
            # PyInstaller로 패키징된 실행 파일인 경우
            application_path = os.path.dirname(sys.executable)
        else:
            # 일반 Python 스크립트로 실행되는 경우
            application_path = os.path.dirname(os.path.abspath(__file__))

        self.config_path = os.path.join(application_path, self.CONFIG_FILE)

        self._create_widgets()
        self._load_config()
        
        # 로그 큐 모니터링 시작
        self.after(100, self._check_log_queue)

    def _check_log_queue(self):
        """큐에 쌓인 로그 메시지를 메인 스레드에서 처리"""
        try:
            # 한 번에 최대 10개의 로그만 처리하여 GUI 응답성 확보
            for _ in range(10):
                if self.log_queue.empty():
                    break
                
                message = self.log_queue.get_nowait()
                timestamp = time.strftime("%H:%M:%S")
                log_entry = f"[{timestamp}] {message}\n"
                
                self._append_log(log_entry)
                self.status_var.set(message)
                
                # 즉시 화면 갱신
                self.update_idletasks()
        except queue.Empty:
            pass
        except Exception as e:
            print(f"로그 처리 중 오류: {e}")
        finally:
            # 0.1초 후에 다시 확인
            self.after(100, self._check_log_queue)

    def _generate_signature(self, secret_key: str, timestamp: str, method: str, request_uri: str) -> str:
        """네이버 검색광고 API 요청 시그니처 생성"""
        message = f"{timestamp}.{method}.{request_uri}"
        h = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
        return base64.b64encode(h.digest()).decode('utf-8')

    def _get_keyword_stats(self, access_key: str, secret_key: str, customer_id: str, hint_keywords: list) -> dict:
        """네이버 검색광고 API로부터 키워드 통계 조회 (로그 출력 포함)"""
        request_uri = "/keywordstool"
        method = "GET"
        timestamp = str(int(time.time() * 1000))

        try:
            signature = self._generate_signature(secret_key, timestamp, method, request_uri)
        except Exception as e:
            self.log_message(f"서명 생성 실패: {e}")
            return {}

        headers = {
            "X-Timestamp": timestamp,
            "X-API-KEY": access_key,
            "X-Customer": customer_id,
            "X-Signature": signature
        }

        params = {
            "hintKeywords": ",".join(hint_keywords),
            "showDetail": "1"
        }

        url = f"{NAVER_API_BASE_URL}{request_uri}"

        try:
            self.log_message(f"API 요청 중... {url}")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            self.log_message("API 응답 성공")
            return response.json()
        except requests.exceptions.Timeout:
            self.log_message(f"API 요청 시간 초과 ({request_uri})")
            return {}
        except requests.exceptions.HTTPError as err:
            self.log_message(f"API HTTP 오류: {err}")
            # 상세 에러 메시지가 있으면 출력
            try:
                self.log_message(f"응답 내용: {response.text}")
            except:
                pass
            return {}
        except requests.exceptions.RequestException as err:
            self.log_message(f"API 요청 오류: {err}")
            return {}
        except Exception as e:
            self.log_message(f"알 수 없는 오류: {e}")
            return {}

    def _get_document_count(self, keyword: str, client_id: str, client_secret: str) -> int:
        """네이버 블로그 검색 API 문서 수 조회 (로그 출력 포함)"""
        encText = urllib.parse.quote(keyword)
        url = f"https://openapi.naver.com/v1/search/blog?query={encText}&display=1"

        headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret
        }

        try:
            response = requests.get(url, headers=headers, timeout=5) # 타임아웃 단축
            response.raise_for_status()
            data = response.json()
            return data.get("total", 0)
        except requests.exceptions.Timeout:
            self.log_message(f"블로그 API 시간 초과 ({keyword})")
            return 0
        except requests.exceptions.HTTPError as err:
            self.log_message(f"블로그 API HTTP 오류 ({keyword}): {err}")
            return 0
        except requests.exceptions.RequestException as err:
            self.log_message(f"블로그 API 요청 오류 ({keyword}): {err}")
            return 0
        except Exception as e:
            self.log_message(f"문서수 조회 중 알 수 없는 오류 ({keyword}): {e}")
            return 0


    def _create_widgets(self):
        container = ctk.CTkFrame(self, corner_radius=16, fg_color="#1f1f1f")
        container.pack(fill="both", expand=True, padx=24, pady=24)

        title = ctk.CTkLabel(container, text="네이버 키워드 검색 도우미", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=(16, 6))
        subtitle = ctk.CTkLabel(container, text="API 정보를 입력하고 키워드 분석을 시작하세요.", font=ctk.CTkFont(size=14))
        subtitle.pack(pady=(0, 16))

        api_frame = ctk.CTkFrame(container, corner_radius=12, fg_color="#2b2b2b")
        api_frame.pack(fill="x", padx=20, pady=12)

        api_title = ctk.CTkLabel(api_frame, text="API 설정", font=ctk.CTkFont(size=18, weight="bold"))
        api_title.grid(row=0, column=0, columnspan=2, pady=(12, 8), padx=12, sticky="w")

        api_fields = [
            ("NAVER_SEARCH_ACCESS_LICENSE_KEY", "검색광고 Access License Key"),
            ("NAVER_SEARCH_SECRET_KEY", "검색광고 Secret Key"),
            ("NAVER_SEARCH_CUSTOMER_ID", "검색광고 Customer ID"),
            ("NAVER_BLOG_CLIENT_ID", "네이버 검색 API Client ID"),
            ("NAVER_BLOG_CLIENT_SECRET", "네이버 검색 API Client Secret"),
        ]

        for idx, (key, label_text) in enumerate(api_fields, start=1):
            label = ctk.CTkLabel(api_frame, text=label_text, anchor="w")
            label.grid(row=idx, column=0, padx=12, pady=6, sticky="w")
            entry = ctk.CTkEntry(api_frame, show="*" if "SECRET" in key or "SECRET" in label_text.upper() else None, width=360)
            entry.grid(row=idx, column=1, padx=12, pady=6, sticky="ew")
            self.api_entries[key] = entry

        api_frame.grid_columnconfigure(1, weight=1)

        keyword_frame = ctk.CTkFrame(container, corner_radius=12, fg_color="#2b2b2b")
        keyword_frame.pack(fill="x", padx=20, pady=12)

        keyword_label = ctk.CTkLabel(keyword_frame, text="검색할 초기 키워드 (쉼표로 구분)", font=ctk.CTkFont(size=16, weight="bold"))
        keyword_label.pack(anchor="w", padx=12, pady=(12, 4))
        self.keyword_entry = ctk.CTkEntry(keyword_frame, placeholder_text="예: 여행, 제주도 맛집, 캠핑", height=40)
        self.keyword_entry.pack(fill="x", padx=12, pady=(0, 12))

        count_frame = ctk.CTkFrame(keyword_frame, corner_radius=8, fg_color="#232323")
        count_frame.pack(fill="x", padx=12, pady=(0, 12))

        count_label = ctk.CTkLabel(count_frame, text="몇 개의 키워드를 조회하시겠습니까? (최대 10000)", font=ctk.CTkFont(size=14))
        count_label.pack(anchor="w", padx=12, pady=(10, 4))
        self.num_entry = ctk.CTkEntry(count_frame, placeholder_text="예: 100", height=36)
        self.num_entry.pack(fill="x", padx=12, pady=(0, 12))

        control_frame = ctk.CTkFrame(container, corner_radius=12, fg_color="#2b2b2b")
        control_frame.pack(fill="x", padx=20, pady=12)

        self.start_button = ctk.CTkButton(control_frame, text="검색 시작", command=self.start_search, height=44, corner_radius=10)
        self.start_button.pack(side="left", padx=12, pady=16, expand=True, fill="x")

        self.stop_button = ctk.CTkButton(control_frame, text="중지", command=self.stop_search, height=44, corner_radius=10, fg_color="#8b1a1a", hover_color="#a83232", state="disabled")
        self.stop_button.pack(side="left", padx=12, pady=16, expand=True, fill="x")

        self.open_excel_button = ctk.CTkButton(control_frame, text="엑셀 열기", command=self.open_saved_excel, height=44, corner_radius=10, fg_color="#2E8B57", hover_color="#3CB371", state="disabled")
        self.open_excel_button.pack(side="left", padx=12, pady=16, expand=True, fill="x")

        status_frame = ctk.CTkFrame(container, corner_radius=12, fg_color="#2b2b2b")
        status_frame.pack(fill="x", padx=20, pady=12)

        status_label = ctk.CTkLabel(status_frame, textvariable=self.status_var, anchor="w", font=ctk.CTkFont(size=14))
        status_label.pack(fill="x", padx=12, pady=(12, 6))

        self.progress_label = ctk.CTkLabel(status_frame, textvariable=self.progress_var, anchor="w")
        self.progress_label.pack(fill="x", padx=12, pady=(0, 6))

        self.progress_bar = ctk.CTkProgressBar(status_frame, height=14)
        self.progress_bar.pack(fill="x", padx=12, pady=(0, 12))
        self.progress_bar.set(0)

        log_frame = ctk.CTkFrame(container, corner_radius=12, fg_color="#2b2b2b")
        log_frame.pack(fill="both", expand=True, padx=20, pady=(12, 20))

        log_label = ctk.CTkLabel(log_frame, text="진행 로그", font=ctk.CTkFont(size=16, weight="bold"))
        log_label.pack(anchor="w", padx=12, pady=(12, 6))

        self.log_text = ctk.CTkTextbox(log_frame, height=350)
        self.log_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log_text.configure(state="disabled")

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for key, entry in self.api_entries.items():
                    entry.delete(0, "end")
                    if value := data.get(key, ""):
                        entry.insert(0, value)
                self.log_message("이전에 저장된 API 정보를 불러왔습니다.")
            except Exception as e:
                self.log_message(f"설정 파일을 불러오는 중 오류가 발생했습니다: {e}")

    def _save_config(self, config_data: dict):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            self.log_message("API 정보를 저장했습니다.")
        except Exception as e:
            self.log_message(f"설정 파일 저장 중 오류가 발생했습니다: {e}")

    def start_search(self):
        print(">>> [DEBUG] start_search called")
        self._clear_log()
        self.log_message("검색 시작 요청을 받았습니다. 설정을 검증합니다...")

        try:
            if self.current_thread and self.current_thread.is_alive():
                print(">>> [DEBUG] Thread already alive")
                self.log_message("이미 검색이 진행 중입니다.")
                messagebox.showinfo("알림", "이미 검색이 진행 중입니다.")
                return

            print(">>> [DEBUG] Reading API config")
            api_config = {key: entry.get().strip() for key, entry in self.api_entries.items()}
            missing_fields = [key for key, value in api_config.items() if not value]
            if missing_fields:
                print(f">>> [DEBUG] Missing fields: {missing_fields}")
                self.log_message(f"누락된 API 설정이 있습니다.")
                messagebox.showerror("입력 오류", "모든 API 정보를 입력해 주세요.")
                return

            print(">>> [DEBUG] Reading keywords")
            initial_keywords = [kw.strip() for kw in self.keyword_entry.get().split(",") if kw.strip()]
            if not initial_keywords:
                print(">>> [DEBUG] No keywords")
                self.log_message("초기 키워드가 입력되지 않았습니다.")
                messagebox.showerror("입력 오류", "최소 한 개의 초기 키워드를 입력해 주세요.")
                return

            print(">>> [DEBUG] Reading count")
            num_text = self.num_entry.get().strip()
            try:
                num_keywords = int(num_text)
            except ValueError:
                print(">>> [DEBUG] Invalid number format")
                self.log_message("키워드 조회 개수가 올바르지 않습니다.")
                messagebox.showerror("입력 오류", "조회할 키워드 개수에 숫자를 입력해 주세요.")
                return

            if num_keywords <= 0 or num_keywords > self.MAX_KEYWORDS:
                print(f">>> [DEBUG] Invalid number range: {num_keywords}")
                self.log_message(f"키워드 조회 개수 범위 오류: {num_keywords}")
                messagebox.showerror("입력 오류", f"조회 개수는 1 이상 {self.MAX_KEYWORDS} 이하로 입력해 주세요.")
                return

            self._save_config(api_config)
            self.log_message("설정이 저장되었습니다.")

            self.stop_event.clear()
            self.all_keyword_data = []
            self.update_progress(0, num_keywords)
            self.status_var.set("검색을 준비하고 있습니다...")

            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            self.open_excel_button.configure(state="disabled")  # 검색 시작 시 열기 버튼 비활성화

            self.log_message("백그라운드 검색 작업을 시작합니다.")
            print(">>> [DEBUG] Starting thread")
            self.current_thread = threading.Thread(
                target=self._process_keywords,
                args=(api_config, initial_keywords, num_keywords),
                daemon=True,
            )
            self.current_thread.start()
            print(">>> [DEBUG] Thread started")

        except Exception as e:
            print(">>> [DEBUG] Exception in start_search:")
            traceback.print_exc()
            self.log_message(f"검색 시작 중 오류 발생: {e}")
            messagebox.showerror("오류", f"작업 시작 중 오류가 발생했습니다: {e}")
            # 오류 발생 시 버튼 상태 복구
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")

    def stop_search(self):
        if self.current_thread and self.current_thread.is_alive():
            self.stop_event.set()
            self.log_message("중지 버튼을 눌렀습니다. 현재 진행 중인 작업을 마치는 대로 종료합니다.")
            self.status_var.set("중지를 요청했습니다. 잠시만 기다려 주세요.")

    def _process_keywords(self, api_config: dict, initial_keywords: list, max_keywords: int):
        first_keyword = initial_keywords[0] if initial_keywords else "result"
        try:
            self.log_message(f"분석 시작: 초기 키워드 {len(initial_keywords)}개, 최대 조회 수 {max_keywords}개")
            keyword_queue = deque(initial_keywords)
            
            # [중요] 검색한 키워드(API 호출함)와 기록된 키워드(엑셀 저장함)를 분리하여 관리
            searched_keywords = set()  # 이미 API로 조회한 키워드
            recorded_keywords = set()  # 엑셀에 저장된 키워드
            
            keywords_recorded_count = 0
            
            while keyword_queue and keywords_recorded_count < max_keywords:
                if self.stop_event.is_set():
                    self.log_message("사용자 요청으로 검색을 중단합니다.")
                    break

                current_keyword = keyword_queue.popleft()
                
                # 이미 API 조회한 키워드면 스킵 (중복 조회 방지)
                if current_keyword in searched_keywords:
                    continue

                searched_keywords.add(current_keyword)
                self.log_message(f"'{current_keyword}' 키워드의 검색량 정보를 가져옵니다...")

                stats_data = self._get_keyword_stats(
                    api_config["NAVER_SEARCH_ACCESS_LICENSE_KEY"],
                    api_config["NAVER_SEARCH_SECRET_KEY"],
                    api_config["NAVER_SEARCH_CUSTOMER_ID"],
                    [current_keyword],
                )

                # [디버깅] API 응답 데이터 상태 확인
                if stats_data:
                    k_list = stats_data.get("keywordList")
                    if k_list is None:
                        self.log_message("⚠️ 응답에 keywordList 필드가 없습니다. API 권한을 확인하세요.")
                        print(f"[DEBUG] Full response: {stats_data}")
                    elif isinstance(k_list, list):
                        self.log_message(f"✅ 연관 키워드 {len(k_list)}개를 수신했습니다. 상세 분석을 시작합니다...")
                        if not k_list:
                            self.log_message("⚠️ 연관 키워드 목록이 비어있습니다.")
                    else:
                        self.log_message("⚠️ keywordList가 리스트 형식이 아닙니다.")
                else:
                    self.log_message("⚠️ API 응답 데이터가 비어있습니다 (None).")

                if stats_data and "keywordList" in stats_data and isinstance(stats_data["keywordList"], list):
                    for item in stats_data["keywordList"]:
                        if self.stop_event.is_set() or keywords_recorded_count >= max_keywords:
                            break

                        rel_keyword = item.get("relKeyword", "N/A")

                        # 이미 엑셀에 저장한 키워드면 스킵
                        if rel_keyword in recorded_keywords:
                            continue

                        monthly_pc_qc_cnt = item.get("monthlyPcQcCnt", "N/A")
                        monthly_mobile_qc_cnt = item.get("monthlyMobileQcCnt", "N/A")

                        total_monthly_qc_cnt = "N/A"
                        try:
                            pc_qc = int(monthly_pc_qc_cnt) if monthly_pc_qc_cnt not in ["<10", "N/A"] else 0
                            mobile_qc = int(monthly_mobile_qc_cnt) if monthly_mobile_qc_cnt not in ["<10", "N/A"] else 0
                            total_value = pc_qc + mobile_qc
                            if "<10" in [monthly_pc_qc_cnt, monthly_mobile_qc_cnt] and total_value < 10:
                                total_monthly_qc_cnt = "<10"
                            elif total_value == 0 and "<10" in [monthly_pc_qc_cnt, monthly_mobile_qc_cnt]:
                                total_monthly_qc_cnt = "<10"
                            else:
                                total_monthly_qc_cnt = total_value
                        except ValueError:
                            pass

                        document_count = self._get_document_count(
                            rel_keyword,
                            api_config["NAVER_BLOG_CLIENT_ID"],
                            api_config["NAVER_BLOG_CLIENT_SECRET"],
                        )

                        competition_rate = "N/A"
                        try:
                            total_qc_for_calc = 0
                            if isinstance(total_monthly_qc_cnt, int):
                                total_qc_for_calc = total_monthly_qc_cnt
                            elif total_monthly_qc_cnt == "<10":
                                total_qc_for_calc = 5

                            if total_qc_for_calc > 0 and document_count > 0:
                                competition_rate = round(document_count / total_qc_for_calc, 2)
                        except Exception as e:
                            self.log_message(f"경쟁률 계산 중 오류 발생: {e}")

                        self.all_keyword_data.append(
                            [
                                rel_keyword,
                                monthly_pc_qc_cnt,
                                monthly_mobile_qc_cnt,
                                total_monthly_qc_cnt,
                                document_count,
                                competition_rate,
                            ]
                        )
                        recorded_keywords.add(rel_keyword)
                        keywords_recorded_count += 1

                        self.log_message(
                            f"{rel_keyword} | PC: {monthly_pc_qc_cnt}, 모바일: {monthly_mobile_qc_cnt}, 문서수: {document_count}, 경쟁률: {competition_rate}"
                        )

                        count_snapshot = keywords_recorded_count
                        self.after(0, lambda c=count_snapshot: self.update_progress(c, max_keywords))

                        # 큐에 추가: 아직 조회 안 했고, 큐에도 없고, 기록 상한 안 찼으면 추가
                        # (주의: searched_keywords에 있으면 이미 조회했으므로 큐에 넣지 않음)
                        if (keywords_recorded_count < max_keywords and 
                            rel_keyword not in searched_keywords and 
                            rel_keyword not in keyword_queue):
                            keyword_queue.append(rel_keyword)
                            
                elif stats_data:
                    self.log_message("API 응답 형식이 예상과 다릅니다.")
                else:
                    self.log_message(f"'{current_keyword}' 키워드 검색량 정보를 가져오는데 실패했습니다.")
            
            self.log_message("모든 검색 작업이 완료되었습니다.")
            
        except Exception as e:
            self.log_message(f"검색 중 치명적 오류가 발생했습니다: {e}")
            traceback.print_exc()
        finally:
            self.after(0, lambda: self._finish_processing(first_keyword))

    def _finish_processing(self, first_keyword: str):
        stopped = self.stop_event.is_set()
        self.stop_event.clear()

        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.current_thread = None

        if self.all_keyword_data:
            self.status_var.set("결과를 저장하고 있습니다...")
            self._save_to_excel(first_keyword)
            if stopped:
                self.status_var.set("검색이 중지되었으며 수집된 데이터까지 저장했습니다.")
            else:
                self.status_var.set("검색을 완료하고 결과를 저장했습니다.")
        else:
            if stopped:
                self.status_var.set("검색이 중지되었지만 저장할 데이터가 없습니다.")
            else:
                self.status_var.set("수집된 데이터가 없어 파일을 저장하지 않았습니다.")

        self.progress_var.set(f"진행 상황: {len(self.all_keyword_data)}/{len(self.all_keyword_data)}")
        self.progress_bar.set(1 if self.all_keyword_data else 0)

    def _save_to_excel(self, first_keyword: str):
        headers = ["키워드", "월간 PC 검색량", "월간 모바일 검색량", "총 월간 검색량", "문서수", "경쟁률"]
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "키워드 검색량"
        sheet.append(headers)

        for row in self.all_keyword_data:
            sheet.append(row)

        # 파일명에 사용할 수 없는 문자 제거
        safe_keyword = re.sub(r'[\\/*?:"<>|]', "", first_keyword)
        excel_file_name = f"{safe_keyword}.xlsx"
        
        self.log_message(f"엑셀 파일 저장을 시도합니다: {excel_file_name}")
        
        try:
            workbook.save(excel_file_name)
            self.log_message(f"결과가 '{excel_file_name}' 파일로 성공적으로 저장되었습니다.")
            
            # 절대 경로로 저장 및 버튼 활성화
            self.last_saved_file = os.path.abspath(excel_file_name)
            self.open_excel_button.configure(state="normal")
            
        except PermissionError:
            messagebox.showerror("파일 저장 오류", f"'{excel_file_name}' 파일에 접근할 수 없습니다. 파일이 열려 있는지 확인해주세요.")
            self.log_message(f"파일 저장 오류: '{excel_file_name}' 파일에 접근할 수 없습니다.")
        except Exception as e:
            messagebox.showerror("파일 저장 오류", f"엑셀 파일 저장 중 오류가 발생했습니다: {e}")
            self.log_message(f"엑셀 파일 저장 중 오류가 발생했습니다: {e}")

    def open_saved_excel(self):
        if self.last_saved_file and os.path.exists(self.last_saved_file):
            try:
                os.startfile(self.last_saved_file)
                self.log_message(f"파일을 엽니다: {self.last_saved_file}")
            except Exception as e:
                messagebox.showerror("오류", f"파일을 여는 중 오류가 발생했습니다: {e}")
                self.log_message(f"파일 열기 오류: {e}")
        else:
             messagebox.showwarning("알림", "열 수 있는 파일이 없습니다.")

    def update_progress(self, current: int, total: int):
        total = max(total, 1)
        progress = min(current / total, 1.0)
        self.progress_bar.set(progress)
        self.progress_var.set(f"진행 상황: {current}/{total}")

    def log_message(self, message: str):
        print(f"[LOG] {message}")  # 콘솔 디버깅용
        # 큐에 메시지만 넣고, 실제 UI 업데이트는 _check_log_queue에서 처리
        self.log_queue.put(message)

    def _append_log(self, text: str):
        try:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", text)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        except Exception as e:
            print(f"로그 텍스트박스 업데이트 오류: {e}")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")


if __name__ == "__main__":
    app = KeywordApp()
    app.mainloop()
