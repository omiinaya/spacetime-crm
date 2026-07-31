
#[cfg(test)]
mod tests {
    use crate::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_log_audit() {
        let ctx = test_ctx();
        log_audit(
            &ctx,
            "t_aud".into(),
            "user_1".into(),
            "Alice".into(),
            "created".into(),
            "customer".into(),
            "cust_1".into(),
            r#"{"name":"Alice"}"#.into(),
        );
        let logs: Vec<AuditLog> = ctx.db.audit_log().iter().collect();
        assert_eq!(logs.len(), 1);
        let l = &logs[0];
        assert!(l.id.starts_with("aud_"));
        assert_eq!(l.action, "created");
        assert_eq!(l.entity, "customer");
        assert_eq!(l.user_name, "Alice");
    }
}
