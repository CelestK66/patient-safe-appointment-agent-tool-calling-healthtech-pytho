from __future__ import annotations

from types import SimpleNamespace

import pytest

from appointment_agent.appointment_workflow import AppointmentRequest, run_appointment_workflow


class FakeMessage:
    def __init__(self, *, content: str | None = None, tool_calls: list[object] | None = None):
        self.content = content
        self.tool_calls = tool_calls

    def model_dump(self, exclude_none: bool = True) -> dict[str, object]:
        del exclude_none
        return {"role": "assistant", "content": self.content}


class FakeCompletions:
    def __init__(self, messages: list[FakeMessage]):
        self.messages = iter(messages)

    def create(self, **kwargs: object) -> object:
        del kwargs
        return SimpleNamespace(choices=[SimpleNamespace(message=next(self.messages))])


def tool_call(status: str) -> object:
    function = SimpleNamespace(name="record_appointment_state", arguments=f'{{"status":"{status}"}}')
    return SimpleNamespace(id="call_1", function=function)


def test_confirmation_with_consent_produces_safe_operational_notice() -> None:
    completions = FakeCompletions(
        [
            FakeMessage(tool_calls=[tool_call("confirmed")]),
            FakeMessage(content="Confirmation recorded."),
        ]
    )
    request = AppointmentRequest(
        appointment_ref="apt_public_123",
        event="slot_confirmed",
        notification_consent=True,
    )

    result = run_appointment_workflow(request, completions)

    assert result.status == "confirmed"
    assert result.notification_sent is True
    assert result.notification == "Your appointment is confirmed. Open the patient portal for details."


def test_notification_is_suppressed_without_consent() -> None:
    completions = FakeCompletions(
        [
            FakeMessage(tool_calls=[tool_call("cancelled")]),
            FakeMessage(content="Cancellation recorded."),
        ]
    )
    request = AppointmentRequest(
        appointment_ref="apt_public_456",
        event="slot_cancelled",
        notification_consent=False,
    )

    result = run_appointment_workflow(request, completions)

    assert result.status == "cancelled"
    assert result.notification_sent is False
    assert result.notification is None


def test_model_cannot_override_the_trusted_event() -> None:
    completions = FakeCompletions([FakeMessage(tool_calls=[tool_call("cancelled")])])
    request = AppointmentRequest(
        appointment_ref="apt_public_789",
        event="slot_confirmed",
        notification_consent=True,
    )

    with pytest.raises(ValueError, match="conflicts with the trusted event"):
        run_appointment_workflow(request, completions)
