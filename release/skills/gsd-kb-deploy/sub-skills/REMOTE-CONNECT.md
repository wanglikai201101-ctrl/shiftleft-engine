# Sub-skill: Remote Connect Flow

## Purpose

Connect to an already-running remote environment: probe endpoints, verify/create account, generate ENV-CONFIG.

## Input (provided by orchestrator)

- `url` — remote base URL
- `module` — module name
- `user` — existing email (optional)
- `pass` — existing password (optional)
- `output` — KB output directory

## Execution

### 1: Probe health

```bash
for path in /health /api/health /healthz /api/v1/health /ping /; do
  status=$(curl -s -o /dev/null -w "%{http_code}" "{url}${path}" 2>/dev/null)
  [ "$status" = "200" ] && break
done
```

No health response → warn but continue.

### 2: Discover login endpoint

```bash
for path in /api/auth/login /api/login /auth/login /login /api/v1/auth/login; do
  status=$(curl -s -o /dev/null -w "%{http_code}" -X POST "{url}${path}" \
    -H "Content-Type: application/json" -d '{}' 2>/dev/null)
  [ "$status" != "404" ] && [ "$status" != "000" ] && break
done
```

400/401/422 = endpoint exists (rejects bad input). 404 = not found.

### 3: Handle credentials

**If --user and --pass provided:** skip to step 4.

**If NOT provided:** try register:
```bash
for path in /api/auth/register /api/register /auth/register /register /api/v1/auth/register; do
  result=$(curl -s -w "\n%{http_code}" -X POST "{url}${path}" \
    -H "Content-Type: application/json" \
    -d '{"email":"qa_autotest@test.local","password":"{{TEST_ACCOUNT_PASSWORD}}","name":"QA AutoTest"}')
  http_code=$(echo "$result" | tail -1)
  [ "$http_code" = "200" ] || [ "$http_code" = "201" ] && break
done
```

If all register paths fail → STOP:
```
❌ Cannot create test account on remote environment.
   No registration endpoint found at {url}.
   Please provide existing credentials: --user <email> --pass <pwd>
```

### 4: Verify login

```bash
curl -X POST {url}/{login_path} \
  -H "Content-Type: application/json" \
  -d '{"email":"{user}","password":"{pass}"}'
```

Extract token: check `response.token`, `response.data.token`, `response.access_token`, headers.

### 5: Detect frontend URL

Heuristic:
```bash
content_type=$(curl -s -I "{url}/" | grep -i "content-type" | head -1)
```
- `text/html` → likely frontend (or SSR) → `frontend_url = url`
- `application/json` → backend-only → check `app.{domain}` or same URL

Cannot determine → assume `frontend_url = backend_url`.

### 6: Generate ENV-CONFIG.json (remote mode)

```json
{
  "_meta": {
    "generated_by": "gsd-kb-deploy",
    "generated_at": "{TODAY}",
    "module": "{module}",
    "deploy_method": "remote-connect",
    "account_method": "{provided|api_register}"
  },
  "environment": {
    "backend_url": "{url}",
    "frontend_url": "{frontend_url}",
    "frontend_login_path": "{login_path}",
    "health_endpoint": "{health_path}",
    "api_prefix": "{detected_prefix}"
  },
  "auth": {
    "method": "{bearer|cookie|session}",
    "username": "{user_email}",
    "password": "{user_password}",
    "login_endpoint": "{login_path}",
    "login_body_field": "{email|username|phone}",
    "token_field": "{response_path}",
    "register_endpoint": "{register_path|null}"
  },
  "database": {
    "type": "remote",
    "container": null,
    "connection": null
  }
}
```

## Output

```
remote_url: {url}
health_endpoint: {path}
login_endpoint: {path}
account: {provided|registered}
frontend_url: {url}
env_config_path: {output}/{module}/tests/ENV-CONFIG.json
```
