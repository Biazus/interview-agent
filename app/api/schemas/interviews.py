from pydantic import BaseModel, Field


class StartInterviewRequest(BaseModel):
    domain: str
    topic: str
    difficulty: int = Field(default=1, ge=1, le=5)


class SubmitAnswerRequest(BaseModel):
    answer: str = Field(min_length=1)
