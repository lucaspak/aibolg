import requests
import hmac
import hashlib
import base64
import time
import json
import urllib.parse
import argparse
import sys
import os
from collections import deque
from dotenv import load_dotenv

# 네이버 검색광고 API 정보
NAVER_API_BASE_URL = "https://api.naver.com"

def generate_signature(secret_key: str, timestamp: str, method: str, request_uri: str) -> str:
    """네이버 검색광고 API 요청 시그니처 생성"""
    if not secret_key:
        return ""
    message = f"{timestamp}.{method}.{request_uri}"
    h = hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256)
    return base64.b64encode(h.digest()).decode('utf-8')

def get_keyword_stats(access_key: str, secret_key: str, customer_id: str, hint_keywords: list) -> dict:
    """네이버 검색광고 API로부터 키워드 통계 조회"""
    request_uri = "/keywordstool"
    method = "GET"
    timestamp = str(int(time.time() * 1000))

    try:
        signature = generate_signature(secret_key, timestamp, method, request_uri)
    except Exception as e:
        sys.stderr.write(f"Signature Generation Error: {e}\n")
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
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        sys.stderr.write(f"Naver Search Ad API HTTP Error: {e}\n")
        if 'response' in locals() and response.text:
            sys.stderr.write(f"Response: {response.text}\n")
        return {}
    except Exception as e:
        sys.stderr.write(f"Naver Search Ad API Error: {e}\n")
        return {}

def get_document_count(keyword: str, client_id: str, client_secret: str) -> int:
    """네이버 블로그 검색 API 문서 수 조회"""
    encText = urllib.parse.quote(keyword)
    url = f"https://openapi.naver.com/v1/search/blog?query={encText}&display=1"

    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("total", 0)
    except Exception as e:
        sys.stderr.write(f"Naver Blog Search API Error for '{keyword}': {e}\n")
        return 0

def process_keywords(api_config: dict, initial_keywords: list, max_keywords: int):
    """키워드 분석 루프 (0121 버전 로직)"""
    keyword_queue = deque(initial_keywords)
    searched_keywords = set()
    recorded_keywords = set()
    results = []
    
    keywords_recorded_count = 0
    
    while keyword_queue and keywords_recorded_count < max_keywords:
        current_keyword = keyword_queue.popleft()
        
        if current_keyword in searched_keywords:
            continue

        searched_keywords.add(current_keyword)
        sys.stderr.write(f"Fetching stats for: {current_keyword}\n")

        stats_data = get_keyword_stats(
            api_config["access_key"],
            api_config["secret_key"],
            api_config["customer_id"],
            [current_keyword],
        )

        if stats_data and "keywordList" in stats_data and isinstance(stats_data["keywordList"], list):
            for item in stats_data["keywordList"]:
                if keywords_recorded_count >= max_keywords:
                    break

                rel_keyword = item.get("relKeyword", "N/A")

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

                document_count = get_document_count(
                    rel_keyword,
                    api_config["blog_client_id"],
                    api_config["blog_client_secret"],
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
                except Exception:
                    pass

                results.append({
                    "keyword": rel_keyword,
                    "monthly_pc_search_volume": monthly_pc_qc_cnt,
                    "monthly_mobile_search_volume": monthly_mobile_qc_cnt,
                    "total_monthly_search_volume": total_monthly_qc_cnt,
                    "document_count": document_count,
                    "competition_rate": competition_rate
                })
                
                recorded_keywords.add(rel_keyword)
                keywords_recorded_count += 1

                if (keywords_recorded_count < max_keywords and 
                    rel_keyword not in searched_keywords and 
                    rel_keyword not in keyword_queue):
                    keyword_queue.append(rel_keyword)
    
    return results

def load_config():
    """config.json에서 기본 API 설정을 불러옵니다."""
    config_path = "config.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def main():
    # Force UTF-8 for stdout and stderr to avoid Windows encoding issues
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

    load_dotenv() 
    parser = argparse.ArgumentParser(description="Naver Keyword Mining Skill (0121 Version)")
    parser.add_argument("--keywords", type=str, required=True, help="Initial keywords separated by comma")
    parser.add_argument("--limit", type=int, default=100, help="Max number of keywords to crawl")
    
    parser.add_argument("--access_key", type=str, help="Naver Search Ad Access License Key")
    parser.add_argument("--secret_key", type=str, help="Naver Search Ad Secret Key")
    parser.add_argument("--customer_id", type=str, help="Naver Search Ad Customer ID")
    parser.add_argument("--blog_id", type=str, help="Naver Blog Client ID")
    parser.add_argument("--blog_secret", type=str, help="Naver Blog Client Secret")

    args = parser.parse_args()

    config = load_config()
    
    api_config = {
        "access_key": args.access_key or config.get("NAVER_SEARCH_ACCESS_LICENSE_KEY") or os.getenv("NAVER_SEARCH_ACCESS_LICENSE_KEY"),
        "secret_key": args.secret_key or config.get("NAVER_SEARCH_SECRET_KEY") or os.getenv("NAVER_SEARCH_SECRET_KEY"),
        "customer_id": args.customer_id or config.get("NAVER_SEARCH_CUSTOMER_ID") or os.getenv("NAVER_SEARCH_CUSTOMER_ID"),
        "blog_client_id": args.blog_id or config.get("NAVER_BLOG_CLIENT_ID") or os.getenv("NAVER_BLOG_CLIENT_ID"),
        "blog_client_secret": args.blog_secret or config.get("NAVER_BLOG_CLIENT_SECRET") or os.getenv("NAVER_BLOG_CLIENT_SECRET")
    }

    missing = [k for k, v in api_config.items() if not v]
    if missing:
        sys.stderr.write(f"Missing API configuration: {', '.join(missing)}\n")
        print(json.dumps({"error": f"Missing API configuration: {', '.join(missing)}", "results": []}, ensure_ascii=False))
        sys.exit(1)

    initial_keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    if not initial_keywords:
        print(json.dumps({"error": "No keywords provided", "results": []}, ensure_ascii=False))
        sys.exit(1)

    try:
        results = process_keywords(api_config, initial_keywords, args.limit)
        print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
    except Exception as e:
        sys.stderr.write(f"Processing Error: {e}\n")
        print(json.dumps({"error": str(e), "results": []}, ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()
