"""Run one confirmed appointment through the live tool loop."""

from .appointment_workflow import AppointmentRequest, run_appointment_workflow


def main() -> None:
    result = run_appointment_workflow(
        AppointmentRequest(
            appointment_ref="apt_demo_4821",
            event="slot_confirmed",
            notification_consent=True,
        )
    )
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
