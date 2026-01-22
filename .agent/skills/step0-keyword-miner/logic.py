import sys
import json
import time
import hmac
import hashlib
import base64
import urllib.parse
import requests
import argparse
from collections import deque
from datetime import datetime, timedelta

if sys.platform == 'win32':
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# --- [데이터] 시즌/캘린더 및 카테고리 ---
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
    1: ["신정", "해돋이", "소한", "대한", "연말정산", "신년운세", "겨울방학", "스키장"],
    2: ["발렌타인데이", "졸업식", "입춘", "우수", "정월대보름", "봄코디"],
    3: ["삼일절", "경칩", "춘분", "화이트데이", "입학식", "미세먼지", "꽃가루"],
    4: ["만우절", "식목일", "청명", "곡우", "벚꽃축제", "중간고사", "피크닉"],
    5: ["근로자의 날", "어린이날", "어버이날", "입하", "스승의 날", "성년의 날", "부부의 날", "석가탄신일"],
    6: ["현충일", "망종", "하지", "단오", "환경의 날", "기말고사", "장마준비"],
    7: ["소서", "대서", "제헌절", "초복", "중복", "여름휴가", "물놀이"],
    8: ["입추", "말복", "광복절", "처서", "칠석", "말복보양식", "개학"],
    9: ["백로", "추분", "추석", "한가위", "가을캠핑", "대하축제"],
    10: ["국군의 날", "개천절", "한글날", "한로", "상강", "할로윈", "단풍구경"],
    11: ["입동", "소설", "빼빼로데이", "수능", "농업인의 날", "첫눈", "블랙프라이데이"],
    12: ["대설", "동지", "크리스마스", "성탄절", "연말파티", "제야의종", "다이어리"]
}

CATEGORY_MAPPING = {
    "문학·책": ["베스트셀러", "추천도서", "서평", "독후감", "작가", "필사", "도서관"],
    "영화": ["개봉예정작", "영화리뷰", "영화평점", "명대사", "영화제", "넷플릭스", "OTT"],
    "미술·디자인": ["전시회", "드로잉", "일러스트", "포트폴리오", "디자인트렌드", "굿즈", "미술강의"],
    "공연·전시": ["뮤지컬", "콘서트", "연극", "박람회", "티켓팅", "얼리버드", "관람후기"],
    "음악": ["플레이리스트", "신곡", "인디음악", "악기연주", "실용음악", "음악학원", "작곡"],
    "드라마": ["드라마추천", "드라마리뷰", "명장면", "등장인물", "줄거리", "결말", "웨이브"],
    "스타·연예인": ["아이돌", "배우", "덕질", "팬미팅", "연예뉴스", "직캠", "음악방송"],
    "만화·애니": ["웹툰추천", "애니리뷰", "피규어", "코스프레", "작화", "성우", "만화방"],
    "방송": ["예능리뷰", "방송시간", "다시보기", "방청신청", "아나운서", "TV채널", "편성표"],
    "일상·생각": ["일기", "단상", "브이로그", "오늘의운세", "기록", "소확행", "고민상담"],
    "육아·결혼": ["예비부부", "웨딩홀", "육아용품", "아이랑갈만한곳", "이유식", "태교", "어린이집"],
    "반려동물": ["강아지", "고양이", "반려견산책", "수제간식", "동물병원", "반려동물동반", "애견훈련"],
    "좋은글·이미지": ["명언", "감성글귀", "배경화면", "인사말", "짧고좋은글", "힐링말씀", "위로글"],
    "패션·미용": ["OOTD", "데일리룩", "스킨케어", "메이크업", "향수", "헤어스타일", "피부과"],
    "인테리어·DIY": ["랜선집들이", "셀프인테리어", "방꾸미기", "가구", "조명", "소품", "리모델링"],
    "요리·레시피": ["집밥", "반찬만들기", "에어프라이어레시피", "디저트", "베이킹", "다이어트식단", "술안주"],
    "상품리뷰": ["내돈내산", "구매후기", "언박싱", "가성비템", "추천템", "비교분석", "할인정보"],
    "원예·재배": ["식집사", "반려식물", "플랜테리어", "텃밭가꾸기", "꽃꽂이", "베란다정원", "식물추천"],
    "게임": ["모바일게임", "PC게임", "공략", "게임리뷰", "e스포츠", "사전예약", "게임추천"],
    "스포츠": ["헬스", "요가", "야구", "축구", "골프", "러닝", "필라테스"],
    "사진": ["출사", "카메라", "사진보정", "인생샷", "스튜디오", "포토그래퍼", "필름사진"],
    "자동차": ["신차", "중고차", "시승기", "세차", "차박", "전기차", "운전연수"],
    "취미": ["원데이클래스", "취미생활", "뜨개질", "프라모델", "캘리그라피", "보드게임", "낚시"],
    "국내여행": ["제주도여행", "부산가볼만한곳", "강원도여행", "경주가볼만한곳", "나들이", "캠핑장", "당일치기"],
    "세계여행": ["해외여행준비물", "일본여행", "동남아여행", "유럽여행", "여행코스", "환전", "숙소예약"],
    "맛집": ["맛집추천", "데이트맛집", "회식장소", "카페투어", "빵지순례", "점심메뉴", "야식"],
    "IT·컴퓨터": ["스마트폰", "노트북", "윈도우", "엑셀", "코딩", "인공지능", "애플"],
    "사회·정치": ["시사뉴스", "경제뉴스", "이슈", "정책", "복지", "취업정보", "부동산"],
    "IT/테크": ["스마트폰", "갤럭시", "아이폰", "앱추천", "웨어러블", "가전제품", "정보기슈"],
    "육아/교육": ["자녀교육", "학습지", "영어회화", "수행평가", "입시정보", "자격증", "온라인강의"],
    "경제/비즈니스": ["재테크", "주식투자", "부동산", "창업", "마케팅", "자기계발", "직장생활"],
    "자기계발": ["동기부여", "시간관리", "독서", "습관", "미라클모닝", "성공학", "멘탈관리"]
}

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
    response = requests.get(url, headers=headers, timeout=5)
    response.raise_for_status()
    return response.json().get("total", 0)

