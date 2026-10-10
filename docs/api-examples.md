# API Examples

Curated examples for the OpsCommand REST API and WebSocket. The full,
auto-generated reference is available at `http://localhost:8000/docs`
(Swagger UI) and `http://localhost:8000/openapi.json`.

Conventions:

- Base URL: `http://localhost:8000`
- API prefix: `/api/v1`
- Org-scoped routes: `/api/v1/organizations/{org_id}/...`
- Auth: `Authorization: Bearer <access_token>`
- Errors use a consistent envelope:
  `{ "error": { "code": "...", "message": "...", "details": {...} } }`

The demo organization id and a demo incident id can be obtained from the seed
data or by listing incidents after login.

---

## 1. Authenticate

### Login

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"responder@acme-ops.io","password":"Demo-Password-123!"}'
```

Response `200`:

```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "expires_in": 900
}
```

### Refresh

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/refresh \
  -H 'Content-Type: application/json' \
  -d '{"refresh_token":"eyJhbGciOi..."}'
```

### Current user

```bash
curl -s http://localhost:8000/api/v1/auth/me \
  -H 'Authorization: Bearer <access_token>'
```

---

## 2. List incidents

```bash
curl -s "http://localhost:8000/api/v1/organizations/{org_id}/incidents?status=investigating" \
  -H 'Authorization: Bearer <access_token>'
```

Response `200` (paginated):

```json
{
  "items": [ { "id": "...", "title": "Checkout latency spike", "severity": "SEV2", "status": "investigating", "version": 2 } ],
  "total": 1,
  "limit": 50,
  "offset": 0,
  "has_more": false
}
```

---

## 3. Create an incident

```bash
curl -s -X POST "http://localhost:8000/api/v1/organizations/{org_id}/incidents" \
  -H 'Authorization: Bearer <access_token>' \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Payment gateway timeouts",
    "summary": "Elevated 5xx on /pay since 15:20 UTC.",
    "severity": "SEV1",
    "service_ids": ["<service-id>"],
    "commander_id": "<user-id>"
  }'
```

Response `201` returns the created incident.

---

## 4. Transition status (optimistic concurrency)

```bash
curl -s -X POST "http://localhost:8000/api/v1/organizations/{org_id}/incidents/{incident_id}/status" \
  -H 'Authorization: Bearer <access_token>' \
  -H 'Content-Type: application/json' \
  -d '{"status":"investigating","expected_version":1}'
```

If `expected_version` does not match the current row version, the API returns a
conflict error (409) so concurrent edits are not silently lost.

---

## 5. Assign an incident role

```bash
curl -s -X POST "http://localhost:8000/api/v1/organizations/{org_id}/incidents/{incident_id}/roles" \
  -H 'Authorization: Bearer <access_token>' \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"<user-id>","role":"commander"}'
```

---

## 6. Add a timeline event

```bash
curl -s -X POST "http://localhost:8000/api/v1/organizations/{org_id}/incidents/{incident_id}/timeline" \
  -H 'Authorization: Bearer <access_token>' \
  -H 'Content-Type: application/json' \
  -d '{"message":"Rolled back deploy 1234."}'
```

---

## 7. Run a playbook

```bash
curl -s -X POST "http://localhost:8000/api/v1/organizations/{org_id}/incidents/{incident_id}/playbook-runs" \
  -H 'Authorization: Bearer <access_token>' \
  -H 'Content-Type: application/json' \
  -d '{"playbook_id":"<playbook-id>","idempotency_key":"run-2026-10-10-001"}'
```

Response `201` returns the run (status `pending`). Reusing the same
`idempotency_key` returns the existing run instead of re-executing.

### Poll the run

```bash
curl -s "http://localhost:8000/api/v1/organizations/{org_id}/incidents/{incident_id}/playbook-runs/{run_id}" \
  -H 'Authorization: Bearer <access_token>'
```

---

## 8. Generate / download a report

```bash
# Preview (Markdown in JSON)
curl -s "http://localhost:8000/api/v1/organizations/{org_id}/incidents/{incident_id}/report" \
  -H 'Authorization: Bearer <access_token>'

# Download as a file
curl -s -OJ "http://localhost:8000/api/v1/organizations/{org_id}/incidents/{incident_id}/report/download" \
  -H 'Authorization: Bearer <access_token>'
```

---

## 9. Audit log

```bash
curl -s "http://localhost:8000/api/v1/organizations/{org_id}/audit?resource_id={incident_id}" \
  -H 'Authorization: Bearer <access_token>'
```

---

## 10. Health / readiness / metrics

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/ready
curl -s http://localhost:8000/metrics
```

---

## WebSocket: subscribe to an incident room

```
ws://localhost:8000/ws/incidents/{incident_id}?token=<access_token>
```

Example (Node.js):

```js
const ws = new WebSocket(
  `ws://localhost:8000/ws/incidents/${incidentId}?token=${accessToken}`
);

ws.onopen = () => console.log('connected');
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  // msg.type: connected | incident_created | incident_updated |
  //           status_changed | role_assigned | timeline_event |
  //           action_item | playbook_progress | ping
  console.log(msg.type, msg);
};
ws.onclose = (e) => console.log('closed', e.code, e.reason);
```

A typical `playbook_progress` event:

```json
{
  "type": "playbook_progress",
  "incident_id": "...",
  "run_id": "...",
  "status": "progress",
  "progress": [
    { "index": 0, "type": "timeline_message", "status": "done", "result": { "message": "Escalation started" } },
    { "index": 1, "type": "create_action_item", "status": "done", "result": { "action_item_id": "..." } }
  ]
}
```
