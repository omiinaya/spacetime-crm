//! FFI stub implementations for running SpacetimeDB module tests natively.
//!
//! When building as an `rlib` (for `cargo test`), the WASM import functions
//! from `spacetimedb-bindings-sys` are not available. This module provides
//! minimal in-memory implementations so that tests using `ReducerContext::__dummy()`
//! can actually execute database operations.
//!
//! Only compiled under `#[cfg(test)]` and `#[cfg(not(target_arch = "wasm32"))]`.

#![allow(non_snake_case, dead_code, unused_unsafe)]
#![allow(private_interfaces)]

use std::cell::RefCell;
use std::collections::HashMap;
use std::sync::{LazyLock, Mutex};

// ─── Type aliases matching spacetimedb_bindings_sys raw types ──

#[repr(transparent)]
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct TableId(pub u32);

#[repr(transparent)]
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct IndexId(pub u32);

#[repr(transparent)]
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct RowIter(pub u32);

impl RowIter {
    const INVALID: Self = Self(0);
}

// ─── Global in-memory datastore ──
//
// IMPORTANT: table/index ID assignment must be PROCESS-GLOBAL, not per-thread.
// The `#[table]` macro caches `table_id()` / `index_id()` in process-global
// `OnceLock`s, so the very first thread to touch a table pins its ID for the
// whole test binary. If the stub assigned IDs from thread-local counters,
// parallel test threads would disagree about which TableId means which table,
// and point/table scans would return rows from the wrong table (garbage
// decodes, `Failed to decode row!` panics).

/// Maps table names to TableIds (process-global).
static TABLE_NAME_TO_ID: LazyLock<Mutex<HashMap<String, TableId>>> =
    LazyLock::new(|| Mutex::new(HashMap::new()));

/// Maps index names to IndexIds (process-global).
static INDEX_NAME_TO_ID: LazyLock<Mutex<HashMap<String, IndexId>>> =
    LazyLock::new(|| Mutex::new(HashMap::new()));

/// Auto-incrementing counters for table/index IDs (process-global).
static NEXT_TABLE_ID: Mutex<u32> = Mutex::new(1);
static NEXT_INDEX_ID: Mutex<u32> = Mutex::new(1);

/// Maps IndexId -> owning table name, parsed from the canonical index name
/// (`{table}_{cols}_idx_{kind}`). Used to scope point scans to one table.
static INDEX_ID_TO_TABLE: LazyLock<Mutex<HashMap<IndexId, String>>> =
    LazyLock::new(|| Mutex::new(HashMap::new()));

thread_local! {
    /// Stores rows for each table: TableId -> Vec of (primary_key_bytes, row_bytes).
    /// Per-thread and reset between tests (see `reset_datastore`).
    static TABLE_ROWS: RefCell<HashMap<TableId, Vec<(Vec<u8>, Vec<u8>)>>> = RefCell::new(HashMap::new());

    /// Iterator storage: handle -> Vec of row bytes to yield.
    static ITERATORS: RefCell<HashMap<u32, Vec<Vec<u8>>>> = RefCell::new(HashMap::new());

    /// Next iterator handle.
    static NEXT_ITER_HANDLE: RefCell<u32> = RefCell::new(1);
}

// ─── Helper: get or create a TableId from a name ──

fn get_table_id(name: &str) -> TableId {
    let mut m = TABLE_NAME_TO_ID.lock().unwrap();
    if let Some(id) = m.get(name) {
        return *id;
    }
    let mut n = NEXT_TABLE_ID.lock().unwrap();
    let id = TableId(*n);
    *n += 1;
    m.insert(name.to_string(), id);
    id
}

fn get_index_id(name: &str) -> IndexId {
    let mut m = INDEX_NAME_TO_ID.lock().unwrap();
    if let Some(id) = m.get(name) {
        return *id;
    }
    let mut n = NEXT_INDEX_ID.lock().unwrap();
    let id = IndexId(*n);
    *n += 1;
    m.insert(name.to_string(), id);

    // Canonical index names look like `{table}_{cols}_idx_{kind}` (see
    // spacetimedb-bindings-macro table.rs). Recover the owning table by
    // taking the longest registered table name that prefixes the
    // `{table}_{cols}` portion. Table names may themselves contain
    // underscores (e.g. `customer_geolocation`), hence longest-prefix match.
    if let Some(idx_marker) = name.rfind("_idx_") {
        let prefix = &name[..idx_marker];
        let tables = TABLE_NAME_TO_ID.lock().unwrap();
        let best = tables
            .keys()
            .filter(|t| prefix == t.as_str() || prefix.starts_with(&format!("{}_", t)))
            .max_by_key(|t| t.len())
            .cloned();
        if let Some(table) = best {
            INDEX_ID_TO_TABLE.lock().unwrap().insert(id, table);
        }
    }
    id
}

