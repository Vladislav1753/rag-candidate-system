import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()


class SummaryAgent:
    """
    Unified Summary Agent for both structured data (dict) and raw text.
    - Supports dict input (from onboarding pipeline)
    - Supports raw text (from PDF parsing)
    """

    def __init__(self, model_name="gpt-4o-mini"):
        self.llm = ChatOpenAI(
            model=model_name, temperature=0.2, api_key=os.getenv("OPENAI_API_KEY")
        )

    def generate_summary(self, input_data: str | dict) -> str:
        """
        Generate a professional executive summary.

        Args:
            input_data: Either raw text (str) or structured data (dict with candidate info)

        Returns:
            str: Professional 3-4 sentence summary
        """

        if isinstance(input_data, dict):
            return self._summarize_structured(input_data)

        return self._summarize_raw_text(input_data)

    def _summarize_structured(self, data: dict) -> str:
        """Summarize from structured candidate data dict."""

        prompt = ChatPromptTemplate.from_template(
            """
You are an HR Evaluation Expert. Write a professional executive summary (up to 5 sentences)
for this candidate based on their extracted data.

Candidate Data:
Name: {full_name}
Title: {professional_title}
Experience: {years_experience} years
Skills: {skills}
Location: {location}
Languages: {spoken_languages}
Projects: {projects}
Work History: {work_history}
Education: {education}
Certifications: {certifications}
Spoken Languages: {spoken_languages}
Rules:
- Start directly with the candidate's name
- Highlight key strengths
- Focus on technical skills and experience
- Keep it concise and professional
- No bullet points or markdown

Write the summary:
            """
        )

        chain = prompt | self.llm
        response = chain.invoke(data)
        return response.content.strip()

    def _summarize_raw_text(self, raw_text: str) -> str:
        prompt = ChatPromptTemplate.from_template(
            """
            You are an AI assistant for summarizing CVs.
            Produce a concise, structured summary (up to 5 sentences) from the following resume text.

            Resume:
            {text}

            Rules:
            - No bullet points.
            - No long paragraphs.
            - No hallucinations: use only information from the text.
            - Focus on skills, experience, industries, technical stack.
            - Start with the candidate's name if mentioned.
            """
        )
        chain = prompt | self.llm
        response = chain.invoke({"text": raw_text})
        return response.content.strip()
