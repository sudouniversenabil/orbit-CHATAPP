"""Wake phrase matching on recognized speech."""


def wake_word_command(text: str, phrase: str) -> str | None:
    """Return text after a leading wake phrase, or None if absent."""
    words = text.strip().split()
    phrase_words = phrase.casefold().split()
    normalized_words = [word.casefold().strip(" ,.!?") for word in words]
    if normalized_words[: len(phrase_words)] != phrase_words:
        return None
    if len(words) == len(phrase_words):
        return ""
    return " ".join(words[len(phrase_words):]).strip(" ,.!?")
