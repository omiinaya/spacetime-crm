#!/usr/bin/env python3
"""Bootstrap spacetime-crm: create admin user, tenant, password, then seed demo data.

Reads environment variables STDB_HOST, STDB_PORT, STDB_DB, and CRM_API_URL
for flexibility with test instances (defaults: localhost:3001 / spacetime-crm / localhost:8723).
"""

import os
import httpx
import bcrypt
import time

STDB_HOST = os.environ.get("STDB_HOST", "localhost")
STDB_PORT = os.environ.get("STDB_PORT", "3001")
STDB_DB = os.environ.get("STDB_DB", "spacetime-crm")
CRM_API_URL = os.environ.get("CRM_API_URL", "http://localhost:8723")

STDB = f"http://{STDB_HOST}:{STDB_PORT}"

C = httpx.Client(base_url=STDB, timeout=15)

# Wait for STDB
for i in range(10):
    try:
        r = C.get("/health")
        if r.status_code == 200:
            break
    except Exception:
        pass
    time.sleep(1)

# 1. Create default tenant
r = C.post(
    f"/v1/database/{STDB_DB}/call/create_tenant", json=["Default Corp", "default"]
)
print(f"  Tenant created: HTTP {r.status_code}")

# 2. Create admin user via reducer
r = C.post(
    f"/v1/database/{STDB_DB}/call/create_user",
    json=["admin", "admin@crm.local", "admin"],
)
print(f"  User created: HTTP {r.status_code}")

# 3. Find user ID
r = C.post(
    f"/v1/database/{STDB_DB}/sql",
    content="SELECT * FROM user WHERE email = 'admin@crm.local'",
    headers={"Content-Type": "text/plain"},
)
users = r.json()
if users and users[0]["rows"]:
    uid = users[0]["rows"][0][0]
    username = users[0]["rows"][0][1]
    print(f"  User ID: {uid}, username: {username}")
    # 4. Set password
    hashed = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
    r = C.post(f"/v1/database/{STDB_DB}/call/set_user_password", json=[uid, hashed])
    print(f"  Password set: HTTP {r.status_code}")
else:
    print("  ERROR: User not found!")
    exit(1)

# 5. Find tenant ID
r = C.post(
    f"/v1/database/{STDB_DB}/sql",
    content="SELECT * FROM tenants WHERE slug = 'default'",
    headers={"Content-Type": "text/plain"},
)
tenants = r.json()
if tenants and tenants[0]["rows"]:
    tid = tenants[0]["rows"][0][0]
    print(f"  Tenant ID: {tid}")
    # 6. Add admin as tenant member
    r = C.post(
        f"/v1/database/{STDB_DB}/call/add_tenant_member", json=[tid, username, "admin"]
    )
    print(f"  Member added: HTTP {r.status_code}")
else:
    print("  ERROR: Tenant not found!")
    exit(1)

# 7. Verify login via API
C2 = httpx.Client(base_url=CRM_API_URL, timeout=15)
r = C2.post(
    "/api/auth/login", json={"email": "admin@crm.local", "password": "admin123"}
)
if r.status_code == 200:
    data = r.json()
    print(f"  ✅ Login OK, token: {data['token'][:30]}...")
    print(f"     tenant_id: {data.get('user', data).get('tenant_id', 'N/A')}")
else:
    print(f"  ❌ Login failed: {r.status_code} {r.text}")
    exit(1)

print("\n✅ Bootstrap complete — admin@crm.local / admin123")
