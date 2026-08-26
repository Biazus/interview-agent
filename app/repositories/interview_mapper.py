from typing import Any

from app.core.domain.interfaces import (
    CandidateReport,
    Evaluation,
    InterviewState,
    Question,
)
from app.core.llm.interfaces import LLMResponse


def _attr(obj: Any, name: str) -> Any:
    return getattr(obj, name)


def evaluation_to_jsonb(evaluation: Evaluation) -> dict:
    raw = evaluation.raw_response
    payload: dict[str, Any] = {
        "text": raw.text,
        "provider": raw.provider,
        "model": raw.model,
    }
    if raw.tokens_used is not None:
        payload["tokens_used"] = raw.tokens_used
    return payload


def evaluation_from_jsonb(payload: dict) -> LLMResponse:
    return LLMResponse(
        text=payload["text"],
        provider=payload["provider"],
        model=payload["model"],
        tokens_used=payload.get("tokens_used"),
    )


def _question_from_fields(
    *,
    id: str,
    topic: str,
    difficulty: int,
    prompt: str,
) -> Question:
    return Question(id=id, topic=topic, difficulty=difficulty, prompt=prompt)


def _question_to_dict(question: Question) -> dict[str, Any]:
    return {
        "id": question.id,
        "topic": question.topic,
        "difficulty": question.difficulty,
        "prompt": question.prompt,
    }


def _question_from_turn(turn: Any) -> Question:
    return _question_from_fields(
        id=_attr(turn, "question_id"),
        topic=_attr(turn, "question_topic"),
        difficulty=_attr(turn, "question_difficulty"),
        prompt=_attr(turn, "question_prompt"),
    )


def _evaluation_response_from_turn(turn: Any) -> LLMResponse:
    raw_payload = _attr(turn, "evaluation_raw_response")
    if isinstance(raw_payload, dict):
        return evaluation_from_jsonb(raw_payload)
    return LLMResponse(
        text="",
        provider=_attr(turn, "evaluation_provider"),
        model=_attr(turn, "evaluation_model"),
    )


def _evaluation_from_turn(turn: Any) -> Evaluation:
    return Evaluation(
        topic=_attr(turn, "question_topic"),
        score=_attr(turn, "evaluation_score"),
        feedback=_attr(turn, "evaluation_feedback"),
        raw_response=_evaluation_response_from_turn(turn),
    )


def _current_question_from_interview(interview: Any) -> Question:
    return _question_from_fields(
        id=_attr(interview, "current_question_id"),
        topic=_attr(interview, "current_question_topic"),
        difficulty=_attr(interview, "current_question_difficulty"),
        prompt=_attr(interview, "current_question_prompt"),
    )


def _placeholder_question(interview: Any, turns: list[Any]) -> Question:
    if turns:
        return _question_from_turn(turns[-1])
    return _question_from_fields(
        id="",
        topic=_attr(interview, "topic"),
        difficulty=_attr(interview, "difficulty"),
        prompt="",
    )


def _report_from_row(report: Any) -> CandidateReport:
    return CandidateReport(
        overall_summary=_attr(report, "overall_summary"),
        strengths=list(_attr(report, "strengths")),
        weaknesses=list(_attr(report, "weaknesses")),
        suggestions=list(_attr(report, "suggestions")),
        total_questions=_attr(report, "total_questions"),
    )


def report_from_row(report: Any) -> CandidateReport:
    return _report_from_row(report)


def to_state(
    interview: Any,
    turns: list[Any],
    report: Any | None = None,
) -> InterviewState:
    finished = _attr(interview, "status") == "finished"

    if finished:
        current_question = _placeholder_question(interview, turns)
    else:
        current_question = _current_question_from_interview(interview)

    history = [
        (_question_from_turn(turn), _evaluation_from_turn(turn)) for turn in turns
    ]

    state = InterviewState(
        topic=_attr(interview, "topic"),
        difficulty=_attr(interview, "difficulty"),
        current_question=current_question,
        history=history,
        finished=finished,
    )

    if report is not None:
        state.report = _report_from_row(report)

    return state


def to_interview_response(interview: Any, state: InterviewState) -> dict:
    response: dict[str, Any] = {
        "interview_id": str(_attr(interview, "id")),
        "domain": _attr(interview, "domain"),
        "topic": state.topic,
        "difficulty": state.difficulty,
        "finished": state.finished,
        "questions_answered": _attr(interview, "questions_answered"),
    }

    if not state.finished:
        response["current_question"] = _question_to_dict(state.current_question)

    return response


def to_report_response(interview_id: Any, report: CandidateReport) -> dict[str, Any]:
    return {
        "interview_id": str(interview_id),
        "overall_summary": report.overall_summary,
        "strengths": list(report.strengths),
        "weaknesses": list(report.weaknesses),
        "suggestions": list(report.suggestions),
        "total_questions": report.total_questions,
    }
