import argparse
import json
import os
import sys
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Rich UI 라이브러리 추가
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

def generate_script(client, model_name, inputs):
    """
    에피파니 브릿지 스크립트를 생성합니다.
    """
    prompt = f"""
# Role: Marketing Captain (Storytelling & Visual Director)
# Goal: Write a High-Retention Blog Post with Image Prompts for Each Section

# Identity (Persona):
- Name: {inputs['nickname']}
- Selected Style: {inputs.get('persona_style', 'Friendly')} (STRICTLY match this tone)
- Voice: Use the tone of '{inputs.get('persona_style', 'Friendly')}'.
- Rule: NEVER mention you are an AI. Act strictly as the human expert '{inputs['nickname']}'.

# Context Data (Integrate these naturally):
- Product/Topic: {inputs['product']}
- Target Customer: {inputs['customer']} (Address them as 'you')
- Key Fact/Trend: {inputs.get('facts', '가상의 최신 통계')}
- Story Draft: {inputs.get('draft', '풍무한 서사')}
- Synopsis: {inputs.get('synopsis', '전체 시놉시스')}

# [Writing Guidelines]
1. **Mobile First**: Short paragraphs (2-3 sentences max). Use line breaks frequently.
2. **Visual Thinking**: For every section, provide a specific image prompt for 'Nano Banana' (AI Artist).
3. **SEO**: Mention '{inputs['product']}' naturally 5+ times.

---
# [Output Format - Strictly Follow This Structure]

## 1. Title Options
- Provide 3 viral titles. (Mix curiosity & benefit).

## 2. Blog Post Body

**[TL;DR Summary]**
- Start with "요약:" followed by 2 sentences summarizing the problem and solution.

**(Line Break)**

**[Intro: The Hook]**
- Start with a strong immersive scene or question.
- Empathize with the customer's pain immediately.
- **[Image Prompt for Nano Banana]**: Describe a high-quality 3D Pixar-style image depicting the tension or hook scene. (English description)

**[Body 1: The Wall (Problem Deep Dive)]**
- Describe the failure of the 'Old Way'. Why didn't it work?
- Use '{inputs.get('facts', '')}' here to show this is a common problem.
- **[Image Prompt for Nano Banana]**: Describe a 3D Pixar-style image showing the frustration or the specific problem situation. (English description)

**[Body 2: The Epiphany (The Solution)]**
- The turning point. How did you discover the solution?
- Focus on the 'Aha!' moment and the new perspective.
- **[Image Prompt for Nano Banana]**: Describe a 3D Pixar-style image showing the moment of discovery, the 'magic tool', or the solution in action. (English description)

**[Body 3: The Offer (Benefit & Result)]**
- How '{inputs['product']}' solves the problem specifically.
- Focus on the user's benefit and the happy result.
- **[Image Prompt for Nano Banana]**: Describe a 3D Pixar-style image showing the happy result, success, or the character enjoying the benefit. (English description)

**[Conclusion & CTA]**
- Summarize the main value.
- **Strong Call To Action**: Tell them exactly what to do next.

## 3. Recommended Hashtags (10 Tags)
- Format: #Keyword1 #Keyword2 ... (Total 10)

---
**Language:** Korean for the blog post. **English** for the Image Prompts.
"""
    
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
        )
    )
    return response.text

def generate_images(client, text, output_dir):
    """
    텍스트에서 이미지 프롬프트를 추출하여 이미지를 생성합니다.
    """
    prompts = re.findall(r'\[Image Prompt for Nano Banana\]:\s*(.*?)(?:\n|$)', text)
    image_paths = []
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        for i, prompt in enumerate(prompts):
            progress.add_task(description=f"이미지 {i+1}/{len(prompts)} 생성 중...", total=None)
            try:
                filename = f"image_{i+1}.png"
                path = os.path.join(output_dir, filename)
                
                response = client.models.generate_images(
                    model='imagen-3.0-generate-001',
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                    )
                )
                
                for result in response.generated_images:
                    result.image.save(path)
                    image_paths.append(path)
            except Exception as e:
                console.print(f"[red]이미지 {i+1} 생성 실패: {e}[/red]")
            
    return image_paths

