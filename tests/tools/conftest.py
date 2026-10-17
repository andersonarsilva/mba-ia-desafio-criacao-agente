from dataclasses import dataclass, field
from typing import Any

import pytest


@dataclass
class FakeConfirmation:
    confirmed: bool


@dataclass
class FakeToolContext:
    user_id: str
    tool_confirmation: FakeConfirmation | None = None
    requested: list[dict[str, Any]] = field(default_factory=list)

    def request_confirmation(self, *, hint: str | None = None, payload: Any = None) -> None:
        self.requested.append({"hint": hint, "payload": payload})


@pytest.fixture
def contexto_101() -> FakeToolContext:
    return FakeToolContext(user_id="101")