/// Reset the entire in-memory datastore for the current thread.
///
/// The stub datastore is `thread_local!`, so it survives across `#[test]`
/// functions that run on the same worker thread. Without a reset, rows from
/// one test leak into the next, tripping unique-index assertions
/// (`datastore_index_scan_point_bsatn on unique field cannot return >1 rows`)
/// and corrupting row decoding with stale schemas. Every test must call this
/// before it starts (see `dummy_ctx`).
#[cfg(test)]
pub fn reset_datastore() {
    // Only per-test DATA is cleared. Table/index ID registries are
    // process-global (the `#[table]` macro caches them in OnceLocks) and must
    // stay stable across tests.
    TABLE_ROWS.with(|m| m.borrow_mut().clear());
    ITERATORS.with(|m| m.borrow_mut().clear());
    NEXT_ITER_HANDLE.with(|n| *n.borrow_mut() = 1);
}

/// Create a fresh `ReducerContext` for a unit test, starting from a clean
/// in-memory datastore. Use this everywhere instead of
/// `ReducerContext::__dummy()` so tests are isolated from each other.
#[cfg(test)]
pub fn dummy_ctx() -> spacetimedb::ReducerContext {
    reset_datastore();
    spacetimedb::ReducerContext::__dummy()
}

/// Extract the primary key bytes from a BSATN-encoded row.
/// For all tables in spacetime-crm, the primary key is the first field (`id: String`).
/// BSATN encodes a String as: u32 length prefix + UTF-8 bytes.
fn extract_primary_key(row_bytes: &[u8]) -> Vec<u8> {
    // BSATN encoding of a struct is the concatenation of its fields' encodings.
    // The first field is `id: String`, which is encoded as:
    //   u32 (little-endian length) + UTF-8 bytes
    if row_bytes.len() < 4 {
        return row_bytes.to_vec();
    }
    let len = u32::from_le_bytes([row_bytes[0], row_bytes[1], row_bytes[2], row_bytes[3]]) as usize;
    let end = 4 + len;
    if end <= row_bytes.len() {
        row_bytes[..end].to_vec()
    } else {
        row_bytes.to_vec()
    }
}

// ─── FFI stub implementations ──
// These are `#[no_mangle]` extern "C" functions that provide the symbols
// that `spacetimedb-bindings-sys` expects when building for native (non-WASM).

#[no_mangle]
pub extern "C" fn table_id_from_name(
    name_ptr: *const u8,
    name_len: usize,
    out: *mut TableId,
) -> u16 {
    let name = if name_ptr.is_null() || name_len == 0 {
        String::new()
    } else {
        let slice = unsafe { std::slice::from_raw_parts(name_ptr, name_len) };
        String::from_utf8_lossy(slice).to_string()
    };
    let id = get_table_id(&name);
    unsafe {
        std::ptr::write(out, id);
    }
    0 // success
}

#[no_mangle]
pub extern "C" fn index_id_from_name(
    name_ptr: *const u8,
    name_len: usize,
    out: *mut IndexId,
) -> u16 {
    let name = if name_ptr.is_null() || name_len == 0 {
        String::new()
    } else {
        let slice = unsafe { std::slice::from_raw_parts(name_ptr, name_len) };
        String::from_utf8_lossy(slice).to_string()
    };
    let id = get_index_id(&name);
    unsafe {
        std::ptr::write(out, id);
    }
    0 // success
}

#[no_mangle]
pub extern "C" fn datastore_insert_bsatn(
    table_id: TableId,
    row_ptr: *mut u8,
    row_len_ptr: *mut usize,
) -> u16 {
    let row_len = unsafe { *row_len_ptr };
    let row_bytes = if row_ptr.is_null() || row_len == 0 {
        Vec::new()
    } else {
        unsafe { std::slice::from_raw_parts(row_ptr, row_len) }.to_vec()
    };

    // Debug logging removed — stubs are shipped alongside production code.
    // Use log::info! if re-adding during development.

    let pk = extract_primary_key(&row_bytes);

    TABLE_ROWS.with(|m| {
        let mut m = m.borrow_mut();
        let rows = m.entry(table_id).or_default();
        rows.push((pk, row_bytes.clone()));
    });

    // Write back empty bytes (no auto-increment columns in these tables)
    unsafe {
        *row_len_ptr = 0;
    }
    0 // success
}

