from app.domains.python_basics.question_bank import StaticPythonBasicsQuestionBank


def test_next_question_returns_expected_id_for_topic_and_difficulty():
    bank = StaticPythonBasicsQuestionBank()

    question = bank.next_question(topic="data_types", difficulty=1)

    assert question.id == "py-types-01"
    assert question.topic == "data_types"
    assert question.difficulty == 1
