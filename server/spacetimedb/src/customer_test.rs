use spacetimedb::*;

#[cfg(test)]
mod tests {
    use crate::customer::customer;
    use crate::*;

    /// Helper to create a test ReducerContext.
    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    /// Test that create_customer inserts a row with correct fields.
    #[test]
    fn test_create_customer() {
        let ctx = test_ctx();
        create_customer(
            &ctx,
            "tenant_test".into(),
            "Alice".into(),
            "Smith".into(),
            "alice@test.com".into(),
            "555-0101".into(),
        );

        let customers: Vec<Customer> = ctx.db.customer().iter().collect();
        assert_eq!(customers.len(), 1);
        let c = &customers[0];
        assert!(c.id.starts_with("cust_"));
        assert_eq!(c.tenant_id, "tenant_test");
        assert_eq!(c.first_name, "Alice");
        assert_eq!(c.last_name, "Smith");
        assert_eq!(c.email, "alice@test.com");
        assert_eq!(c.phone, "555-0101");
        assert!(c.created_at > 0);
        assert_eq!(c.created_at, c.updated_at);
    }

    /// Test that update_customer modifies fields but preserves others.
    #[test]
    fn test_update_customer() {
        let ctx = test_ctx();
        create_customer(
            &ctx,
            "tenant_test".into(),
            "Bob".into(),
            "Jones".into(),
            "bob@test.com".into(),
            "555-0102".into(),
        );

        let c = ctx
            .db
            .customer()
            .iter()
            .next()
            .expect("expected at least one customer record");
        let original_id = c.id.clone();
        let original_created = c.created_at;

        update_customer(
            &ctx,
            original_id.clone(),
            "Robert".into(),
            "Jones".into(),
            "robert@test.com".into(),
            "555-0199".into(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
        );

        let updated = ctx
            .db
            .customer()
            .id()
            .find(&original_id)
            .expect("expected record to exist");
        assert_eq!(updated.first_name, "Robert");
        assert_eq!(updated.email, "robert@test.com");
        assert_eq!(updated.phone, "555-0199");
        assert_eq!(updated.id, original_id);
        assert_eq!(updated.created_at, original_created);
        assert!(updated.updated_at >= original_created);
        assert_eq!(updated.last_name, "Jones");
    }

    /// Test that delete_customer actually removes the row.
    #[test]
    fn test_delete_customer() {
        let ctx = test_ctx();
        create_customer(
            &ctx,
            "tenant_test".into(),
            "Carol".into(),
            "White".into(),
            "carol@test.com".into(),
            "555-0103".into(),
        );

        let c = ctx
            .db
            .customer()
            .iter()
            .next()
            .expect("expected at least one customer record");
        delete_customer(&ctx, c.id.clone());
        assert_eq!(ctx.db.customer().iter().count(), 0);
    }

    /// Test that set_customer_password updates the password hash.
    #[test]
    fn test_set_customer_password() {
        let ctx = test_ctx();
        create_customer(
            &ctx,
            "tenant_test".into(),
            "Dave".into(),
            "Black".into(),
            "dave@test.com".into(),
            "555-0104".into(),
        );

        let c = ctx
            .db
            .customer()
            .iter()
            .next()
            .expect("expected at least one customer record");
        assert!(c.portal_password_hash.is_empty());

        let hash = "bcrypt_hash_here".to_string();
        set_customer_password(&ctx, c.id.clone(), hash.clone());

        let updated = ctx
            .db
            .customer()
            .id()
            .find(&c.id)
            .expect("expected record to exist");
        assert_eq!(updated.portal_password_hash, hash);
    }

    /// Test that deleting a nonexistent customer doesn't panic.
    #[test]
    fn test_delete_nonexistent_customer() {
        let ctx = test_ctx();
        delete_customer(&ctx, "cust_nonexistent".into());
        assert_eq!(ctx.db.customer().iter().count(), 0);
    }

    /// Test that updating a nonexistent customer doesn't panic.
    #[test]
    fn test_update_nonexistent_customer() {
        let ctx = test_ctx();
        update_customer(
            &ctx,
            "cust_nonexistent".into(),
            "Nope".into(),
            "Nada".into(),
            "nope@test.com".into(),
            "555-0000".into(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
            String::new(),
        );
        assert_eq!(ctx.db.customer().iter().count(), 0);
    }

    /// Test customer isolation: two tenants' customers shouldn't mix.
    #[test]
    fn test_tenant_isolation() {
        let ctx = test_ctx();
        create_customer(
            &ctx,
            "tenant_a".into(),
            "Alice".into(),
            "A".into(),
            "alice@a.com".into(),
            "555-1001".into(),
        );
        create_customer(
            &ctx,
            "tenant_b".into(),
            "Bob".into(),
            "B".into(),
            "bob@b.com".into(),
            "555-1002".into(),
        );

        let tenants: Vec<String> = ctx
            .db
            .customer()
            .iter()
            .map(|c| c.tenant_id.clone())
            .collect();
        assert_eq!(tenants.len(), 2);
        assert!(tenants.contains(&"tenant_a".to_string()));
        assert!(tenants.contains(&"tenant_b".to_string()));

        let tenant_a_only: Vec<Customer> = ctx
            .db
            .customer()
            .iter()
            .filter(|c| c.tenant_id == "tenant_a")
            .collect();
        assert_eq!(tenant_a_only.len(), 1);
        assert_eq!(tenant_a_only[0].email, "alice@a.com");
    }
}
