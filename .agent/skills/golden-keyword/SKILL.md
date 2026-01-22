# Skill: Golden Keyword Miner (골든키워드 채굴기 - 0121 Ver)

## Description
이 스킬은 네이버 검색광고 API와 블로그 검색 API를 활용하여 특정 키워드에 대한 월간 검색량, 문서수, 경쟁률을 분석하고 연관 키워드를 확장하여 '황금 키워드'를 찾아주는 도구입니다. 특히 `마케팅 커맨드센터`의 시즌/기념일 기반 트렌드 추천 로직이 통합되어 있어 더욱 전략적인 키워드 발굴이 가능합니다.

## Usage
터미널에서 `argparse` 인자를 사용하여 실행하며, 결과는 JSON으로 출력됩니다.

### 명령어 예시
```bash
python .agent/skills/golden-keyword/keyword_agent_skill.py --keywords "캠핑, 차박" --limit 30
```

### 인자 리스트
- `--keywords`: 분석을 시작할 초기 키워드 (쉼표 구분, 필수)
- `--limit`: 최대 추출할 키워드 개수 (기본값: 100)
- `--access_key`: 네이버 검색광고 Access License Key
- `--secret_key`: 네이버 검색광고 Secret Key
- `--customer_id`: 네이버 검색광고 Customer ID
- `--blog_id`: 네이버 검색 API Client ID
- `--blog_secret`: 네이버 검색 API Client Secret

## Output format
성공 시 JSON 객체를 반환합니다:
```json
{
  "results": [
    {
      "keyword": "캠핑용품",
      "monthly_pc_search_volume": "1500",
      "monthly_mobile_search_volume": "4500",
      "total_monthly_search_volume": 6000,
      "document_count": 12000,
      "competition_rate": 2.0
    }
  ]
}
```

## 🌟 신규 기능: 스마트 트렌드 추천 (GUI 전용)
`마케팅 캡틴` GUI에서는 다음과 같은 지능형 추천이 가능합니다:
- **시즌 기반 추천**: 매월 달라지는 `SEASONAL_DATA`를 분석하여 적시성 있는 키워드 제안
- **기념일 기반 추천**: 공휴일, 절기 등 `CALENDAR_EVENTS`를 활용한 이벤트성 글감 생성
- **트렌드 이슈 검증**: 네이버 데이터랩 API와 연동하여 현재 급상승 중인 키워드 식별 (🔥 표시)

## ⚠️ 주의사항
- **인코딩**: 윈도우 환경에서의 한글 깨짐을 방지하기 위해 UTF-8 출력을 지원합니다.
- **실시간 로그**: 채굴 진행 상황은 `stderr`를 통해 실시간으로 출력되므로, 연동 프로그램에서 이를 읽어 사용자에게 표시할 수 있습니다.
- **API 제한**: 네이버 API 가이드를 준수하며, 단기간에 너무 많은 요청을 보낼 경우 API가 일시적으로 제한될 수 있습니다.
