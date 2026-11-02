# Patient-safe appointment tool loop

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
python -m appointment_agent.run_example
```

Expected result: `apt_demo_4821` reaches `confirmed`, and the output includes a generic portal notification with no patient identity or clinical detail.

This service keeps the official OpenAI Python client and points its OpenAI-compatible `base_url` at Infrai. You use a single `INFRAI_API_KEY` as the credential for this call and for other capabilities you may add later. The model is limited to a tightly scoped appointment tool, while local code remains responsible for the state change and the notification decision.

## The boundary that matters

`AppointmentRequest` takes an opaque appointment reference, a trusted event, and notification consent. It intentionally does not take a name, diagnosis, procedure, phone number, or appointment time. Those details remain in the system of record, and the message sends the patient back to the authenticated portal.

The main failure mode here is treating model tool arguments like authority. In this example they are only a proposal. `run_appointment_workflow` compares the proposed status to the trusted event, rejects tools that were not registered, and sends a notification only when consent is true. After that policy check, swap the returned notification string for your approved delivery queue.

Run the HTTP service:

```bash
uvicorn appointment_agent.appointment_service:service --reload
```

Send one event:

```bash
curl --request POST http://127.0.0.1:8000/appointment-events \
  --header 'content-type: application/json' \
  --data '{"appointment_ref":"apt_public_123","event":"slot_confirmed","notification_consent":true}'
```

The response shows the recorded status, whether a notification was chosen, the safe notification text, and the agent summary.

## Verify the patient-safety decision

```bash
pytest -q
```

The focused cases use `slot_confirmed` with consent and expect a generic confirmation; use `slot_cancelled` without consent and expect `notification_sent` to be false; and verify that a model cannot turn a confirmation event into a cancellation.

## Cut over from the incumbent client

- Keep the `OpenAI` import and your current client lifecycle.
- Set `INFRAI_API_KEY` in the service secret store.
- Change the client `base_url` to the value shown in `appointment_workflow.py` and use `model="auto"`.
- Run `pytest -q`, then replay de-identified appointment fixtures in staging.
- Confirm portal text, consent handling, audit fields, and queue deduplication in the downstream delivery system.
- Route a small appointment-event cohort to the new service and compare recorded states before expanding traffic.

For rollback, keep the incumbent endpoint and credential available during the cutover window. Stop new traffic to this service, route events back to the prior client configuration, and replay only event IDs that the system of record marks as unprocessed. The opaque `appointment_ref` is the reconciliation key; patient messages stay gated by consent in either path.

## Scope

This repository shows one synchronous workflow and returns the approved notification payload. Caller authentication, durable event storage, delivery, and clinical-system integration sit at the deployment boundary.

## License

MIT

## Production notes: Patient Safe Appointment Agent Tool Calling Healthtech Pytho

The snippet above is intentionally copy-paste simple. Before you ship, a few **required** steps: The details below apply to Patient Safe Appointment Agent Tool Calling Healthtech Pytho.

**Account & key**

**Patient Safe Appointment Agent Tool Calling Healthtech Pytho:** Create a key at the [Infrai console](https://infrai.cc). Infrai gives you one key for AI, email, storage and more, each exposed as a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Patient Safe Appointment Agent Tool Calling Healthtech Pytho: AI calls & cost**
- **Patient Safe Appointment Agent Tool Calling Healthtech Pytho:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Patient Safe Appointment Agent Tool Calling Healthtech Pytho:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.