#[no_mangle]
pub extern "C" fn datastore_update_bsatn(
    table_id: TableId,
    _index_id: IndexId,
    row_ptr: *mut u8,
    row_len_ptr: *mut usize,
) -> u16 {
    let row_len = unsafe { *row_len_ptr };
    let row_bytes = if row_ptr.is_null() || row_len == 0 {
        Vec::new()
    } else {
        unsafe { std::slice::from_raw_parts(row_ptr, row_len) }.to_vec()
    };

    let pk = extract_primary_key(&row_bytes);

    TABLE_ROWS.with(|m| {
        let mut m = m.borrow_mut();
        if let Some(rows) = m.get_mut(&table_id) {
            // Find and replace the row with matching primary key
            for (existing_pk, existing_row) in rows.iter_mut() {
                if *existing_pk == pk {
                    *existing_row = row_bytes.clone();
                    break;
                }
            }
        }
    });

    // Write back empty bytes (no auto-increment columns)
    unsafe {
        *row_len_ptr = 0;
    }
    0 // success
}

#[no_mangle]
pub extern "C" fn datastore_table_scan_bsatn(table_id: TableId, out: *mut RowIter) -> u16 {
    let handle = NEXT_ITER_HANDLE.with(|n| {
        let h = *n.borrow();
        n.replace_with(|n| *n + 1);
        h
    });

    let rows: Vec<Vec<u8>> = TABLE_ROWS.with(|m| {
        m.borrow()
            .get(&table_id)
            .map(|rows| rows.iter().map(|(_, row)| row.clone()).collect())
            .unwrap_or_default()
    });

    // Debug logging removed — stubs are shipped alongside production code.

    ITERATORS.with(|iters| {
        iters.borrow_mut().insert(handle, rows);
    });

    unsafe {
        std::ptr::write(out, RowIter(handle));
    }
    0 // success
}

#[no_mangle]
pub extern "C" fn datastore_index_scan_point_bsatn(
    _index_id: IndexId,
    point_ptr: *const u8,
    point_len: usize,
    out: *mut RowIter,
) -> u16 {
    let point_bytes = if point_ptr.is_null() || point_len == 0 {
        Vec::new()
    } else {
        unsafe { std::slice::from_raw_parts(point_ptr, point_len) }.to_vec()
    };

    // For point index scans, find rows of the index's OWN table whose index
    // column matches the point. The primary key is the first field, so for the
    // pk index (`{table}_id_idx_pk`) comparing the point against the first
    // field of each row is exact. Scoping to the owning table is essential:
    // scanning every table returns rows that happen to share the same pk
    // value, which callers then decode as the wrong type (garbage decodes).
    //
    // Lock ordering: the ID registries are append-only (a name never maps to
    // a different ID), so clone the owner table out of INDEX_ID_TO_TABLE and
    // DROP that lock before acquiring TABLE_NAME_TO_ID. Holding
    // INDEX_ID_TO_TABLE while taking TABLE_NAME_TO_ID would deadlock against
    // `get_index_id`, which holds TABLE_NAME_TO_ID while inserting into
    // INDEX_ID_TO_TABLE (ABBA).
    let owner_table = {
        let id_map = INDEX_ID_TO_TABLE.lock().unwrap();
        id_map.get(&_index_id).cloned()
    }
    .and_then(|t| TABLE_NAME_TO_ID.lock().unwrap().get(&t).copied());

    let matching_rows: Vec<Vec<u8>> = TABLE_ROWS.with(|m| {
        let m = m.borrow();
        let mut result = Vec::new();
        if let Some(owner_tid) = owner_table {
            if let Some(rows) = m.get(&owner_tid) {
                for (pk, row) in rows.iter() {
                    if pk == &point_bytes || pk.starts_with(&point_bytes) {
                        result.push(row.clone());
                    }
                }
            }
        } else {
            // Index not yet mapped to a table: fall back to a pk match across
            // all tables (legacy behavior).
            for (_table_id, rows) in m.iter() {
                for (pk, row) in rows.iter() {
                    if pk == &point_bytes || pk.starts_with(&point_bytes) {
                        result.push(row.clone());
                    }
                }
            }
        }
        result
    });

    let handle = NEXT_ITER_HANDLE.with(|n| {
        let h = *n.borrow();
        n.replace_with(|n| *n + 1);
        h
    });

    ITERATORS.with(|iters| {
        iters.borrow_mut().insert(handle, matching_rows);
    });

    unsafe {
        std::ptr::write(out, RowIter(handle));
    }
    0 // success
}

