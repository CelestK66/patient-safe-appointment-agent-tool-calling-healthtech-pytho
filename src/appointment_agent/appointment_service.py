"""HTTP boundary for the appointment workflow."""

from fastapi import FastAPI, HTTPException

from .appointment_workflow import AppointmentRequest, AppointmentResult, run_appointment_workflow


service = FastAPI(title="Patient-safe appointment agent")


@service.post("/appointment-events", response_model=AppointmentResult)
def process_appointment_event(request: AppointmentRequest) -> AppointmentResult:
    try:
        return run_appointment_workflow(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
