"""Appointment automation with a local patient-safety boundary."""

from .appointment_workflow import AppointmentRequest, AppointmentResult, run_appointment_workflow

__all__ = ["AppointmentRequest", "AppointmentResult", "run_appointment_workflow"]