def get_naver_autosuggestions(query):
    """네이버 통합검색 자동완성 키워드 가져오기"""
    try:
        url = f"https://ac.search.naver.com/nx/ac?q={urllib.parse.quote(query)}&r_format=json&t_koreng=1&st=100"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if "items" in data and data["items"]:
            return [item[0] for item in data["items"][0]]
    except Exception as e:
        print(f"DEBUG: Auto-suggest error for '{query}': {e}", file=sys.stderr)
    return []

def get_datalab_trend(client_id, client_secret, keywords):
    url = "https://openapi.naver.com/v1/datalab/search"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json"
    }
    body = {
        "startDate": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
        "endDate": datetime.now().strftime("%Y-%m-%d"),
        "timeUnit": "date",
        "keywordGroups": [{"groupName": k, "keywords": [k]} for k in keywords]
    }
    response = requests.post(url, headers=headers, data=json.dumps(body))
    if response.status_code == 200:
        return response.json()
    return None

def run_mining(nav_config, initial_keywords, limit):
    keyword_queue = deque(initial_keywords)
    searched_keywords = set()
    recorded_keywords = set()
    all_results = []
    count = 0
    
    ak, sk, cid = nav_config["naver_access_key"], nav_config["naver_secret_key"], nav_config["naver_customer_id"]
    bl_id, bl_sk = nav_config["naver_client_id"], nav_config["naver_client_secret"]

    while keyword_queue and count < limit:
        current = keyword_queue.popleft()
        if current in searched_keywords: continue
        searched_keywords.add(current)
        
        try:
            # Step 1: Naver Keyword Stats API
            print(f"LOG: '{current}' 연관 키워드 목록 가져오는 중...", file=sys.stderr, flush=True)
            stats = get_naver_keyword_stats(ak, sk, cid, [current])
            
            if stats and "keywordList" in stats:
                items = stats["keywordList"]
                if not items:
                    print(f"LOG: '{current}'에 대한 연관 키워드 결과가 없습니다.", file=sys.stderr, flush=True)
                    continue
                    
                print(f"LOG: '{current}' 관련 후보 {len(items)}개 분석 시작...", file=sys.stderr, flush=True)
                
                for i, item in enumerate(items):
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
                    
                    # Step 2: Naver Blog Search API (Document Count)
                    print(f"DEBUG: [{count+1}/{limit}] '{rel}' 분석 중 (검색량: {total})...", file=sys.stderr, flush=True)
                    
                    doc_count = 0
                    try:
                        doc_count = get_naver_document_count(rel, bl_id, bl_sk)
                    except Exception as e:
                        print(f"DEBUG: '{rel}' 문서수 조회 건너뜀 (오류: {e})", file=sys.stderr, flush=True)
                    
                    comp = "N/A"
                    try:
                        calc_total = total if isinstance(total, int) else (5 if total == "<10" else 0)
                        if calc_total > 0: comp = round(doc_count / calc_total, 2)
                    except: pass
                    
                    row = {"keyword": rel, "pc": pc, "mo": mo, "total": total, "docs": doc_count, "comp": comp}
                    all_results.append(row)
                    recorded_keywords.add(rel)
                    count += 1
                    
                    # Send row data to GUI
                    print(f"ROW:{json.dumps(row, ensure_ascii=False)}", file=sys.stderr, flush=True)
                    
                    # Brief pause to be gentle with APIs and allow UI updates
                    time.sleep(0.05)
                    
                    if count < limit and rel not in searched_keywords and rel not in keyword_queue:
                        keyword_queue.append(rel)
            else:
                print(f"LOG: '{current}' API 응답 없음", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"LOG: 분석 중 오류 발생: {e}", file=sys.stderr, flush=True)
            time.sleep(1) # Error cooldown
            
    # Final sorted result for stdout callback (redundant but kept for consistency)
    all_results.sort(key=lambda x: (x["comp"] if isinstance(x["comp"], (int, float)) else 999999))
    return all_results

