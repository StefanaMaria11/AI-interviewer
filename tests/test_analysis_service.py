from backend.services.analysis_service import AnalysisService

def test_sentiment_counts_whole_words_only():
    service = AnalysisService()

    answers = [
        "I compared the likelihood of different model outputs."
    ]

    result = service.analyze_sentiment(answers)

    assert result["positive_score"] == 0
    assert result["negative_score"] == 0
    assert result["sentiment"] == "neutral"

def test_negated_positive_sentiment():
    service = AnalysisService()

    answers = [
        "I did not enjoy debugging."
    ]

    result = service.analyze_sentiment(answers)

    assert result["positive_score"] == 0
    assert result["negative_score"] == 1
    assert result["sentiment"] == "challenging"

def test_negated_negative_sentiment():
    service = AnalysisService()

    answers = [
        "I was not disappointed with the result."
    ]

    result = service.analyze_sentiment(answers)

    assert result["positive_score"] == 0
    assert result["negative_score"] == 0
    assert result["sentiment"] == "neutral"