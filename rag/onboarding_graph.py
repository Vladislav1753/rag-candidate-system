from typing import TypedDict, List
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Optional
from langgraph.graph import StateGraph, END

load_dotenv()


class ExtractedResumeData(BaseModel):
    full_name: str = Field(description="Full name of the candidate")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    location: Optional[str] = Field(None, description="City and Country")
    professional_title: Optional[str] = Field(
        None, description="Current professional title or role"
    )
    years_experience: Optional[int] = Field(
        None, description="Total years of experience (integer)"
    )
    spoken_languages: List[str] = Field(
        default_factory=list, description="List of spoken languages"
    )

    skills: List[str] = Field(
        default_factory=list, description="List of technical and soft skills"
    )
    tools_technologies: List[str] = Field(
        default_factory=list,
        description="List of specific tools, libraries, frameworks",
    )
    projects: List[str] = Field(
        default_factory=list,
        description="List of key project names or brief descriptions",
    )
    work_history: List[str] = Field(
        default_factory=list, description="List of past job titles and companies"
    )

    education: Optional[str] = Field(
        None, description="Summary of education (Degrees, Universities)"
    )
    certifications: List[str] = Field(
        default_factory=list, description="List of certifications or licenses"
    )


class OnboardingState(TypedDict):
    raw_text: str
    extracted_data: dict
    final_summary: str


llm = ChatOpenAI(model="gpt-4o", temperature=0)


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


def summary_agent(state: OnboardingState):
    """Agent 2 (Summarizer): Writes a summary based on clean, structured data."""
    print("--- SUMMARY AGENT WORKING ---")
    data = state["extracted_data"]

    prompt = ChatPromptTemplate.from_template(
        """
        You are an HR Evaluation Expert. Write a professional executive summary (3-4 sentences)
        for this candidate based on their extracted data.

        Candidate Data:
        Name: {full_name}
        Title: {professional_title}
        Experience: {years_experience} years
        Skills: {skills}

        Start directly with the candidate's name. Highlight key strengths.
        """
    )

    chain = prompt | llm
    response = chain.invoke(data)

    return {"final_summary": response.content}


workflow = StateGraph(OnboardingState)

workflow.add_node("extractor", extractor_agent)
workflow.add_node("summarizer", summary_agent)

workflow.set_entry_point("extractor")
workflow.add_edge("extractor", "summarizer")
workflow.add_edge("summarizer", END)

app_workflow = workflow.compile()
