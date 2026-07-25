use spacetimedb::*;

#[cfg(test)]
mod tests {
    use crate::customer::customer;
    use crate::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
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
            "imported@test.com".into(),
            "555-0001".into(),
            "555-0002".into(),
            "123 Main St".into(),
            "".into(),
            "Portland".into(),
            "OR".into(),
            "97201".into(),
            "Acme Corp".into(),
            "Bulk import".into(),
            "".into(),
            1000000000000,
            1000000000000,
        );
        let customers: Vec<Customer> = ctx.db.customer().iter().collect();
        assert_eq!(customers.len(), 1);
        let c = &customers[0];
        assert_eq!(c.id, "cust_imported_1");
        assert_eq!(c.first_name, "Imported");
        assert_eq!(c.created_at, 1000000000000);
        assert_eq!(c.updated_at, 1000000000000);
        assert_eq!(c.company, "Acme Corp");
        assert_eq!(c.city, "Portland");
    }
}
