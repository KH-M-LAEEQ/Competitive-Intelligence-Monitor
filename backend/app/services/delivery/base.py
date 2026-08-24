from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DeliveryPayload:
    title: str
    body_markdown: str


@dataclass
class DeliveryResult:
    success: bool
    detail: str | None = None


class DeliveryConnector(ABC):
    @abstractmethod
    def send(self, config: dict, payload: DeliveryPayload) -> DeliveryResult:
        ...
