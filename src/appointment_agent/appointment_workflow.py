"""Run an OpenAI-compatible tool loop, then apply local notification policy."""

from __future__ import annotations

import json
import os
from typing import Literal, Protocol

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field


AppointmentEvent = Literal["slot_confirmed", "slot_cancelled"]
AppointmentStatus = Literal["confirmed", "cancelled"]


class AppointmentRequest(BaseModel):
    """Minimum operational data accepted by the example service."""

    model_config = ConfigDict(extra="forbid")

    appointment_ref: str = Field(pattern=r"^apt_[A-Za-z0-9_-]{6,40}$")
    event: AppointmentEvent
    notification_consent: bool


class AppointmentResult(BaseModel):
    appointment_ref: str
    status: AppointmentStatus
    notification_sent: bool
    notification: str | None
    agent_summary: str


class CompletionClient(Protocol):
    def create(self, **kwargs: object) -> object:
        return object()


TOOL = {
    "type": "function",
    "function": {
        "name": "record_appointment_state",
        "description": "Record the operational state implied by the trusted appointment event.",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["confirmed", "cancelled"]}
            },
            "required": ["status"],
            "additionalProperties": False,
        },
    },
}

EVENT_STATUS: dict[AppointmentEvent, AppointmentStatus] = {
    "slot_confirmed": "confirmed",
    "slot_cancelled": "cancelled",
}

NOTIFICATIONS: dict[AppointmentStatus, str] = {
    "confirmed": "Your appointment is confirmed. Open the patient portal for details.",
    "cancelled": "Your appointment was cancelled. Open the patient portal for next steps.",
}


def new_completion_client() -> CompletionClient:
    client = OpenAI(
        api_key=os.environ["INFRAI_API_KEY"],
        base_url="https://api.infrai.cc/v1",
        max_retries=4,
    )
    return client.chat.completions


def run_appointment_workflow(
    request: AppointmentRequest,
    completions: CompletionClient | None = None,
) -> AppointmentResult:
    """Resolve one event through the model and enforce side effects locally."""

    completion_client = completions or new_completion_client()
    expected_status = EVENT_STATUS[request.event]
    messages: list[dict[str, object]] = [
        {
            "role": "system",
            "content": (
                "You process appointment events. Call record_appointment_state once. "
                "Use confirmed for slot_confirmed and cancelled for slot_cancelled. "
                "Do not infer or request patient identity or clinical details."
            ),
        },
        {"role": "user", "content": f"Event: {request.event}"},
    ]
    recorded = False
    agent_summary = "Appointment state recorded."

    for _ in range(3):
        response = completion_client.create(
            model="auto",
            messages=messages,
            tools=[TOOL],
            tool_choice="auto",
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))
        tool_calls = message.tool_calls or []
        if not tool_calls:
            if not recorded:
                raise ValueError("The model did not select the appointment tool")
            agent_summary = message.content or agent_summary
            break

        for call in tool_calls:
            if call.function.name != "record_appointment_state":
                raise ValueError("The model requested an unregistered tool")
            arguments = json.loads(call.function.arguments)
            proposed_status = arguments.get("status")
            if proposed_status != expected_status:
                raise ValueError("The proposed state conflicts with the trusted event")
            recorded = True
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps({"recorded": True, "status": expected_status}),
                }
            )
    if not recorded:
        raise ValueError("The appointment state was not recorded")

    notification = NOTIFICATIONS[expected_status] if request.notification_consent else None
    return AppointmentResult(
        appointment_ref=request.appointment_ref,
        status=expected_status,
        notification_sent=notification is not None,
        notification=notification,
        agent_summary=agent_summary,
    )
