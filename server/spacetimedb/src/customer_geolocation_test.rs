#[cfg(test)]
mod tests {
    use crate::*;

    fn test_ctx() -> ReducerContext {
        crate::test_stubs::dummy_ctx()
    }

    #[test]
    fn test_set_customer_geolocation() {
        let ctx = test_ctx();
        set_customer_geolocation(&ctx, "t_geo".into(), "cust_1".into(), 40.7128, -74.0060);
        let geos: Vec<CustomerGeolocation> = ctx.db.customer_geolocations().iter().collect();
        assert_eq!(geos.len(), 1);
        let g = &geos[0];
        assert_eq!(g.customer_id, "cust_1");
        assert!((g.latitude - 40.7128).abs() < 0.001);
        assert!((g.longitude - -74.0060).abs() < 0.001);
    }

    #[test]
    fn test_set_customer_geolocation_upsert() {
        let ctx = test_ctx();
        set_customer_geolocation(&ctx, "t".into(), "cust_1".into(), 40.0, -74.0);
        assert_eq!(ctx.db.customer_geolocations().iter().count(), 1);
        set_customer_geolocation(&ctx, "t".into(), "cust_1".into(), 41.0, -73.0);
        assert_eq!(ctx.db.customer_geolocations().iter().count(), 1);
        assert!(
            (ctx.db
                .customer_geolocations()
                .iter()
                .next()
                .expect("expected at least one customer_geolocations record")
                .latitude
                - 41.0)
                .abs()
                < 0.001
        );
    }

    #[test]
    fn test_delete_customer_geolocation() {
        let ctx = test_ctx();
        set_customer_geolocation(&ctx, "t".into(), "cust_1".into(), 10.0, 20.0);
        assert_eq!(ctx.db.customer_geolocations().iter().count(), 1);
        delete_customer_geolocation(&ctx, "cust_1".into());
        assert_eq!(ctx.db.customer_geolocations().iter().count(), 0);
    }
}
