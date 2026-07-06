//! Container-based integration tests for SpacetimeCRM STDB module.
//!
//! These tests connect to a real running STDB instance via its HTTP API
//! using `curl` (via std::process::Command) to avoid heavy Rust deps.
//!
//! Gated behind `STDB_RUN_CONTAINER_TESTS=1` env var.
//!
//! Usage:
//!   STDB_RUN_CONTAINER_TESTS=1 \
//!     STDB_CONTAINER_URL=http://localhost:3002 \
//!     STDB_CONTAINER_DB=spacetime-crm-test \
//!     cargo test container_ -- --test-threads=1

#[cfg(test)]
mod tests {
    use std::env;
    use std::process::Command;
    use std::str;

    fn stdb_url() -> String {
        env::var("STDB_CONTAINER_URL")
            .unwrap_or_else(|_| "http://localhost:3002".to_string())
    }

    fn stdb_db() -> String {
        env::var("STDB_CONTAINER_DB")
            .unwrap_or_else(|_| "spacetime-crm-test".to_string())
    }

    fn sql_url() -> String {
        format!("{}/v1/database/{}/sql", stdb_url(), stdb_db())
    }

    fn call_url() -> String {
        format!("{}/v1/database/{}/call", stdb_url(), stdb_db())
    }

    fn run_curl(method: &str, url: &str, data: Option<&str>) -> String {
        let mut cmd = Command::new("curl");
        cmd.arg("-sSf");
        cmd.arg("-X").arg(method);
        cmd.arg("--max-time").arg("15");
        if let Some(body) = data {
            cmd.arg("-d").arg(body);
            cmd.arg("-H").arg("Content-Type: application/sql");
        }
        cmd.arg(url);

        let output = cmd.output().unwrap_or_else(|e| {
            panic!("curl failed (is curl installed?): {e}")
        });
        assert!(output.status.success(),
            "curl {} {} failed: stderr={}",
            method, url,
            str::from_utf8(&output.stderr).unwrap_or("(non-utf8)"));
        str::from_utf8(&output.stdout)
            .unwrap_or_else(|e| panic!("curl output not UTF-8: {e}"))
            .to_string()
    }

    fn run_sql(query: &str) -> String {
        run_curl("POST", &sql_url(), Some(query))
    }

    fn call_reducer(reducer: &str, args_json: &str) -> String {
        run_curl("POST", &format!("{}/{}", call_url(), reducer), Some(args_json))
    }

    fn should_run() -> bool {
        env::var("STDB_RUN_CONTAINER_TESTS").is_ok()
    }

    // ── Connection & Module Health ─────────────────────────────────

    #[test]
    fn container_stdb_is_reachable() {
        if !should_run() { /* skip */ return; }
        let _ = run_curl("GET", &stdb_url(), None);
        // If we get here without panic, STDB is reachable
    }

    #[test]
    fn container_module_is_published() {
        if !should_run() { /* skip */ return; }
        let out = run_sql("SELECT count(*) AS cnt FROM customer");
        assert!(out.contains("cnt") || out.contains("rows"),
            "Expected customer table to exist, got: {:.200}", out);
    }

    #[test]
    fn container_list_tables() {
        if !should_run() { /* skip */ return; }
        for tbl in &["customer", "ticket", "invoice", "payment",
                     "appointment", "user", "products", "tenant", "audit_log"] {
            let out = run_sql(&format!("SELECT count(*) AS cnt FROM {tbl}"));
            assert!(out.contains("cnt") || out.contains("rows"),
                "Table '{tbl}' should exist, got: {:.200}", out);
        }
    }

    // ── Customer CRUD ──────────────────────────────────────────────

