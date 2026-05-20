from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from app.core.config import settings
from rag.agents.summary_agent import SummaryAgent


class ExtractedResumeData(BaseModel):
    full_name: str = Field(description="Full name of the candidate")
    email: str | None = Field(None, description="Email address")
    phone: str | None = Field(None, description="Phone number")
    location: str | None = Field(None, description="City and Country")
    professional_title: str | None = Field(
        None, description="Current professional title or role"
    )
    years_experience: int | None = Field(
        None, description="Total years of experience (integer)"
    )
    spoken_languages: list[str] = Field(
        default_factory=list, description="List of spoken languages"
    )

    skills: list[str] = Field(
        default_factory=list, description="List of technical and soft skills"
    )
    tools_technologies: list[str] = Field(
        default_factory=list,
        description="List of specific tools, libraries, frameworks",
    )
    projects: list[str] = Field(
        default_factory=list,
        description="List of key project names or brief descriptions",
    )
    work_history: list[str] = Field(
        default_factory=list, description="List of past job titles and companies"
    )

    education: str | None = Field(
        None, description="Summary of education (Degrees, Universities)"
    )
    certifications: list[str] = Field(
        default_factory=list, description="List of certifications or licenses"
    )


class OnboardingState(TypedDict):
    raw_text: str
    extracted_data: dict
    final_summary: str


llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=settings.app.openai_api_key)
summary_agent = SummaryAgent()


def extractor_agent(state: OnboardingState):
    """Agent 1 (Extractor): Parses raw text into structured JSON."""
    print("--- EXTRACTOR AGENT WORKING ---")
    raw_text = state["raw_text"]

    structured_llm = llm.with_structured_output(ExtractedResumeData)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert HR Data Extractor. Extract structured data from the resume.",
            ),
            ("human", "{text}"),
        ]
    )

    chain = prompt | structured_llm
    result = chain.invoke({"text": raw_text[:10000]})

    return {"extracted_data": result.model_dump()}


def summary_agent_node(state: OnboardingState):
    """Agent 2 (Summarizer): Writes a summary based on clean, structured data."""
    print("--- SUMMARY AGENT WORKING ---")
    data = state["extracted_data"]

    # Use unified SummaryAgent with structured data
    summary_text = summary_agent.generate_summary(data)

    return {"final_summary": summary_text}


workflow = StateGraph(OnboardingState)

workflow.add_node("extractor", extractor_agent)
workflow.add_node("summarizer", summary_agent_node)

workflow.set_entry_point("extractor")
workflow.add_edge("extractor", "summarizer")
workflow.add_edge("summarizer", END)

app_workflow = workflow.compile()
