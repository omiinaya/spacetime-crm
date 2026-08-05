use spacetimedb::*;

#[spacetimedb::table(accessor = customer_geolocations, public)]
#[derive(Debug, Clone)]
pub struct CustomerGeolocation {
    #[primary_key]
    pub customer_id: String,
    #[index(btree)]
    pub tenant_id: String,
    pub latitude: f64,
    pub longitude: f64,
    pub updated_at: u64,
}

#[spacetimedb::reducer]
pub fn set_customer_geolocation(
    ctx: &ReducerContext,
    tenant_id: String,
    customer_id: String,
    latitude: f64,
    longitude: f64,
) {
    let now = super::now_ms(ctx);
    // Upsert — insert or update
    if let Some(existing) = ctx
        .db
        .customer_geolocations()
        .customer_id()
        .find(&customer_id)
    {
        ctx.db
            .customer_geolocations()
            .customer_id()
            .update(CustomerGeolocation {
                tenant_id,
                latitude,
                longitude,
                updated_at: now,
                ..existing
            });
    } else {
        ctx.db.customer_geolocations().insert(CustomerGeolocation {
            customer_id,
            tenant_id,
            latitude,
            longitude,
            updated_at: now,
        });
    }
}

#[spacetimedb::reducer]
pub fn delete_customer_geolocation(ctx: &ReducerContext, customer_id: String) {
    ctx.db
        .customer_geolocations()
        .customer_id()
        .delete(&customer_id);
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_ctx() -> ReducerContext {
        ReducerContext::__dummy()
    }

    #[test]
    fn test_set_geolocation() {
        let ctx = test_ctx();
        set_customer_geolocation(&ctx, "t_geo".into(), "cust_1".into(), 40.7128, -74.0060);
        let geos: Vec<CustomerGeolocation> = ctx.db.customer_geolocations().iter().collect();
        assert_eq!(geos.len(), 1);
        let g = &geos[0];
        assert_eq!(g.customer_id, "cust_1");
        assert_eq!(g.tenant_id, "t_geo");
        assert!((g.latitude - 40.7128).abs() < 0.001);
        assert!((g.longitude - -74.0060).abs() < 0.001);
        assert!(g.updated_at > 0);
    }

    #[test]
    fn test_set_geolocation_upsert() {
        let ctx = test_ctx();
        set_customer_geolocation(&ctx, "t".into(), "cust_1".into(), 40.0, -74.0);
        assert_eq!(ctx.db.customer_geolocations().iter().count(), 1);
        let original_updated = ctx
            .db
            .customer_geolocations()
            .iter()
            .next()
            .unwrap()
            .updated_at;
        set_customer_geolocation(&ctx, "t".into(), "cust_1".into(), 41.0, -73.0);
        assert_eq!(ctx.db.customer_geolocations().iter().count(), 1);
        let updated = ctx.db.customer_geolocations().iter().next().unwrap();
        assert!((updated.latitude - 41.0).abs() < 0.001);
        assert!((updated.longitude - -73.0).abs() < 0.001);
        assert!(updated.updated_at >= original_updated);
    }

    #[test]
    fn test_set_geolocation_multiple_customers() {
        let ctx = test_ctx();
        set_customer_geolocation(&ctx, "t".into(), "cust_1".into(), 10.0, 10.0);
        set_customer_geolocation(&ctx, "t".into(), "cust_2".into(), 20.0, 20.0);
        set_customer_geolocation(&ctx, "t".into(), "cust_3".into(), 30.0, 30.0);
        assert_eq!(ctx.db.customer_geolocations().iter().count(), 3);
    }

    #[test]
    fn test_delete_geolocation() {
        let ctx = test_ctx();
        set_customer_geolocation(&ctx, "t".into(), "cust_1".into(), 10.0, 20.0);
        assert_eq!(ctx.db.customer_geolocations().iter().count(), 1);
        delete_customer_geolocation(&ctx, "cust_1".into());
        assert_eq!(ctx.db.customer_geolocations().iter().count(), 0);
    }

    #[test]
    fn test_delete_nonexistent_geolocation() {
        let ctx = test_ctx();
        delete_customer_geolocation(&ctx, "cust_nonexistent".into());
        assert_eq!(ctx.db.customer_geolocations().iter().count(), 0);
    }

    #[test]
    fn test_tenant_isolation() {
        let ctx = test_ctx();
        set_customer_geolocation(&ctx, "t_a".into(), "cust_1".into(), 1.0, 1.0);
        set_customer_geolocation(&ctx, "t_b".into(), "cust_2".into(), 2.0, 2.0);
        let a_only: Vec<CustomerGeolocation> = ctx
            .db
            .customer_geolocations()
            .iter()
            .filter(|g| g.tenant_id == "t_a")
            .collect();
        assert_eq!(a_only.len(), 1);
        assert_eq!(a_only[0].customer_id, "cust_1");
    }
}
