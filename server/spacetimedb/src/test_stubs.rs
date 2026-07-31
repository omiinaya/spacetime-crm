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

thread_local! {
    /// Maps table names to TableIds.
    static TABLE_NAME_TO_ID: RefCell<HashMap<String, TableId>> = RefCell::new(HashMap::new());

    /// Maps index names to IndexIds.
    static INDEX_NAME_TO_ID: RefCell<HashMap<String, IndexId>> = RefCell::new(HashMap::new());

    /// Auto-incrementing counter for table/index IDs.
    static NEXT_TABLE_ID: RefCell<u32> = RefCell::new(1);
    static NEXT_INDEX_ID: RefCell<u32> = RefCell::new(1);

    /// Stores rows for each table: TableId -> Vec of (primary_key_bytes, row_bytes).
    static TABLE_ROWS: RefCell<HashMap<TableId, Vec<(Vec<u8>, Vec<u8>)>>> = RefCell::new(HashMap::new());

    /// Iterator storage: handle -> Vec of row bytes to yield.
    static ITERATORS: RefCell<HashMap<u32, Vec<Vec<u8>>>> = RefCell::new(HashMap::new());

    /// Next iterator handle.
    static NEXT_ITER_HANDLE: RefCell<u32> = RefCell::new(1);
}

// ─── Helper: get or create a TableId from a name ──

fn get_table_id(name: &str) -> TableId {
    TABLE_NAME_TO_ID.with(|m| {
        let mut m = m.borrow_mut();
        if let Some(id) = m.get(name) {
            return *id;
        }
        let id = NEXT_TABLE_ID.with(|n| {
            let n = n.replace_with(|n| *n + 1);
            TableId(n)
        });
        m.insert(name.to_string(), id);
        id
    })
}

fn get_index_id(name: &str) -> IndexId {
    INDEX_NAME_TO_ID.with(|m| {
        let mut m = m.borrow_mut();
        if let Some(id) = m.get(name) {
            return *id;
        }
        let id = NEXT_INDEX_ID.with(|n| {
            let n = n.replace_with(|n| *n + 1);
            IndexId(n)
        });
        m.insert(name.to_string(), id);
        id
    })
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
    TABLE_NAME_TO_ID.with(|m| m.borrow_mut().clear());
    INDEX_NAME_TO_ID.with(|m| m.borrow_mut().clear());
    NEXT_TABLE_ID.with(|n| *n.borrow_mut() = 1);
    NEXT_INDEX_ID.with(|n| *n.borrow_mut() = 1);
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

    eprintln!(
        "POINT SCAN: index_id={:?} point={:?} ({} bytes)",
        _index_id,
        point_bytes,
        point_bytes.len()
    );

    let handle = NEXT_ITER_HANDLE.with(|n| {
        let h = *n.borrow();
        n.replace_with(|n| *n + 1);
        h
    });

    // For point index scans, we need to find rows where the index column matches the point.
    // The point is a BSATN-encoded value (e.g., a String for the primary key).
    // We scan all tables and find rows whose primary key matches the point.
    // Since the primary key is the first field, and the point is the BSATN encoding
    // of the primary key value, we can compare the point bytes with the first
    // field of each row.
    let matching_rows: Vec<Vec<u8>> = TABLE_ROWS.with(|m| {
        let m = m.borrow();
        let mut result = Vec::new();
        for (table_id, rows) in m.iter() {
            for (pk, row) in rows.iter() {
                let matched = pk == &point_bytes || pk.starts_with(&point_bytes);
                if matched {
                    eprintln!("  MATCH: table={:?} pk={:?}", table_id, pk);
                }
                if matched {
                    result.push(row.clone());
                }
            }
        }
        result
    });
    eprintln!("POINT SCAN result: {} rows", matching_rows.len());

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

    let deleted_count: u32 = TABLE_ROWS.with(|m| {
        let mut m = m.borrow_mut();
        let mut count = 0u32;
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

/// TEMPORARY DEBUG — dump datastore contents.
#[cfg(test)]
pub fn debug_dump() {
    TABLE_ROWS.with(|m| {
        for (tid, rows) in m.borrow().iter() {
            eprintln!("TABLE {:?}: {} rows", tid, rows.len());
            for (i, (pk, row)) in rows.iter().enumerate() {
                eprintln!(
                    "  row {}: pk={:?} len={} bytes={:?}",
                    i,
                    pk,
                    row.len(),
                    &row[..row.len().min(48)]
                );
            }
        }
    });
    TABLE_NAME_TO_ID.with(|m| {
        for (name, id) in m.borrow().iter() {
            eprintln!("  name {:?} -> {:?}", name, id);
        }
    });
}
