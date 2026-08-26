# Sub-skill: Create Test Account

## Purpose

Create a dedicated test account for automated testing with admin privileges. API registration first, SQL fallback if needed. Always attempt role elevation after creation.

## Input (provided by orchestrator)

- `source` — project source root
- `port` — backend port
- `module` — module name
- `db_container` — DB container name (if Docker)

## Test Credentials

- email: `qa_autotest@test.local`
- password: `{{TEST_ACCOUNT_PASSWORD}}`
- username/name: `QA AutoTest`
- target_role: `admin`

## Execution

### Path A: Registration API (preferred)

1. Find registration endpoint:
```bash
grep -rn "register\|signup\|sign-up\|create.*user\|create.*account" {source} \
  --include="*.py" --include="*.ts" --include="*.js" --include="*.java" --include="*.go" \
  | grep -i "route\|router\|app\.\|@\|endpoint\|path\|url"
```

2. Patterns to match:
   - Python: `@router.post("/register")`, `@app.route("/api/auth/register")`
   - Node: `router.post('/register')`, `app.post('/api/auth/signup')`
   - Java: `@PostMapping("/register")`, `@RequestMapping("/auth/signup")`

3. Determine required fields by reading the handler:
   - Typical: `email`, `password`, `name`/`username`
   - May include: `confirm_password`, `role`, `org_id`

4. Execute registration (attempt with role first):
```bash
# Try with role field
curl -X POST http://localhost:{port}/{register_path} \
  -H "Content-Type: application/json" \
  -d '{"email":"qa_autotest@test.local","password":"{{TEST_ACCOUNT_PASSWORD}}","name":"QA AutoTest","role":"admin"}'
```

If role field rejected (422/400 mentioning "role") → retry without role:
```bash
curl -X POST http://localhost:{port}/{register_path} \
  -H "Content-Type: application/json" \
  -d '{"email":"qa_autotest@test.local","password":"{{TEST_ACCOUNT_PASSWORD}}","name":"QA AutoTest"}'
```

If 2xx → success, proceed to role elevation (Step C).

### Path B: SQL Fallback (if no register API or it fails)

1. Read auth model — determine table + columns:
```bash
grep -rn "class.*User\|CREATE TABLE.*user\|__tablename__.*user" {source} \
  --include="*.py" --include="*.ts" --include="*.sql" --include="*.java"
```

2. Read password hashing method:
```bash
grep -rn "bcrypt\|argon2\|hashlib\|pbkdf2\|crypto\|hash.*password\|password.*hash" {source} \
  --include="*.py" --include="*.ts" --include="*.js" --include="*.java"
```

3. Generate password hash:
```bash
python3 -c "import bcrypt; print(bcrypt.hashpw(b'{{TEST_ACCOUNT_PASSWORD}}', bcrypt.gensalt()).decode())"
```

4. Detect role column/field:
```bash
grep -rn "role\|is_admin\|is_superuser\|user_type\|permissions" {source} \
  --include="*.py" --include="*.ts" --include="*.sql" --include="*.java" \
  | grep -i "column\|field\|model\|schema\|table\|enum"
```

5. Insert into DB with admin role:
```bash
# Adapt role field name and value based on Step 4 detection
docker exec {db_container} psql -U {user} -d {db} -c \
  "INSERT INTO users (email, password_hash, name, is_active, role) VALUES ('qa_autotest@test.local', '{hash}', 'QA AutoTest', true, 'admin') ON CONFLICT (email) DO NOTHING;"
```

If role column uses enum/integer: detect correct admin value from code (e.g., `role=1`, `role='ADMIN'`, `is_admin=true`).

### Step C: Role Elevation (MANDATORY after account creation)

After account exists (via Path A or B), ensure it has admin privileges:

1. Detect the role model:
```bash
grep -rn "role\|is_admin\|is_superuser\|user_type\|UserRole\|RoleEnum" {source} \
  --include="*.py" --include="*.ts" --include="*.js" --include="*.java" \
  | grep -iv "test\|mock\|spec" | head -20
```

2. Determine role field name and admin value:
   - `role` column with string enum → value: `"admin"` or `"ADMIN"`
   - `role` column with int enum → value: find admin int from enum definition
   - `is_admin` boolean → value: `true`
   - `is_superuser` boolean → value: `true`
   - `user_type` → value: `"admin"` or equivalent

3. Elevate via SQL (most reliable):
```bash
docker exec {db_container} psql -U {user} -d {db} -c \
  "UPDATE users SET {role_field} = '{admin_value}' WHERE email = 'qa_autotest@test.local';"
```

4. If no DB access (remote mode) → try admin API:
```bash
# Login as existing admin (if seed admin credentials found in .env/code)
# Then PATCH/PUT user role via admin API
curl -X PATCH http://localhost:{port}/api/admin/users/{user_id}/role \
  -H "Authorization: Bearer {admin_token}" \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'
```

5. Verify elevation — login and check for admin indicator:
```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:{port}/{login_path} \
  -H "Content-Type: application/json" \
  -d '{"email":"qa_autotest@test.local","password":"{{TEST_ACCOUNT_PASSWORD}}"}' \
  | jq -r '.{token_path}')

# Try an admin-only endpoint (common patterns)
curl -s -o /dev/null -w "%{http_code}" http://localhost:{port}/api/admin/users \
  -H "Authorization: Bearer $TOKEN"
# 200 = admin confirmed; 403 = elevation failed
```

🔒 Rules:
- NEVER skip role elevation — a regular user account cannot test admin features
- If elevation fails via SQL AND admin API → log warning, proceed with note in ENV-CONFIG
- If role model cannot be detected → try common patterns: `role='admin'`, `is_admin=true`, `is_superuser=true`

## Output

```
method: {api_register|sql_fallback}
email: qa_autotest@test.local
password: {{TEST_ACCOUNT_PASSWORD}}
role: {admin|user} (elevated: {true|false})
role_field: {role|is_admin|is_superuser|user_type}
register_endpoint: {path|null}
db_table: {table_name|null}
elevation_method: {sql|admin_api|registration_param|failed}
```
