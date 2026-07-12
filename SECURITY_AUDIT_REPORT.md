# SECURITY AUDIT REPORT
Generated: 2026-07-12T03:26:44.285912

## SAST Baseline (Bandit)

- Total production findings: 123
- HIGH severity: 0
- MEDIUM severity: 115
- LOW severity: 8

### Production Findings by Type
- B608 (SQL Injection (string-based query construction)): 114 occurrences
- B110 (Try/Except/Pass): 7 occurrences
- B105 (Hardcoded password): 1 occurrences
- B104 (Binding to all interfaces): 1 occurrences

## Triaged Findings

### FIXED (0 HIGH + 3 MEDIUM)
- B701: Jinja2 autoescape=False → True (server/helpers.py:29)
- B608: SQL injection via unsanitized invoice_id (server/routes/invoices.py:208)
- B608: SQL injection via unsanitized customer_id (server/routes/appointments.py:197,220)

### FALSE POSITIVES (Documented)
The following B608 SQL injection alerts are false positives because the variables are either:
- Extracted from JWT user dict (trusted)
- Wrapped with _safe_id() or _sanitize_sql()
- From internally validated allowlists

- ~88 B608 findings in production use _safe_id wrapper (already protected)

### ACCEPTABLE RISK (WONTFIX)
- B104: Binding to 0.0.0.0 required for Docker deployment
- B110: Bare except blocks in auth.py (error handling for edge cases)
- B608: tenant_id from JWT is trusted (88+ occurrences)

## npm Audit (Frontend Dependencies)

- Total vulnerabilities: 5

- **@vitest/coverage-v8**: critical — vitest
  - Vulnerable: <=3.2.5
  - Fix: {'name': '@vitest/coverage-v8', 'version': '4.1.10', 'isSemVerMajor': True}
- **esbuild**: moderate — {'source': 1102341, 'name': 'esbuild', 'dependency': 'esbuild', 'title': 'esbuild enables any website to send any requests to the development server and read the response', 'url': 'https://github.com/advisories/GHSA-67mh-4wv8-2f99', 'severity': 'moderate', 'cwe': ['CWE-346'], 'cvss': {'score': 5.3, 'vectorString': 'CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:H/I:N/A:N'}, 'range': '<=0.24.2'}
  - Vulnerable: <=0.24.2
  - Fix: {'name': 'vitest', 'version': '4.1.10', 'isSemVerMajor': True}
- **vite**: high — {'source': 1116229, 'name': 'vite', 'dependency': 'vite', 'title': 'Vite Vulnerable to Path Traversal in Optimized Deps `.map` Handling', 'url': 'https://github.com/advisories/GHSA-4w7w-66w2-5vf9', 'severity': 'moderate', 'cwe': ['CWE-22', 'CWE-200'], 'cvss': {'score': 0, 'vectorString': None}, 'range': '<=6.4.1'}
  - Vulnerable: <=6.4.2
  - Fix: {'name': 'vitest', 'version': '4.1.10', 'isSemVerMajor': True}
- **vite-node**: moderate — vite
  - Vulnerable: <=2.2.0-beta.2
  - Fix: {'name': 'vitest', 'version': '4.1.10', 'isSemVerMajor': True}
- **vitest**: critical — {'source': 1120126, 'name': 'vitest', 'dependency': 'vitest', 'title': 'When Vitest UI server is listening, arbitrary file can be read and executed', 'url': 'https://github.com/advisories/GHSA-5xrq-8626-4rwp', 'severity': 'critical', 'cwe': ['CWE-862'], 'cvss': {'score': 9.8, 'vectorString': 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H'}, 'range': '<3.2.6'}
  - Vulnerable: <=3.2.5
  - Fix: {'name': 'vitest', 'version': '4.1.10', 'isSemVerMajor': True}

## Recommendations

1. **npm audit fix** for frontend dependency vulnerabilities
2. **Monitor bare except** blocks in auth.py (B110)
3. **Consider parameterized queries** for future SQL improvements
4. **Run bandit periodically** with: `bandit -r server/ --exclude .venv,tests/`
