import sys
import argparse
from google import genai

def run_step2(api_key, customer_profile, role, flaw, backstory, persona_style):
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    # Goal: Step 2. Define Attractive Character
    # Context (Target Audience Profile):
    {customer_profile}
    
    # Identity Style (Strictly Follow This):
    - Style: {persona_style}
    
    # Input Data:
    - Role: {role}
    - Flaw: {flaw}
    - Backstory: {backstory}
    
    # Task:
    1. Create a character profile that is the PERFECT GUIDE for the Target Audience above.
    2. Body tone and voice must perfectly match the chosen Style: '{persona_style}'.
    3. Format clearly. Language: Korean.
    
    **Output strictly in Markdown.**
    Structure:
    - **Name/Title**: ...
    - **Style/Vibe**: ...
    - **Role (Identity)**: ...
    - **Flaw (Vulnerability)**: ...
    - **Backstory**: ...
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
    parser.add_argument("--customer_profile", default="")
    parser.add_argument("--role", default="")
    parser.add_argument("--flaw", default="")
    parser.add_argument("--backstory", default="")
    parser.add_argument("--persona_style", default="Friendly")
    
    args = parser.parse_args()
    result = run_step2(args.api_key, args.customer_profile, args.role, args.flaw, args.backstory, args.persona_style)
    print(result)
