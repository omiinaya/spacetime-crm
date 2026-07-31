//! Container-based integration tests for SpacetimeCRM STDB module.
//!
//! These tests connect to a real running STDB instance via its HTTP API
//! using curl (via std::process::Command) — no SpacetimeDB deps needed.
//!
//! Usage:
//!   STDB_CONTAINER_URL=http://localhost:3002 \
//!     STDB_CONTAINER_DB=spacetime-crm \
//!     cargo run -p container-tests
//!
//! Or via the runner script:
//!   scripts/run-integration-tests.sh

use std::env;
use std::process::Command;
use std::str;

fn stdb_url() -> String {
    env::var("STDB_CONTAINER_URL")
        .unwrap_or_else(|_| "http://localhost:3002".to_string())
}

fn stdb_db() -> String {
    env::var("STDB_CONTAINER_DB")
        .unwrap_or_else(|_| "spacetime-crm".to_string())
}

fn sql_url() -> String {
    format!("{}/v1/database/{}/sql", stdb_url(), stdb_db())
}

fn call_url() -> String {
    format!("{}/v1/database/{}/call", stdb_url(), stdb_db())
}

fn run_curl(method: &str, url: &str, data: Option<&str>, content_type: &str) -> Result<String, String> {
    let mut cmd = Command::new("curl");
    cmd.arg("-sSf");
    cmd.arg("-X").arg(method);
    cmd.arg("--max-time").arg("15");
    if let Some(body) = data {
        cmd.arg("-d").arg(body);
        cmd.arg("-H").arg(format!("Content-Type: {content_type}"));
    }
    cmd.arg(url);

    let output = cmd.output().map_err(|e| format!("curl failed: {e}"))?;
    if !output.status.success() {
        let stderr = str::from_utf8(&output.stderr).unwrap_or("(non-utf8)");
        return Err(format!("curl {} {} failed: {stderr}", method, url));
    }
    str::from_utf8(&output.stdout)
        .map(|s| s.to_string())
        .map_err(|e| format!("curl output not UTF-8: {e}"))
}

fn run_sql(query: &str) -> Result<String, String> {
    run_curl("POST", &sql_url(), Some(query), "application/sql")
}

fn call_reducer(reducer: &str, args_json: &str) -> Result<String, String> {
    // /call endpoints take JSON-encoded reducer args (Content-Type:
    // application/json) — application/sql yields HTTP 415.
    run_curl(
        "POST",
        &format!("{}/{}", call_url(), reducer),
        Some(args_json),
        "application/json",
    )
}

// ── Test helpers ──────────────────────────────────────────────────

fn assert_sql_contains(query: &str, expected: &str, label: &str) -> Result<(), String> {
    let out = run_sql(query)?;
    if out.contains(expected) {
        Ok(())
    } else {
        Err(format!("FAIL [{label}]: expected '{expected}' in output: {:.200}", out))
    }
}

// ── Connection & Module Health ────────────────────────────────────

fn test_stdb_is_reachable() -> Result<(), String> {
    // STDB v2.6.1 serves /v1/health (bare / returns 404).
    let _ = run_curl("GET", &format!("{}/v1/health", stdb_url()), None, "application/json")?;
    Ok(())
}

fn test_module_is_published() -> Result<(), String> {
    let out = run_sql("SELECT count(*) AS cnt FROM customer")?;
    if out.contains("cnt") || out.contains("rows") {
        Ok(())
    } else {
        Err(format!("customer table not found: {:.200}", out))
    }
}

fn test_list_tables() -> Result<(), String> {
    for tbl in &[
        "customer", "ticket", "invoices", "payment",
        "appointment", "user", "products", "tenants", "audit_log",
    ] {
        let out = run_sql(&format!("SELECT count(*) AS cnt FROM {tbl}"))?;
        if !out.contains("cnt") && !out.contains("rows") {
            return Err(format!("Table '{tbl}' not found: {:.200}", out));
        }
    }
    Ok(())
}

// ── Customer CRUD ─────────────────────────────────────────────────

fn test_create_customer() -> Result<(), String> {
    let _ = call_reducer(
        "create_customer",
        r#"["tenant_ct","Container","Test","container@test.com","555-9999"]"#,
    )?;
    assert_sql_contains(
        "SELECT first_name, tenant_id FROM customer WHERE email = 'container@test.com'",
        "Container",
        "create_customer",
    )?;
    assert_sql_contains(
        "SELECT first_name, tenant_id FROM customer WHERE email = 'container@test.com'",
        "tenant_ct",
        "create_customer tenant",
    )?;
    Ok(())
}

// ── Ticket CRUD ───────────────────────────────────────────────────

fn test_create_ticket() -> Result<(), String> {
    let _ = call_reducer(
        "create_ticket",
        r#"["tenant_tk","cust_tk1","Broken screen","Cracked glass","iPhone","15","SN001","high"]"#,
    )?;
    assert_sql_contains(
        "SELECT status, priority FROM ticket WHERE title = 'Broken screen'",
        "new",
        "create_ticket status",
    )?;
    assert_sql_contains(
        "SELECT status, priority FROM ticket WHERE title = 'Broken screen'",
        "high",
        "create_ticket priority",
    )?;
    Ok(())
}

