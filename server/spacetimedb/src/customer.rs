// TODO (kanban): Replace 6 unwrap() call(s) with proper error handling
use spacetimedb::*;

#[spacetimedb::table(accessor = customer, public)]
#[derive(Debug, Clone)]
pub struct Customer {
    #[primary_key]
    pub id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub first_name: String,
    pub last_name: String,
    pub email: String,
    pub phone: String,
    pub mobile: String,
    pub address_line1: String,
    pub address_line2: String,
    pub city: String,
    pub state: String,
    pub zip: String,
    pub company: String,
    pub notes: String,
    pub tags: String,
    pub portal_password_hash: String,
    pub created_at: u64,
    pub updated_at: u64,
}

#[spacetimedb::reducer]
pub fn create_customer(
    ctx: &ReducerContext,
    tenant_id: String,
    first_name: String,
    last_name: String,
    email: String,
    phone: String,
) {
    let id = super::make_id("cust", ctx);
    let now = super::now_ms(ctx);
    ctx.db.customer().insert(Customer {
        id,
        tenant_id,
        first_name,
        last_name,
        email,
        phone,
        mobile: String::new(),
        address_line1: String::new(),
        address_line2: String::new(),
        city: String::new(),
        state: String::new(),
        zip: String::new(),
        company: String::new(),
        notes: String::new(),
        tags: String::new(),
        portal_password_hash: String::new(),
        created_at: now,
        updated_at: now,
    });
}

#[spacetimedb::reducer]
pub fn update_customer(
    ctx: &ReducerContext,
    id: String,
    first_name: String,
    last_name: String,
    email: String,
    phone: String,
    mobile: String,
    address_line1: String,
    address_line2: String,
    city: String,
    state: String,
    zip: String,
    company: String,
    notes: String,
    tags: String,
) {
    if let Some(c) = ctx.db.customer().id().find(&id) {
        ctx.db.customer().id().update(Customer {
            first_name,
            last_name,
            email,
            phone,
            mobile,
            address_line1,
            address_line2,
            city,
            state,
            zip,
            company,
            notes,
            tags,
            updated_at: super::now_ms(ctx),
            ..c
        });
    }
}

#[spacetimedb::reducer]
pub fn set_customer_password(ctx: &ReducerContext, id: String, password_hash: String) {
    if let Some(c) = ctx.db.customer().id().find(&id) {
        ctx.db.customer().id().update(Customer {
            portal_password_hash: password_hash,
            ..c
        });
    }
}

#[spacetimedb::reducer]
pub fn delete_customer(ctx: &ReducerContext, id: String) {
    ctx.db.customer().id().delete(&id);
}

