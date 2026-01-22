import sys
import json
import argparse
import io
import os
from google import genai
from PIL import Image

def run_step5_text(api_key, data, part):
    client = genai.Client(api_key=api_key)
    
    product = data.get("product", "")
    nickname = data.get("nickname", "마케팅 캡틴")
    target_topic = data.get("target_topic", "")
    persona_style = data.get("persona_style", "Friendly")
    theme_topic = data.get("series_parts", {}).get(part, {}).get("topic", target_topic)
    
    part_guide = {
        "1": "1회차: 주인공의 현재 상황과 결핍, 그리고 새로운 기회(씨앗) 발견.",
        "2": "2회차: 기회를 잡으려다 마주친 예상치 못한 장벽과 실패, 절망감 묘사.",
        "3": "3회차: 장벽을 허무는 결정적인 '깨달음(Epiphany)'과 새로운 시각.",
        "4": f"4회차: 완벽한 해결책인 '{product}' 제시 및 상업적 행동(CTA) 촉구."
    }.get(part, "")

    prompt = f"""
    # Role: 마케팅 캡틴 (시리즈 작가)
    # Target: {part}회차 포스팅
    # Theme: {theme_topic}
    # Guide: {part_guide}
    # Tone: {persona_style}
    
    # Task:
    1. Write a high-conversion blog post for this specific part.
    2. Incorporate Naver SEO Home Feed strategy (Emotional, Experience-based).
    3. Include 4 distinct image prompts for AI Artist 'Nano Banana' (Pixar 3D style).
    
    # Format:
    [Title] ...
    [Content] ...
    [Image Prompts]
    - Prompt 1: ...
    - Prompt 2: ...
    - Prompt 3: ...
    - Prompt 4: ...
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[prompt]
        )
        return {"content": response.text}
    except Exception as e:
        return {"content": f"❌ AI 원고 생성 중 오류 발생: {str(e)}"}

def run_recommend_topic(api_key, data, part):
    client = genai.Client(api_key=api_key)
    target_topic = data.get('target_topic', '')
    product = data.get('product', '')
    
    prompt = f"""
    # Context:
    - Target Topic: {target_topic}
    - Product: {product}
    # Task:
    Recommend a catchy blog title/topic for Part {part} of a 4-part series.
    It must be curiosity-driven and related to the context.
    Output ONLY the title in Korean, no quotes.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[prompt]
        )
        return response.text.strip().replace('"', '')
    except Exception as e:
        return f"❌ 주제 추천 오류: {str(e)}"

def generate_image(api_key, prompt, output_path):
    client = genai.Client(api_key=api_key)
    try:
        # 사용자가 언급한 'Nano Banana'는 내부적으로 imagen-3.0-generate-001 모델을 사용함
        # 이전의 generate_content 방식이나 혹은 SDK 가이드에 따른 방식을 유지하되, 
        # 사용자가 '잘 되었다고' 한 이전 상태의 구조로 복원
        response = client.models.generate_image(
            model='imagen-3.0-generate-001',
            prompt=prompt
        )
        if response.generated_images:
            img_part = response.generated_images[0]
            # byte 데이터 추출 방식 재검토 (안정적인 방식)
            img_data = None
            if hasattr(img_part, 'image') and hasattr(img_part.image, 'image_bytes'):
                img_data = img_part.image.image_bytes
            elif hasattr(img_part, 'image_bytes'):
                img_data = img_part.image_bytes
                
            if img_data:
                image = Image.open(io.BytesIO(img_data))
                image.save(output_path)
                return output_path
            else:
                print(f"DEBUG: 이미지 데이터 추출 실패", file=sys.stderr)
    except Exception as e:
        print(f"DEBUG: Nano Banana 이미지 생성 오류: {e}", file=sys.stderr)
    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="text", choices=["text", "image", "recommend_topic"])
    parser.add_argument("--api_key", required=True)
    parser.add_argument("--data_json")
    parser.add_argument("--part")
    parser.add_argument("--prompt")
    parser.add_argument("--out")
    
    args = parser.parse_args()
    
    if args.mode == "text":
        data = json.loads(args.data_json)
        result = run_step5_text(args.api_key, data, args.part)
        print(json.dumps(result, ensure_ascii=False))
    elif args.mode == "recommend_topic":
        data = json.loads(args.data_json)
        result = run_recommend_topic(args.api_key, data, args.part)
        print(result)
    else:
        path = generate_image(args.api_key, args.prompt, args.out)
        print(path if path else "")
