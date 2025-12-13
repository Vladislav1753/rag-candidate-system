import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class SummaryAgent:
    def __init__(self, model_name="gpt-4.1-mini"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model_name = model_name

    def generate_summary(self, raw_text: str) -> str:
        prompt = f"""
You are an AI assistant for summarizing CVs.
Produce a concise, structured summary (up to 4-5 sentences).

Rules:
- No bullet points.
- No long paragraphs.
- No hallucinations: use only information from the text.
- Focus on skills, experience, industries, technical stack.

Resume:
\"\"\"
{raw_text}
\"\"\"

Write the summary:
"""

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        return response.choices[0].message.content.strip()
