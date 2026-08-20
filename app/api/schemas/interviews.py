from pydantic import BaseModel, Field


class StartInterviewRequest(BaseModel):
    domain: str
    topic: str
    difficulty: int = Field(default=1, ge=1, le=5)


class SubmitAnswerRequest(BaseModel):
    answer: str = Field(min_length=1)


class CurrentQuestionResponse(BaseModel):
    id: str
    topic: str
    difficulty: int
    prompt: str


class InterviewResponse(BaseModel):
    interview_id: str
    domain: str
    topic: str
    difficulty: int
    finished: bool
    questions_answered: int
    current_question: CurrentQuestionResponse | None = None


class ReportResponse(BaseModel):
    interview_id: str
    overall_summary: str
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    total_questions: int
