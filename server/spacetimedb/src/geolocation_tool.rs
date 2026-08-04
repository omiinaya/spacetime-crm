/// Geolocation tool stubs for testing.
use spacetimedb::*;

/// Placeholder module for geolocation tool tests.
/// The main geolocation logic lives in customer_geolocation.rs.
#[spacetimedb::reducer]
pub fn geocode_address(_ctx: &ReducerContext, _address: String) {
    // Stub — real implementation uses external geocoding API
}

#[cfg(test)]
mod geolocation_tool_tests {
    use crate::*;

    fn test_ctx() -> ReducerContext {
        crate::test_stubs::dummy_ctx()
    }

    #[test]
    fn test_geocode_address_is_noop_stub() {
        let ctx = test_ctx();
        // The reducer is a stub — calling it must not panic and must not
        // write anything into the datastore (no geolocation rows exist).
        geocode_address(&ctx, "123 Main St, Springfield".into());
        assert_eq!(ctx.db.customer_geolocations().iter().count(), 0);
    }

    #[test]
    fn test_geocode_address_empty_string_is_noop() {
        let ctx = test_ctx();
        geocode_address(&ctx, String::new());
        assert_eq!(ctx.db.customer_geolocations().iter().count(), 0);
    }
}
