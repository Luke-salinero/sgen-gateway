# sgen-gateway

Public-facing API gateway for the SGen platform, deployed behind a Cloudflare
Tunnel. It authenticates incoming requests, enforces per-subject entitlements
(plan limits), and forwards accepted work to `sgen-controller` (job creation)
and `sgen-worker` (status/results).

## What this service does

- Verifies the caller's bearer JWT (Keycloak-issued, RS256 via JWKS)
- Calls `sgen-entitlement` to resolve the caller's plan limits
- Validates and normalizes the SGen job configuration (`n`, `k`, masks, ranges)
- Rejects requests that exceed the caller's entitled `max_n` / `max_k`
- Forwards accepted jobs to `sgen-controller` and proxies status/result
  lookups to `sgen-worker`, scoped to the caller's own jobs

## Repository structure

- `app/api/v1/` — routes: `health`, `sgen_submit` (`/submit`), `status`
  (`/status/{job_id}`), `results` (`/results/{job_id}`)
- `app/core/` — settings (`config.py`) and logging setup
- `app/models/` — request/response schemas and job-config validation
- `app/services/` — HTTP clients for `sgen-entitlement`, `sgen-controller`,
  and `sgen-worker`, plus entitlement-limit enforcement
- `app/util/` — JWT verification and bearer-token extraction

## API endpoints

| Method | Path | Auth | Description |
| ------ | ---- | ---- | ----------- |
| `GET`  | `/health` | none | Service name, version, mode, status. |
| `POST` | `/submit` | Bearer JWT | Validates a job config against the caller's entitlements and creates a job via `sgen-controller`. |
| `GET`  | `/status/{job_id}` | Bearer JWT | Polls job progress/summary via `sgen-worker`, scoped to the caller's own job. |
| `GET`  | `/results/{job_id}` | Bearer JWT | Fetches completed job results via `sgen-worker`, scoped to the caller's own job. |

All authenticated routes resolve the caller's identity from the bearer JWT,
then call `sgen-entitlement` to get a `subject_id` and limits; that
`subject_id` is what scopes job ownership downstream, not anything the client
sends directly.

## Job configuration format (`POST /submit` body)

| Field | Type | Required | Notes |
| ----- | ---- | -------- | ----- |
| `n` | integer (1-2048) | yes | Bit width of the binary strings to process. |
| `k` | integer | yes | Number of active bits per pattern; must be ≤ `n`. |
| `block_size` | integer | yes | Internal batching parameter for `sgen-controller`/`sgen-worker`. |
| `existential` | boolean | no | Defaults to `true`. |
| `prune_masks` | array of `"0b..."` strings | no | Each must be `n` bits wide with ≤ `k` set bits, and fall within one of `ranges`. |
| `find_masks` | array of `"0b..."` strings | no | Same constraints as `prune_masks`. |
| `ranges` | array of `["0bSTART", "0bEND"]` pairs | yes (at least one) | Non-overlapping, `n`-bit inclusive intervals; every mask must fall in one of them. |

See `app/models/sgen.py` for the full validation logic (`SGenSubmitRequest`).

## Configuration

Environment variables (see `app/core/config.py`):

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `SGEN_MODE` | `mock` | `mock` or `live`. |
| `SGEN_CONTROLLER_BASE_URL` | `http://127.0.0.1:8001` | `sgen-controller` base URL. |
| `SGEN_ENTITLEMENTS_BASE_URL` | `http://127.0.0.1:8002` | `sgen-entitlement` base URL. |
| `SGEN_WORKER_BASE_URL` | `http://0.0.0.0:8002` | `sgen-worker` base URL (read directly via `os.getenv`, not through `Settings`). |
| `SGEN_REQUEST_TIMEOUT` | `120` | Timeout (seconds) for calls to `sgen-controller`. |
| `JWT_ISSUER`, `JWT_AUDIENCE`, `JWT_ALGORITHMS` | see `config.py` | Expected JWT claims. |
| `JWT_JWKS_URL` | prod Keycloak JWKS endpoint | Used to verify RS256 tokens. |
| `JWT_PUBLIC_KEY` | unset | Only consulted if `JWT_JWKS_URL` is unset (legacy HS256 path); the service refuses to verify tokens on that path until this is set. |

No secrets should be committed; see `.gitignore` for what's excluded
(env files, Cloudflare Tunnel credentials, keys/certs, local DBs).

## Running locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Available at `http://127.0.0.1:8000`, docs at `/docs`.

## Tests

```bash
pytest
```
