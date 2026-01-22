# Skill: Step 0 Keyword Miner & Smart Recommender

## 1. Description
네이버 검색광고 API 및 블로그 검색 API를 사용하여 황금 키워드를 채굴하고, 시즌 및 카테고리 데이터를 기반으로 지능형 키워드를 추천합니다.

## 2. Usage
```bash
python logic.py --mode [mining|recommend] --keywords "키워드1,키워드2" --limit 30 --month 1 --category "맛집"
```

## 3. Arguments
- `--mode`: `mining` (채굴) 또는 `recommend` (추천)
- `--keywords`: 분석할 시드 키워드 (쉼표 구분)
- `--limit`: 최대 발굴 개수
- `--month`: 추천용 월 (1-12)
- `--category`: 추천용 카테고리 기획

## 4. Output
- JSON 형식의 분석 결과 (키워드명, 검색량, 문서수, 경쟁률 등)
