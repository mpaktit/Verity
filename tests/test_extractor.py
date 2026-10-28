from app.services.extractor import extract_signals, score_page, strip_html


def test_strip_html_removes_scripts_and_tags():
    html = "<html><script>alert(1)</script><p>Student pack is free</p></html>"
    text = strip_html(html)
    assert "alert" not in text
    assert "Student pack is free" in text


def test_extract_signals_finds_trial_and_student_language():
    html = "<p>Start a free trial. Verified students get GitHub Education benefits and starter credits.</p>"
    signals = extract_signals(html)
    labels = {item["label"] for item in signals}
    assert "free-trial" in labels
    assert "student-program" in labels
    assert score_page(signals, 200) > 50


def test_failed_http_scores_zero():
    assert score_page([{"label": "trial", "weight": 20}], 404) == 0
