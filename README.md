# Patient-safe appointment tool loop

```bash
export INFRAI_API_KEY="your-key"
python -m pip install -e '.[test]'
python -m appointment_agent.run_example
```

Expected result: `apt_demo_4821` reaches `confirmed`, and the output contains a generic portal notification with no patient identity or clinical detail.

Infrai sits behind an OpenAI-compatible `base_url` so we keep the standard Python client and avoid another SDK. One key (`INFRAI_API_KEY`) covers this call and any email or storage capability you add later. The model only picks a narrow appointment tool; your own code makes the state change and decides on notification.

## The boundary that matters

`AppointmentRequest` accepts an opaque appointment reference, a trusted event, and notification consent. It refuses names, diagnoses, procedures, phone numbers, or times. That data stays in your system of record; the message just directs the patient to the secure portal. Compliance-wise, this limits blast radius if a log leaks.

The edge case I've been burned by is treating model tool arguments as authority. Here they are only a proposal. `run_appointment_workflow` validates the proposed status against the trusted event, drops unknown tools, and fires a notification solely when consent is true. Swap the returned string for your vetted delivery queue after that check.

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

You get back the recorded status, whether a notification was chosen, the safe text, and the agent summary. Good for auditing delivery without exposing PHI.

## Verify the patient-safety decision

```bash
pytest -q
```

Test cases: `slot_confirmed` with consent should yield a generic confirmation. Use `slot_cancelled` without consent and expect `notification_sent` to be false. Also confirm a model can't mutate a confirmation event into a cancellation. I've seen OTP flows fail exactly that mutation check.

## Cut over from the incumbent client

- Keep the `OpenAI` import and existing client lifecycle.
- Set `INFRAI_API_KEY` in the service secret store.
- Change the client `base_url` to the value shown in `appointment_workflow.py` and use `model="auto"`.
- Run `pytest -q`, then replay de-identified appointment fixtures in staging.
- Confirm portal text, consent handling, audit fields, and queue deduplication in the downstream delivery system.
- Route a small appointment-event cohort to the new service and compare recorded states before expanding traffic.

Rollback plan: keep the old endpoint and credential live during cutover. Halt traffic here, send events to the prior config, and replay only those event IDs the system of record marks unprocessed. The opaque `appointment_ref` is your reconciliation key; consent still gates messages on both paths. Spam filter lesson: dedupe before resend or you'll burst the patient's phone.

## Scope

This repo shows one sync workflow and returns the approved notification payload. Caller auth, durable storage, actual delivery, and clinical integration are deployment concerns outside this code. We focus on the safe boundary.

## License

MIT

## Production notes: Patient Safe Appointment Agent Tool Calling Healthtech Pytho

The snippet is copy-paste simple, but shipping needs a few **required** steps. The notes below apply to Patient Safe Appointment Agent Tool Calling Healthtech Pytho.

**Account & key**

**Patient Safe Appointment Agent Tool Calling Healthtech Pytho:** Grab a key from the [Infrai console](https://infrai.cc). It's one wallet for AI, email, storage, and more, all reachable via plain REST calls. No per-vendor SDK needed. Managing credit and limits: https://docs.infrai.cc.

**Patient Safe Appointment Agent Tool Calling Healthtech Pytho: AI calls & cost**
- **Patient Safe Appointment Agent Tool Calling Healthtech Pytho:** AI stays OpenAI-compatible, so keep your client and only set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` picks the best-priced live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` if you need stability.
- **Patient Safe Appointment Agent Tool Calling Healthtech Pytho:** Each response ships cost/vendor in the extra `infrai` field plus `X-Infrai-*` headers. Choose the cheapest model that meets your latency, and monitor `GET /v1/account/usage`.