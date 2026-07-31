/// Geolocation tool stubs for testing.
use spacetimedb::*;

/// Placeholder module for geolocation tool tests.
/// The main geolocation logic lives in customer_geolocation.rs.
#[spacetimedb::reducer]
pub fn geocode_address(_ctx: &ReducerContext, _address: String) {
    // Stub — real implementation uses external geocoding API
}