def run_recommend(nav_config, month, category, gemini_key, context_keywords=None):
    # 1. Anniversary/Seasonal
    calendar_seeds = CALENDAR_EVENTS.get(month, [])
    seasonal_seeds = SEASONAL_DATA.get(month, [])
    category_suffixes = CATEGORY_MAPPING.get(category, [])
    anniversary_kws = list(set(calendar_seeds + seasonal_seeds))
    
    # 2. Naver Auto-Suggest (Trend/Issue)
    # Using User context + Category + Anniversary seeds to find auto-completes
    auto_suggestions = []
    
    # Seeds for auto-complete: Context + Top 3 Anniversary + Category Name
    seed_queries = []
    if context_keywords: seed_queries.extend(context_keywords)
    seed_queries.extend(anniversary_kws[:3])
    seed_queries.append(category)
    
    print(f"LOG: 자동완성 시드 키워드 분석 중: {seed_queries}", file=sys.stderr, flush=True)
    for q in seed_queries[:5]: # Limit to avoid too many requests
        found = get_naver_autosuggestions(q)
        if found: auto_suggestions.extend(found)
        time.sleep(0.1)
    
    # 3. Gemini Derived Keywords
    gemini_kws = []
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-pro')
            
            prompt = f"""
            Context: Blog Keyword Planning for '{category}' in Month {month}.
            Seeds: {', '.join(seed_queries[:10])}
            Task: Recommend 15 specific, high-search-volume long-tail keywords related to the seeds and category that Koreans would search for on Naver.
            Format: Comma separated list (e.g. Keyword1, Keyword2, ...)
            Strictly return ONLY the keywords.
            """
            print("LOG: Gemini에게 파생 키워드 추천 요청 중...", file=sys.stderr, flush=True)
            resp = model.generate_content(prompt)
            if resp.text:
                raw_txt = resp.text.replace("\n", "").replace("'", "").replace('"', "")
                gemini_kws = [k.strip() for k in raw_txt.split(",") if k.strip()]
        except Exception as e:
            print(f"DEBUG: Gemini Error: {e}", file=sys.stderr, flush=True)

    # 4. Flatten and Deduplicate ALL
    final_list = []
    
    # Priority Order: Auto-suggest (High Intent) -> Gemini (Creative) -> Anniversary (Base) -> Category Mix
    source_map = {} # To track where it came from (log only)
    
    for k in auto_suggestions: 
        if k not in final_list: 
            final_list.append(k)
            source_map[k] = "Auto-Suggest"
            
    for k in gemini_kws:
        if k not in final_list:
            final_list.append(k)
            source_map[k] = "Gemini"
            
    for k in anniversary_kws:
        if k not in final_list:
            final_list.append(k)
            source_map[k] = "Anniversary"
            
    # Add simple category combos if list is short
    if len(final_list) < 10:
        for base in anniversary_kws[:3]:
            for suff in category_suffixes[:3]:
                combo = f"{base} {suff}"
                if combo not in final_list: final_list.append(combo)

    print(f"LOG: 총 {len(final_list)}개의 통합 키워드를 확보했습니다. 심층 분석을 시작합니다.", file=sys.stderr, flush=True)
    return final_list[:50] # Safety limit

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["mining", "recommend"])
    parser.add_argument("--config", required=True, help="JSON string of Naver API config")
    parser.add_argument("--keywords", help="Comma separated keywords for mining")
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--month", type=int)
    parser.add_argument("--category", help="Category for recommendation")
    
    parser.add_argument("--gemini_key", help="Google Gemini API Key")
    
    args = parser.parse_args()
    nav_config = json.loads(args.config)
    
    if args.mode == "mining":
        initial = [k.strip() for k in args.keywords.split(",") if k.strip()]
        result = run_mining(nav_config, initial, args.limit)
    else:
        context = [k.strip() for k in args.keywords.split(",") if k.strip()] if args.keywords else None
        result = run_recommend(nav_config, args.month, args.category, args.gemini_key, context_keywords=context)
        
    print(json.dumps(result, ensure_ascii=False))