    #[test]
    fn container_create_customer() {
        if !should_run() { /* skip */ return; }
        let _ = call_reducer("create_customer",
            r#"["tenant_ct","Container","Test","container@test.com","555-9999"]"#);

        let out = run_sql(
            "SELECT first_name, tenant_id FROM customer WHERE email = 'container@test.com'");
        assert!(out.contains("Container"), "Customer should exist, got: {:.200}", out);
        assert!(out.contains("tenant_ct"), "Wrong tenant, got: {:.200}", out);
    }

    // ── Ticket CRUD ────────────────────────────────────────────────

    #[test]
    fn container_create_ticket() {
        if !should_run() { /* skip */ return; }
        let _ = call_reducer("create_ticket",
            r#"["tenant_tk","cust_tk1","Broken screen - container","Cracked glass","iPhone","15","SN001","high"]"#);

        let out = run_sql(
            "SELECT status, priority FROM ticket WHERE title = 'Broken screen - container'");
        assert!(out.contains("new"), "Status should be 'new', got: {:.200}", out);
        assert!(out.contains("high"), "Priority should be 'high', got: {:.200}", out);
    }

    #[test]
    fn container_update_ticket_status() {
        if !should_run() { /* skip */ return; }
        let _ = call_reducer("create_ticket",
            r#"["t_upd","c_upd","Status update test","","","","","low"]"#);

        // Get ticket id
        let out = run_sql("SELECT id FROM ticket WHERE title = 'Status update test'");
        // We need to extract the ID — parse the JSON response
        let id = extract_id_from_sql_output(&out);
        assert!(!id.is_empty(), "Could not find ticket ID in: {:.200}", out);

        let _ = call_reducer("update_ticket_status",
            &format!(r#"["{}","in_progress"]"#, id));

        let out = run_sql(&format!(
            "SELECT status FROM ticket WHERE id = '{}'", id));
        assert!(out.contains("in_progress"),
            "Status should be 'in_progress', got: {:.200}", out);
    }

    fn extract_id_from_sql_output(output: &str) -> String {
        // STDB SQL returns JSON like: [{"rows":[["tkt_xxx"]],"schema":{...}}]
        // Try to parse with basic string find
        if let Some(start) = output.find("\"rows\":[[\"") {
            let rest = &output[start + 9..]; // skip "rows":[["
            if let Some(end) = rest.find('\"') {
                return rest[..end].to_string();
            }
        }
        // Fallback: look for "tkt_" pattern
        if let Some(start) = output.find("tkt_") {
            let rest = &output[start..];
            let mut id = String::new();
            for c in rest.chars() {
                if c.is_alphanumeric() || c == '_' { id.push(c); } else { break; }
            }
            return id;
        }
        String::new()
    }

    // ── Invoice CRUD ───────────────────────────────────────────────

    #[test]
    fn container_create_invoice() {
        if !should_run() { /* skip */ return; }
        let _ = call_reducer("create_invoice",
            r#"["tenant_inv","cust_inv1","","Container invoice test","Net 30",1710000000000,"USD"]"#);

        let out = run_sql(
            "SELECT status, currency FROM invoice WHERE notes = 'Container invoice test'");
        assert!(out.contains("draft"), "Status should be 'draft', got: {:.200}", out);
        assert!(out.contains("USD"), "Currency should be USD, got: {:.200}", out);
    }

    // ── Payment CRUD ───────────────────────────────────────────────

    #[test]
    fn container_record_payment() {
        if !should_run() { /* skip */ return; }
        let _ = call_reducer("record_payment",
            r#"["tenant_pay","inv_pay1","cust_pay1",150.0,"cash","REF-001","Walk-in payment","USD"]"#);

        let out = run_sql(
            "SELECT amount, method FROM payment WHERE reference = 'REF-001'");
        assert!(out.contains("150"), "Amount should be 150, got: {:.200}", out);
        assert!(out.contains("cash"), "Method should be 'cash', got: {:.200}", out);
    }

    // ── User CRUD ──────────────────────────────────────────────────

    #[test]
    fn container_create_user() {
        if !should_run() { /* skip */ return; }
        let _ = call_reducer("create_user",
            r#"["container_user","container@user.com","tech"]"#);

        let out = run_sql(
            "SELECT name, role, active FROM user WHERE email = 'container@user.com'");
        assert!(out.contains("container_user"), "User should exist, got: {:.200}", out);
        assert!(out.contains("tech"), "Role should be 'tech', got: {:.200}", out);
        assert!(out.contains("true") || out.contains("1"),
            "User should be active, got: {:.200}", out);
    }

    // ── Tenant CRUD ────────────────────────────────────────────────

    #[test]
    fn container_create_tenant() {
        if !should_run() { /* skip */ return; }
        let _ = call_reducer("create_tenant",
            r#"["Container Shop","container-shop"]"#);

        let out = run_sql(
            "SELECT name FROM tenant WHERE slug = 'container-shop'");
        assert!(out.contains("Container Shop"), "Tenant should exist, got: {:.200}", out);
    }

    // ── Appointment CRUD ───────────────────────────────────────────

    #[test]
    fn container_create_appointment() {
        if !should_run() { /* skip */ return; }
        let _ = call_reducer("create_appointment",
            r#"["tenant_appt","cust_appt1","","Screen repair - container",
               "Replace cracked screen",1700000000000,1700003600000,false,"",""]"#);

        let out = run_sql(
            "SELECT status FROM appointment WHERE title = 'Screen repair - container'");
        assert!(out.contains("scheduled"),
            "Status should be 'scheduled', got: {:.200}", out);
    }
}
