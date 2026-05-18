"""
Query Expansion Agent for improving search queries.
Transforms simple queries into detailed, comprehensive search terms.
"""

import os

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

load_dotenv()


class QueryExpansionAgent:
    """
    Agent for expanding and improving search queries.
    Transforms simple queries like 'python lead' into detailed search terms
    like 'Senior Python Developer, Team Lead, Django, Flask, Architecture'.
    """

    def __init__(self, model_name="gpt-4o-mini"):
        self.llm = ChatOpenAI(
            model=model_name, temperature=0.0, api_key=os.getenv("OPENAI_API_KEY")
        )

    def expand_query(self, original_query: str) -> str:
        """
        Expand a simple search query into a more detailed and comprehensive version.

        Args:
            original_query: Original search query from the user

        Returns:
            str: Expanded and improved query with relevant technical terms
        """

        if not original_query or len(original_query.strip()) < 2:
            return original_query

        prompt = ChatPromptTemplate.from_template(
            """
You are an expert HR and recruitment search assistant. Your task is to expand and improve search queries for finding candidates.

Original Query: {query}

Your task:
1. Identify the core role, seniority level, and technologies mentioned
2. Add relevant synonyms, related technologies, and common requirements
3. Include typical seniority markers (Junior, Mid-level, Senior, Lead, etc.) if applicable
4. Add common related skills and technologies for this role
5. Keep the expansion concise (max 15-20 words)

Rules:
- DO NOT use bullet points or lists
- DO NOT add explanations or commentary
- Output ONLY the expanded query as a single line of comma-separated terms
- Include both broad terms (e.g., "Software Engineer") and specific ones (e.g., "FastAPI")
- Prioritize the most relevant and commonly co-occurring skills

Examples:
Input: "python lead"
Output: Senior Python Developer, Team Lead, Django, Flask, FastAPI, System Architecture, Microservices

Input: "frontend react"
Output: Frontend Developer, React, JavaScript, TypeScript, Next.js, Redux, HTML/CSS

Input: "data scientist"
Output: Data Scientist, Machine Learning, Python, R, TensorFlow, PyTorch, Statistics, Data Analysis

Input: "devops aws"
Output: DevOps Engineer, AWS, Docker, Kubernetes, CI/CD, Terraform, Linux, Infrastructure as Code

Now expand this query:
Input: "{query}"
Output:
            """
        )

        # chain = prompt | self.llm
        # response = chain.invoke({"query": original_query.strip()})

        messages = prompt.format_messages(query=original_query.strip())
        response = self.llm.invoke(messages)
        expanded = response.content.strip()

        # Remove any potential prefixes like "Output:" if the model adds them
        if ":" in expanded and len(expanded.split(":")[0]) < 15:
            expanded = expanded.split(":", 1)[1].strip()

        return expanded
