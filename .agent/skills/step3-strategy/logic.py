import sys
import argparse
from google import genai

def run_step3(api_key, customer, character, secret, wall, epiphany, cta, strategy):
    client = genai.Client(api_key=api_key)
    
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

    prompt = f"""
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
    - [Naver Home Feed Title] (Keyword + Clickable Copy)
    - [Core Content] (Experience-focused summary)
    - [Open Loop] (Ending sentence to hook into next episode)
    
    Language: Korean.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[prompt]
        )
        return response.text
    except Exception as e:
        return f"❌ AI 호출 중 오류 발생: {str(e)}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api_key", required=True)
    parser.add_argument("--customer", default="")
    parser.add_argument("--character", default="")
    parser.add_argument("--secret", default="")
    parser.add_argument("--wall", default="")
    parser.add_argument("--epiphany", default="")
    parser.add_argument("--cta", default="")
    parser.add_argument("--strategy", default="Standard")
    
    args = parser.parse_args()
    result = run_step3(args.api_key, args.customer, args.character, args.secret, args.wall, args.epiphany, args.cta, args.strategy)
    print(result)
