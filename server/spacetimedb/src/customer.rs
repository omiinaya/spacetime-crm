use spacetimedb::*;

#[spacetimedb::table(accessor = customer, public)]
#[derive(Debug, Clone)]
pub struct Customer {
    #[primary_key]
    pub id: String,
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
    pub created_at: u64,
    pub updated_at: u64,
}

#[spacetimedb::reducer]
pub fn create_customer(ctx: &ReducerContext, first_name: String, last_name: String, email: String, phone: String) {
    let id = super::make_id("cust", ctx);
    let now = super::now_ms(ctx);
    ctx.db.customer().insert(Customer {
        id,
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
    let now = super::now_ms(ctx);
    if let Some(c) = ctx.db.customer().id().find(&id) {
        ctx.db.customer().id().update(Customer { first_name, last_name, email, phone, mobile, address_line1, address_line2, city, state, zip, company, notes, tags, updated_at: now, ..c });
    }
}

#[spacetimedb::reducer]
pub fn delete_customer(ctx: &ReducerContext, id: String) {
    ctx.db.customer().id().delete(&id);
}
