from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel


class LLMOutputError(Exception):
    pass


@dataclass
class LLMCallResult:
    value: BaseModel
    model: str
    prompt_tokens: int
    completion_tokens: int


@dataclass
class EmbedResult:
    vectors: list[list[float]]
    model: str
    prompt_tokens: int


class LLMClient(Protocol):
    """Model-agnostic interface — swapping providers is a config change,
    never a call-site change. All calls are text-in/JSON-out with no
    tool/function-calling access, so untrusted scraped content passed as
    `user` can never trigger a side effect even if it contains an
    injection attempt (see prompts.py for the untrusted-content wrapper).
    """

    def complete(
        self, system: str, user: str, response_model: type[BaseModel]
    ) -> LLMCallResult:
        ...

    def embed(self, texts: list[str]) -> EmbedResult:
        ...
