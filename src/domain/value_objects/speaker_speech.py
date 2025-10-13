"""Domain value object for speaker and speech content."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SpeakerSpeech:
    """Value object representing a speaker and their speech content.

    This is a domain-level representation that is independent of any
    infrastructure or processing implementation details.

    Attributes:
        speaker: Name of the speaker
        speech_content: Content of the speech
        chapter_number: Sequential number of the divided text chapter
        sub_chapter_number: Sequential number if text was re-divided
        speech_order: Order of the speech in the sequence
    """

    speaker: str
    speech_content: str
    chapter_number: int = 1
    sub_chapter_number: int = 1
    speech_order: int = 1

    def __post_init__(self):
        """Validate the value object.

        Raises:
            ValueError: If speaker or speech_content is empty
        """
        if not self.speaker:
            raise ValueError("speaker cannot be empty")
        if not self.speech_content:
            raise ValueError("speech_content cannot be empty")
        if self.chapter_number < 1:
            raise ValueError("chapter_number must be >= 1")
        if self.sub_chapter_number < 1:
            raise ValueError("sub_chapter_number must be >= 1")
        if self.speech_order < 1:
            raise ValueError("speech_order must be >= 1")
