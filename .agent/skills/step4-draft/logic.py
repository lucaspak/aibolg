import sys
import argparse
from google import genai

def run_step4(api_key, synopsis, character, episode, scene, inner):
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    # Goal: Step 4. Write Content Draft (Story Alchemist)
    # Target Episode: {episode}
    # Deep Details:
    - Scene Sensory: {scene}
    - Inner Voice: {inner}
    # Context:
    - Synopsis: {synopsis}
    - Character: {character}
    # Task:
    Write a high-immersion blog post draft that makes the reader feel like they are there.
    **Output strictly in Markdown.**
    
    Structure:
    - **Scene Setting**: (Sensory details)
    - **Inner Monologue**: (Character's thoughts)
    - **Dialogue**: (If any)
    - **Action**: (What happens)
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
    parser.add_argument("--synopsis", default="")
    parser.add_argument("--character", default="")
    parser.add_argument("--episode", default="")
    parser.add_argument("--scene", default="")
    parser.add_argument("--inner", default="")
    
    args = parser.parse_args()
    result = run_step4(args.api_key, args.synopsis, args.character, args.episode, args.scene, args.inner)
    print(result)
