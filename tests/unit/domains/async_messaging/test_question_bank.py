from app.domains.async_messaging.question_bank import StaticAsyncMessagingQuestionBank


def test_next_question_returns_expected_id_for_topic_and_difficulty():
    bank = StaticAsyncMessagingQuestionBank()

    question = bank.next_question(topic="dead_letter_queue", difficulty=1)

    assert question.id == "sqs-01"
    assert question.topic == "dead_letter_queue"
    assert question.difficulty == 1