#[no_mangle]
pub extern "C" fn datastore_delete_by_index_scan_point_bsatn(
    _index_id: IndexId,
    point_ptr: *const u8,
    point_len: usize,
    out: *mut u32,
) -> u16 {
    let point_bytes = if point_ptr.is_null() || point_len == 0 {
        Vec::new()
    } else {
        unsafe { std::slice::from_raw_parts(point_ptr, point_len) }.to_vec()
    };

    // Scope deletion to the index's own table, same as the point scan.
    // Same lock-ordering discipline: clone out of INDEX_ID_TO_TABLE, drop the
    // lock, then look up the TableId in TABLE_NAME_TO_ID (see ABBA note above).
    let owner_table = {
        let id_map = INDEX_ID_TO_TABLE.lock().unwrap();
        id_map.get(&_index_id).cloned()
    }
    .and_then(|t| TABLE_NAME_TO_ID.lock().unwrap().get(&t).copied());

    let deleted_count: u32 = TABLE_ROWS.with(|m| {
        let mut m = m.borrow_mut();
        let mut count = 0u32;
        if let Some(owner_tid) = owner_table {
            if let Some(rows) = m.get_mut(&owner_tid) {
                rows.retain(|(pk, _)| {
                    if pk == &point_bytes || pk.starts_with(&point_bytes) {
                        count += 1;
                        false // remove
                    } else {
                        true // keep
                    }
                });
            }
        } else {
            for (_table_id, rows) in m.iter_mut() {
                rows.retain(|(pk, _)| {
                    if pk == &point_bytes || pk.starts_with(&point_bytes) {
                        count += 1;
                        false // remove
                    } else {
                        true // keep
                    }
                });
            }
        }
        count
    });

    unsafe {
        std::ptr::write(out, deleted_count);
    }
    0 // success
}

#[no_mangle]
pub extern "C" fn row_iter_bsatn_advance(
    iter: RowIter,
    buffer_ptr: *mut u8,
    buffer_len_ptr: *mut usize,
) -> i16 {
    if iter == RowIter::INVALID {
        // Caller uses buf_len to size the returned chunk; leaving it stale
        // makes RowIter::read append uninitialized memory to the buffer.
        unsafe { *buffer_len_ptr = 0 };
        return -1; // exhausted
    }

    let mut rows = ITERATORS.with(|iters| iters.borrow_mut().remove(&iter.0).unwrap_or_default());

    if rows.is_empty() {
        // CRITICAL: zero the buffer length on the exhausted path. RowIter::read()
        // appends buf_len bytes to its output buffer on -1; leaving the stale
        // incoming capacity (e.g. 65536) appends 64KB of uninitialized memory
        // and every subsequent row decode fails with garbage.
        unsafe { *buffer_len_ptr = 0 };
        return -1; // exhausted
    }

    // Take the first row
    let row = rows.remove(0);

    // Put the remaining rows back
    ITERATORS.with(|iters| {
        iters.borrow_mut().insert(iter.0, rows.clone());
    });

    let is_last = rows.is_empty();
    let buf_len = unsafe { *buffer_len_ptr };
    if buffer_ptr.is_null() || buf_len < row.len() {
        // Buffer too small - tell caller how much space we need.
        unsafe {
            *buffer_len_ptr = row.len();
        }
        // errno::BUFFER_TOO_SMALL == 11 in spacetimedb-primitives. The real
        // `RowIter::read` matches on this exact value; any other positive
        // return is treated as an unexpected error and panics.
        return 11;
    }

    // Write the row into the buffer
    unsafe {
        std::ptr::copy_nonoverlapping(row.as_ptr(), buffer_ptr, row.len());
        *buffer_len_ptr = row.len();
    }

    // Return -1 (exhausted) when this was the last row. The real runtime
    // signals exhaustion in the same call that writes the final chunk, and
    // callers (e.g. `UniqueColumn::find`'s `is_exhausted` assert) rely on it:
    // a 0 here leaves the RowIter handle valid, so `find` believes a unique
    // index scan returned more than one row and panics.
    if is_last {
        return -1;
    }

    0 // success, more rows available
}

#[no_mangle]
pub extern "C" fn row_iter_bsatn_close(iter: RowIter) -> u16 {
    if iter == RowIter::INVALID {
        return 0;
    }
    ITERATORS.with(|iters| {
        iters.borrow_mut().remove(&iter.0);
    });
    0 // success
}