def interactive_interview():
    """
    사용자와 인터랙티브하게 대화하며 입력을 받습니다.
    """
    console.print(Panel.fit(
        "[bold cyan]🚀 에피파니 브릿지 스튜디오 인터뷰[/bold cyan]\n"
        "마케팅 캡틴이 당신의 스토리를 블로그 포스팅으로 만들어 드립니다.",
        border_style="cyan"
    ))

    product = Prompt.ask("[bold yellow]🏷️ 홍보할 제품이나 주제는 무엇인가요?[/bold yellow]")
    customer = Prompt.ask("[bold yellow]👥 타겟 고객은 누구인가요?[/bold yellow] (예: 30대 직장인)")
    nickname = Prompt.ask("[bold yellow]✍️ 당신의 닉네임은 무엇인가요?[/bold yellow]", default="마케팅 캡틴")
    
    facts = Prompt.ask("[cyan]📊 관련 통계나 강조하고 싶은 팩트가 있나요?[/cyan] (엔터로 건너뛰기)", default="")
    synopsis = Prompt.ask("[cyan]📖 대략적인 스토리 흐름(시놉시스)이 있나요?[/cyan] (엔터로 건너뛰기)", default="")
    draft = Prompt.ask("[cyan]📝 참고할만한 초안이 있나요?[/cyan] (엔터로 건너뛰기)", default="")
    
    persona_style = Prompt.ask(
        "[green]🎭 어떤 톤앤매너로 작성할까요?[/green]",
        choices=["Friendly", "Expert", "Energetic", "Luxury", "Witty"],
        default="Friendly"
    )
    
    gen_image = Confirm.ask("[bold magenta]🖼️ AI 이미지도 함께 생성할까요?[/bold magenta]", default=False)
    
    return {
        "product": product,
        "customer": customer,
        "nickname": nickname,
        "facts": facts,
        "synopsis": synopsis,
        "draft": draft,
        "persona_style": persona_style,
        "image": gen_image
    }

def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Epiphany Bridge Script Generator Skill")
    parser.add_argument("--api_key", help="Gemini API Key")
    parser.add_argument("--product", help="Product or Topic name")
    parser.add_argument("--customer", help="Target customer description")
    parser.add_argument("--nickname", help="Author nickname")
    parser.add_argument("--facts", default="", help="Key facts or trends")
    parser.add_argument("--synopsis", default="", help="Story synopsis")
    parser.add_argument("--draft", default="", help="Story draft")
    parser.add_argument("--persona_style", default="Friendly", help="Persona style")
    parser.add_argument("--image", action="store_true", help="Generate images from prompts")
    parser.add_argument("--output_dir", default="output", help="Output directory for images")
    parser.add_argument("--model", default="gemini-2.0-flash-exp", help="Gemini model name")
    parser.add_argument("--interactive", action="store_true", help="Force interactive mode")

    args = parser.parse_args()

    # 인자가 부족하거나 --interactive 플래그가 있으면 인터뷰 모드 실행
    if args.interactive or not (args.product and args.customer and args.nickname):
        inputs = interactive_interview()
        args.product = inputs["product"]
        args.customer = inputs["customer"]
        args.nickname = inputs["nickname"]
        args.facts = inputs["facts"]
        args.synopsis = inputs["synopsis"]
        args.draft = inputs["draft"]
        args.persona_style = inputs["persona_style"]
        if inputs["image"]:
            args.image = True

    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        console.print("[red]에러: API Key가 필요합니다. .env 파일이나 --api_key 인자를 확인해 주세요.[/red]")
        sys.exit(1)

    try:
        client = genai.Client(api_key=api_key)
        
        with console.status("[bold green]에피파니 브릿지 스크립트 생성 중...[/bold green]"):
            input_data = {
                "product": args.product,
                "customer": args.customer,
                "nickname": args.nickname,
                "facts": args.facts,
                "synopsis": args.synopsis,
                "draft": args.draft,
                "persona_style": args.persona_style
            }
            script_text = generate_script(client, args.model, input_data)
        
        # 터미널에 예쁘게 결과 출력
        console.print("\n" + "="*50)
        console.print(Panel(Markdown(script_text), title="[bold green]✨ 생성된 블로그 포스팅[/bold green]", border_style="green"))
        console.print("="*50 + "\n")
        
        image_paths = []
        if args.image:
            image_paths = generate_images(client, script_text, args.output_dir)
            if image_paths:
                console.print(f"[bold green]✅ 이미지 저장 완료: {len(image_paths)}개의 이미지가 '{args.output_dir}' 폴더에 저장되었습니다.[/bold green]")
                for p in image_paths:
                    console.print(f" - {os.path.abspath(p)}")

        # JSON 출력 (전통적인 CLI/에이전트 호환용)
        # 단, 인터랙티브 모드에서는 가독성을 위해 맨 뒤로 뺍니다.
        final_result = {
            "results": [
                {
                    "script": script_text,
                    "images": [os.path.abspath(p) for p in image_paths]
                }
            ]
        }
        
    except Exception as e:
        console.print(f"[red]치명적 오류 발생: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()
