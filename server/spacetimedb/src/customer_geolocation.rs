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
pub fn set_customer_geolocation(ctx: &ReducerContext, tenant_id: String, customer_id: String, latitude: f64, longitude: f64) {
    let now = super::now_ms(ctx);
    // Upsert — insert or update
    if let Some(existing) = ctx.db.customer_geolocations().customer_id().find(&customer_id) {
        ctx.db.customer_geolocations().customer_id().update(CustomerGeolocation {
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
    ctx.db.customer_geolocations().customer_id().delete(&customer_id);
}
