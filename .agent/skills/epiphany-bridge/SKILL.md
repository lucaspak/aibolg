# Skill: Epiphany Bridge Script Generator (에피파니 브릿지 스크립트 작성기)

## Description
이 스킬은 '에피파니 브릿지' 스토리텔링 기법을 활용하여 고객의 공감을 이끌어내고 전환율을 높이는 블로그 포스팅 스크립트를 생성합니다. 텍스트 본문과 함께 각 섹션에 어울리는 AI 이미지 생성용 프롬프트도 함께 제공하며, 필요에 따라 즉시 이미지를 생성할 수도 있습니다.

## Usage
터미널에서 `argparse` 인자를 사용하여 실행하거나, 인자 없이 실행하여 **인터랙티브 인터뷰 모드**를 사용할 수 있습니다.

### 명령어 예시
```bash
# 인터랙티브 인터뷰 모드 (추천: 마케팅 캡틴이 질문을 던집니다)
python .agent/skills/epiphany-bridge/epiphany_bridge_skill.py

# CLI 인자 방식 (자동화용)
python .agent/skills/epiphany-bridge/epiphany_bridge_skill.py --product "홍삼 정" --customer "기력이 부족한 40대 가장" --nickname "건강매니저"

# 스크립트와 이미지 함께 생성
python .agent/skills/epiphany-bridge/epiphany_bridge_skill.py --product "갤럭시 S24" --customer "얼리어답터 대학생" --nickname "테크마스터" --image --output_dir "./images"
```

### 인자 리스트
- `--product`: 홍보할 제품 또는 주제 (필수)
- `--customer`: 타겟 고객 상세 설명 (필수)
- `--nickname`: 작성자 닉네임 (필수)
- `--api_key`: Gemini API 키 (인자로 전달하거나, 프로젝트 루트의 `.env` 파일 또는 환경 변수 `GEMINI_API_KEY`로 설정 가능)
- `--facts`: 관련 데이터 또는 가상 통계
- `--synopsis`: 전체적인 이야기 흐름 (시놉시스)
- `--draft`: 초기 초안 또는 아이디어
- `--persona_style`: 작성 스타일 (Friendly, Expert, energetic 등)
- `--image`: AI 이미지 생성 여부 (플래그)
- `--output_dir`: 이미지가 저장될 디렉토리 (기본값: output)

## Output Format
결과는 JSON 형식으로 `stdout`에 출력됩니다.

```json
{
  "results": [
    {
      "script": "생성된 블로그 포스팅 전문 (마크다운 형식)",
      "images": [
        "C:\\absolute\\path\\to\\image_1.png",
        "C:\\absolute\\path\\to\\image_2.png"
      ]
    }
  ]
}
```

에러 발생 시:
```json
{
  "error": "에러 메시지",
  "results": []
}
```