#[spacetimedb::reducer]
pub fn import_customer(
    ctx: &ReducerContext,
    tenant_id: String,
    id: String,
    first_name: String,
    last_name: String,
    email: String,
    phone: String,
    mobile: String,
    address_line1: String,
    address_line2: String,
    city: String,
    state: String,
    zip: String,
    company: String,
    notes: String,
    tags: String,
    created_at: u64,
    updated_at: u64,
) {
    ctx.db.customer().insert(Customer {
        id,
        tenant_id,
        first_name,
        last_name,
        email,
        phone,
        mobile,
        address_line1,
        address_line2,
        city,
        state,
        zip,
        company,
        notes,
        tags,
        portal_password_hash: String::new(),
        created_at,
        updated_at,
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_create_customer() {
        let ctx = test_ctx();
        create_customer(
            &ctx,
            "tenant_t".into(),
            "Alice".into(),
            "Smith".into(),
            "alice@test.com".into(),
            "555-0101".into(),
        );
        let customers: Vec<Customer> = ctx.db.customer().iter().collect();
        assert_eq!(customers.len(), 1);
        let c = &customers[0];
        assert!(c.id.starts_with("cust_"));
        assert_eq!(c.tenant_id, "tenant_t");
        assert_eq!(c.first_name, "Alice");
        assert_eq!(c.last_name, "Smith");
        assert_eq!(c.email, "alice@test.com");
        assert_eq!(c.phone, "555-0101");
        assert!(c.created_at > 0);
        assert_eq!(c.created_at, c.updated_at);
        assert!(c.portal_password_hash.is_empty());
    }

    #[test]
    fn test_update_customer() {
        let ctx = test_ctx();
        create_customer(
            &ctx,
            "t".into(),
            "Bob".into(),
            "Jones".into(),
            "bob@test.com".into(),
            "555-0102".into(),
        );
        let c = ctx.db.customer().iter().next().unwrap();
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
        let updated = ctx.db.customer().id().find(&original_id).unwrap();
        assert_eq!(updated.first_name, "Robert");
        assert_eq!(updated.email, "robert@test.com");
        assert_eq!(updated.id, original_id);
        assert_eq!(updated.created_at, original_created);
        assert!(updated.updated_at >= original_created);
    }

    #[test]
    fn test_update_nonexistent_customer() {
        let ctx = test_ctx();
        update_customer(
            &ctx,
            "cust_nonexistent".into(),
            "N".into(),
            "N".into(),
            "n@t.com".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
            "".into(),
        );
        assert_eq!(ctx.db.customer().iter().count(), 0);
    }

    #[test]
    fn test_set_customer_password() {
        let ctx = test_ctx();
        create_customer(
            &ctx,
            "t".into(),
            "Dave".into(),
            "B".into(),
            "dave@test.com".into(),
            "555-0104".into(),
        );
        let c = ctx.db.customer().iter().next().unwrap();
        assert!(c.portal_password_hash.is_empty());
        let hash = "bcrypt_hash_here".to_string();
        set_customer_password(&ctx, c.id.clone(), hash.clone());
        let updated = ctx.db.customer().id().find(&c.id).unwrap();
        assert_eq!(updated.portal_password_hash, hash);
    }

    #[test]
    fn test_set_customer_password_nonexistent() {
        let ctx = test_ctx();
        set_customer_password(&ctx, "cust_nonexistent".into(), "hash".into());
        assert_eq!(ctx.db.customer().iter().count(), 0);
    }

    #[test]
    fn test_delete_customer() {
        let ctx = test_ctx();
        create_customer(
            &ctx,
            "t".into(),
            "Carol".into(),
            "W".into(),
            "c@test.com".into(),
            "555-0103".into(),
        );
        assert_eq!(ctx.db.customer().iter().count(), 1);
        let c = ctx.db.customer().iter().next().unwrap();
        delete_customer(&ctx, c.id.clone());
        assert_eq!(ctx.db.customer().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent_customer() {
        let ctx = test_ctx();
        delete_customer(&ctx, "cust_nonexistent".into());
        assert_eq!(ctx.db.customer().iter().count(), 0);
    }

    #[test]
    fn test_import_customer() {
        let ctx = test_ctx();
        import_customer(
            &ctx,
            "t_imp".into(),
            "cust_imported_1".into(),
            "Imported".into(),
            "User".into(),
            "imp@test.com".into(),
            "555-0001".into(),
            "555-0002".into(),
            "123 Main St".into(),
            "".into(),
            "Portland".into(),
            "OR".into(),
            "97201".into(),
            "Acme Corp".into(),
            "Bulk".into(),
            "".into(),
            1000000000000,
            1000000000000,
        );
        let c = ctx.db.customer().iter().next().unwrap();
        assert_eq!(c.id, "cust_imported_1");
        assert_eq!(c.first_name, "Imported");
        assert_eq!(c.created_at, 1000000000000);
        assert_eq!(c.updated_at, 1000000000000);
        assert_eq!(c.company, "Acme Corp");
        assert_eq!(c.city, "Portland");
    }

    #[test]
    fn test_tenant_isolation() {
        let ctx = test_ctx();
        create_customer(
            &ctx,
            "t_a".into(),
            "Alice".into(),
            "A".into(),
            "a@a.com".into(),
            "555-1".into(),
        );
        create_customer(
            &ctx,
            "t_b".into(),
            "Bob".into(),
            "B".into(),
            "b@b.com".into(),
            "555-2".into(),
        );
        assert_eq!(ctx.db.customer().iter().count(), 2);
        let a_only: Vec<Customer> = ctx
            .db
            .customer()
            .iter()
            .filter(|c| c.tenant_id == "t_a")
            .collect();
        assert_eq!(a_only.len(), 1);
        assert_eq!(a_only[0].email, "a@a.com");
    }
}
