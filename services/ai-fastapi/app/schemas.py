from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LanguageCode = Literal["en", "or", "hi"]
SUPPORTED_TRANSLATION_PAIRS = {
    ("en", "or"),
    ("or", "en"),
    ("en", "hi"),
    ("hi", "en"),
}


class TranslationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=5000)
    source_language: LanguageCode
    target_language: LanguageCode

    @model_validator(mode="after")
    def validate_language_pair(self) -> "TranslationRequest":
        if (self.source_language, self.target_language) not in SUPPORTED_TRANSLATION_PAIRS:
            raise ValueError("This language pair is not supported in Phase 1.")
        return self


class TranslationResponse(BaseModel):
    translated_text: str
    source_language: LanguageCode
    target_language: LanguageCode
    model_name: str
    model_version: str
