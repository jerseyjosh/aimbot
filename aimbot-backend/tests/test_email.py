from aimbot.email_renderer import EmailRenderer

def test_first_sentence():

    text = "This is the first sentence. Here is the second sentence. And a third."
    result = EmailRenderer.first_sentence(text)
    assert result == "This is the first sentence."

def test_period_in_first_sentence():
    text = "This cost £1.2 million. Here is the second sentence."
    result = EmailRenderer.first_sentence(text)
    assert result == "This cost £1.2 million."