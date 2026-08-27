from app.domains.python_basics.question_bank import StaticPythonBasicsQuestionBank

DATA_TYPES_DIFFICULTY_1_IDS = {
    "py-types-01",
    "py-types-02",
}


def test_next_question_returns_expected_id_for_topic_and_difficulty():
    bank = StaticPythonBasicsQuestionBank()

    question = bank.next_question(topic="data_types", difficulty=1)

    assert question.id in DATA_TYPES_DIFFICULTY_1_IDS
    assert question.topic == "data_types"
    assert question.difficulty == 1
