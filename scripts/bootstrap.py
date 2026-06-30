#!/usr/bin/env python3
"""Bootstrap spacetime-crm: create admin user, tenant, password, then seed demo data."""
import httpx
import bcrypt
import time

STDB = "http://localhost:3001"
BASE = "http://localhost:8723"

C = httpx.Client(base_url=STDB, timeout=15)

# Wait for STDB
for i in range(10):
    try:
        r = C.get("/health")
        if r.status_code == 200:
            break
    except:
        pass
    time.sleep(1)

# 1. Create default tenant
r = C.post("/v1/database/spacetime-crm/call/create_tenant", json=["Default Corp", "default"])
print(f"  Tenant created: HTTP {r.status_code}")

# 2. Create admin user via reducer
r = C.post("/v1/database/spacetime-crm/call/create_user", json=["admin", "admin@crm.local", "admin"])
print(f"  User created: HTTP {r.status_code}")

# 3. Find user ID
r = C.post("/v1/database/spacetime-crm/sql", content="SELECT * FROM user WHERE email = 'admin@crm.local'", headers={"Content-Type": "text/plain"})
users = r.json()
if users and users[0]["rows"]:
    uid = users[0]["rows"][0][0]
    username = users[0]["rows"][0][1]
    print(f"  User ID: {uid}, username: {username}")
    # 4. Set password
    hashed = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
    r = C.post(f"/v1/database/spacetime-crm/call/set_user_password", json=[uid, hashed])
    print(f"  Password set: HTTP {r.status_code}")
else:
    print("  ERROR: User not found!")
    exit(1)

# 5. Find tenant ID
r = C.post("/v1/database/spacetime-crm/sql", content="SELECT * FROM tenants WHERE slug = 'default'", headers={"Content-Type": "text/plain"})
tenants = r.json()
if tenants and tenants[0]["rows"]:
    tid = tenants[0]["rows"][0][0]
    print(f"  Tenant ID: {tid}")
    # 6. Add admin as tenant member
    r = C.post("/v1/database/spacetime-crm/call/add_tenant_member", json=[tid, username, "admin"])
    print(f"  Member added: HTTP {r.status_code}")
else:
    print("  ERROR: Tenant not found!")
    exit(1)

# 7. Verify login via API
C2 = httpx.Client(base_url=BASE, timeout=15)
r = C2.post("/api/auth/login", json={"email": "admin@crm.local", "password": "admin123"})
if r.status_code == 200:
    data = r.json()
    print(f"  ✅ Login OK, token: {data['token'][:30]}...")
    print(f"     tenant_id: {data.get('user', data).get('tenant_id', 'N/A')}")
else:
    print(f"  ❌ Login failed: {r.status_code} {r.text}")
    exit(1)

print("\n✅ Bootstrap complete — admin@crm.local / admin123")