fn test_update_ticket_status() -> Result<(), String> {
    let _ = call_reducer(
        "create_ticket",
        r#"["t_upd","c_upd","Status test","","","","","low"]"#,
    )?;
    let out = run_sql("SELECT id FROM ticket WHERE title = 'Status test'")?;
    let id = extract_id_from_output(&out);
    if id.is_empty() {
        return Err(format!("Could not find ticket id in: {:.200}", out));
    }
    let _ = call_reducer("update_ticket_status", &format!(
        r#"["{}","in_progress"]"#, id
    ))?;
    assert_sql_contains(
        &format!("SELECT status FROM ticket WHERE id = '{}'", id),
        "in_progress",
        "update_ticket_status",
    )?;
    Ok(())
}

fn extract_id_from_output(output: &str) -> String {
    let trimmed = output.trim();
    if let Some(start) = trimmed.find("\"rows\":[[\"") {
        let rest = &trimmed[start + 10..];
        if let Some(end) = rest.find('\"') {
            return rest[..end].to_string();
        }
    }
    if let Some(start) = trimmed.find("tkt_") {
        let rest = &trimmed[start..];
        return rest.chars().take_while(|c| c.is_alphanumeric() || *c == '_').collect();
    }
    String::new()
}

// ── Invoice CRUD ──────────────────────────────────────────────────

fn test_create_invoice() -> Result<(), String> {
    let _ = call_reducer(
        "create_invoice",
        r#"["tenant_inv","cust_inv1","","Container invoice","Net 30",1710000000000,"USD"]"#,
    )?;
    assert_sql_contains(
        "SELECT status, currency FROM invoices WHERE notes = 'Container invoice'",
        "draft",
        "create_invoice status",
    )?;
    assert_sql_contains(
        "SELECT status, currency FROM invoices WHERE notes = 'Container invoice'",
        "USD",
        "create_invoice currency",
    )?;
    Ok(())
}

// ── Payment CRUD ──────────────────────────────────────────────────

fn test_record_payment() -> Result<(), String> {
    let _ = call_reducer(
        "record_payment",
        r#"["tenant_pay","inv_pay1","cust_pay1",150.0,"cash","REF-001","Walk-in payment","USD"]"#,
    )?;
    assert_sql_contains(
        "SELECT amount, method FROM payment WHERE reference = 'REF-001'",
        "150",
        "record_payment amount",
    )?;
    assert_sql_contains(
        "SELECT amount, method FROM payment WHERE reference = 'REF-001'",
        "cash",
        "record_payment method",
    )?;
    Ok(())
}

// ── User CRUD ─────────────────────────────────────────────────────

fn test_create_user() -> Result<(), String> {
    let _ = call_reducer(
        "create_user",
        r#"["container_user","container@user.com","tech"]"#,
    )?;
    assert_sql_contains(
        "SELECT name, role, active FROM user WHERE email = 'container@user.com'",
        "container_user",
        "create_user name",
    )?;
    assert_sql_contains(
        "SELECT name, role, active FROM user WHERE email = 'container@user.com'",
        "tech",
        "create_user role",
    )?;
    Ok(())
}

// ── Tenant CRUD ───────────────────────────────────────────────────

fn test_create_tenant() -> Result<(), String> {
    let _ = call_reducer("create_tenant", r#"["Container Shop","container-shop"]"#)?;
    assert_sql_contains(
        "SELECT name FROM tenants WHERE slug = 'container-shop'",
        "Container Shop",
        "create_tenant",
    )?;
    Ok(())
}

// ── Appointment CRUD ──────────────────────────────────────────────

fn test_create_appointment() -> Result<(), String> {
    let _ = call_reducer(
        "create_appointment",
        r#"["tenant_appt","cust_appt1","","Screen repair","Replace cracked screen",1700000000000,1700003600000,false,"","",""]"#,
    )?;
    assert_sql_contains(
        "SELECT status FROM appointment WHERE title = 'Screen repair'",
        "scheduled",
        "create_appointment status",
    )?;
    Ok(())
}

// ── Main runner ───────────────────────────────────────────────────

type TestFn = fn() -> Result<(), String>;

struct TestCase {
    name: &'static str,
    func: TestFn,
}

const TESTS: &[TestCase] = &[
    TestCase { name: "STDB reachable", func: test_stdb_is_reachable },
    TestCase { name: "Module published (customer table)", func: test_module_is_published },
    TestCase { name: "All tables present", func: test_list_tables },
    TestCase { name: "Create customer", func: test_create_customer },
    TestCase { name: "Create ticket", func: test_create_ticket },
    TestCase { name: "Update ticket status", func: test_update_ticket_status },
    TestCase { name: "Create invoice", func: test_create_invoice },
    TestCase { name: "Record payment", func: test_record_payment },
    TestCase { name: "Create user", func: test_create_user },
    TestCase { name: "Create tenant", func: test_create_tenant },
    TestCase { name: "Create appointment", func: test_create_appointment },
];

fn main() {
    let total = TESTS.len();
    let mut passed = 0;
    let mut failed = 0;

    println!("══════════════════════════════════════════════");
    println!("  Container Integration Tests");
    println!("  Target: {}/v1/database/{}", stdb_url(), stdb_db());
    println!("══════════════════════════════════════════════");

    for test in TESTS {
        print!("  {:.<55} ", test.name);
        match (test.func)() {
            Ok(()) => {
                println!("PASS");
                passed += 1;
            }
            Err(msg) => {
                println!("FAIL");
                eprintln!("    {}", msg);
                failed += 1;
            }
        }
    }

    println!("══════════════════════════════════════════════");
    println!("  Results: {passed}/{total} passed, {failed}/{total} failed");
    if failed > 0 {
        std::process::exit(1);
    }
}
