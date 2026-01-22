import sys
import json
import argparse
from google import genai
from google.genai import types

def run_step1(api_key, product, pain, target_topic):
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    # Goal: Step 1. Define Dream Customer
    # Input Data:
    - Product: {product}
    - Pain: {pain}
    - Analysis Target Topic: {target_topic}
    
    # Task:
    1. Identify the most desperate target audience related to the 'Analysis Target Topic'.
    2. Define their Persona (Age, Job, Situation, Deepest Desire).
    3. Write in Korean, friendly and clear.
    
    **Output strictly in Markdown.**
    Structure:
    - **Target Audience**: ...
    - **Demographics**: ...
    - **Psychographics (Desire/Pain)**: ...
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
    parser.add_argument("--product", default="")
    parser.add_argument("--pain", default="")
    parser.add_argument("--target_topic", default="")
    
    args = parser.parse_args()
    result = run_step1(args.api_key, args.product, args.pain, args.target_topic)
    print(result)
