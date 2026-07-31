#[cfg(test)]
mod tests {
    use crate::appointment::appointment;
    use crate::*;

    #[test]
    fn debug_roundtrip() {
        crate::test_stubs::reset_datastore();
        let ctx = ReducerContext::__dummy();
        create_appointment(
            &ctx,
            "t_appt".into(),
            "cust_1".into(),
            "tkt_1".into(),
            "Screen repair".into(),
            "Replace cracked screen".into(),
            1700000000000,
            1700003600000,
            false,
            String::new(),
            String::new(),
            String::new(),
        );
        crate::test_stubs::debug_dump();
        let appts: Vec<Appointment> = ctx.db.appointment().iter().collect();
        eprintln!("READ BACK: {} rows", appts.len());
    }
}
