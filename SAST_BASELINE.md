======================================================================
STATIC ANALYSIS SECURITY TESTING (SAST) BASELINE REPORT
======================================================================
Generated: 2026-07-12T03:16:15.384287
Tool: Bandit bandit 1.9.4
  python version = 3.11.2 (main, Apr  8 2026, 01:58:00) [GCC 12.2.0]

Total findings (all): 1005
Production findings: 123
Test file findings: 882

--- Production Findings by Severity ---
HIGH: 0
MEDIUM: 115
LOW: 8

--- Production Findings by Test Type ---
  B104: 1 (1%)
  B105: 1 (1%)
  B110: 7 (6%)
  B608: 114 (93%)

--- Detailed Triage ---

[MEDIUM/   LOW]   B608 | REAL_VULNERABILITY   | server/helpers.py:138
  Code: count_result = await _sql(f"SELECT count(*) AS cnt FROM {table}{where_clause}")

[MEDIUM/   LOW]   B608 | REAL_VULNERABILITY   | server/helpers.py:142
  Code: query = f"SELECT * FROM {table}{where_clause}"

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/helpers.py:239
  Code: rows = await _sql(f"SELECT * FROM user WHERE id = '{_safe_id(user_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/helpers.py:291
  Code: rows = await _sql(f"SELECT * FROM user WHERE id = '{_safe_id(user_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[   LOW/MEDIUM]   B105 | FALSE_POSITIVE       | server/main.py:20
  Code: if settings.jwt_secret == "set-via-environment-variable":  # pragma: allowlist secret
  Note: Placeholder secret, not a real password

[MEDIUM/MEDIUM]   B104 | FALSE_POSITIVE       | server/main.py:86
  Code: host="0.0.0.0",
  Note: Dev binding to 0.0.0.0 for Docker - acceptable

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/appointments.py:62
  Code: f"SELECT * FROM appointment WHERE tenant_id = '{user['tenant_id']}' AND recurrence_rule != '' AND series_id = ''"
  Note: tenant_id comes from JWT (internal, not user-supplied)

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/appointments.py:67
  Code: f"SELECT * FROM appointment WHERE tenant_id = '{user['tenant_id']}' AND series_id = '{s['id']}'"
  Note: tenant_id comes from JWT (internal, not user-supplied)

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/appointments.py:102
  Code: cust = await _sql(f"SELECT * FROM customer WHERE id = '{_safe_id(body.customer_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/appointments.py:148
  Code: f"SELECT * FROM appointment WHERE tenant_id = '{user['tenant_id']}' AND id = '{_safe_id(body.series_id)}' AND recurrence_rule != '
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/appointments.py:161
  Code: f"SELECT * FROM appointment WHERE tenant_id = '{user['tenant_id']}' AND series_id = '{_safe_id(body.series_id)}'"
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/appointments.py:188
  Code: f"SELECT * FROM appointment WHERE tenant_id = '{user['tenant_id']}' "
  Note: tenant_id comes from JWT (internal, not user-supplied)

[MEDIUM/   LOW]   B608 | REAL_VULNERABILITY   | server/routes/appointments.py:197
  Code: f"SELECT first_name, last_name, email, mobile, phone FROM customer WHERE id = '{r.get('customer_id', '')}'"

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/appointments.py:212
  Code: f"SELECT * FROM appointment WHERE tenant_id = '{user['tenant_id']}' "
  Note: tenant_id comes from JWT (internal, not user-supplied)

[MEDIUM/   LOW]   B608 | REAL_VULNERABILITY   | server/routes/appointments.py:220
  Code: f"SELECT first_name, last_name, email, mobile, phone FROM customer WHERE id = '{appt.get('customer_id', '')}'"

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/auth.py:104
  Code: rows = await _sql(f"SELECT * FROM user WHERE email = '{_sanitize_sql(email)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/auth.py:136
  Code: tm_rows = await _sql(f"SELECT * FROM tenant_members WHERE username = '{_sanitize_sql(user['name'])}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[   LOW/  HIGH]   B110 | NOTE_WONTFIX         | server/routes/auth.py:139
  Code: except Exception:
  Note: Bare except - needs handling but low severity

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/auth.py:164
  Code: rows = await _sql(f"SELECT * FROM user WHERE id = '{_safe_id(user_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/auth.py:183
  Code: tm_rows = await _sql(f"SELECT * FROM tenant_members WHERE username = '{_safe_id(user['name'])}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[   LOW/  HIGH]   B110 | NOTE_WONTFIX         | server/routes/auth.py:186
  Code: except Exception:
  Note: Bare except - needs handling but low severity

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/auth.py:209
  Code: trows = await _sql(f"SELECT * FROM tenants WHERE id = '{user['tenant_id']}'")
  Note: tenant_id comes from JWT (internal, not user-supplied)

[   LOW/  HIGH]   B110 | NOTE_WONTFIX         | server/routes/auth.py:212
  Code: except Exception:
  Note: Bare except - needs handling but low severity

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/auth.py:219
  Code: rows = await _sql(f"SELECT * FROM user WHERE id = '{_safe_id(user['id'])}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[   LOW/  HIGH]   B110 | NOTE_WONTFIX         | server/routes/auth.py:223
  Code: except Exception:
  Note: Bare except - needs handling but low severity

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/auth.py:244
  Code: rows = await _sql(f"SELECT * FROM user WHERE id = '{_safe_id(user['id'])}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/auth.py:269
  Code: rows = await _sql(f"SELECT * FROM user WHERE id = '{_safe_id(user['id'])}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/auth.py:289
  Code: rows = await _sql(f"SELECT * FROM user WHERE id = '{_safe_id(user['id'])}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/auth.py:311
  Code: tm_rows = await _sql(f"SELECT * FROM tenant_members WHERE username = '{_safe_id(user['name'])}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[   LOW/  HIGH]   B110 | NOTE_WONTFIX         | server/routes/auth.py:314
  Code: except Exception:
  Note: Bare except - needs handling but low severity

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/auth.py:360
  Code: rows = await _sql(f"SELECT * FROM user WHERE id = '{_safe_id(user_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/auth.py:375
  Code: tm_rows = await _sql(f"SELECT * FROM tenant_members WHERE username = '{_safe_id(user['name'])}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[   LOW/  HIGH]   B110 | NOTE_WONTFIX         | server/routes/auth.py:378
  Code: except Exception:
  Note: Bare except - needs handling but low severity

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/auth.py:410
  Code: rows = await _sql(f"SELECT * FROM user WHERE email = '{_safe_id(email)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/auth.py:415
  Code: rows = await _sql(f"SELECT * FROM customer WHERE email = '{_safe_id(email)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/custom_fields.py:99
  Code: rows = await _sql(f"SELECT * FROM custom_field_values WHERE entity_id = '{_safe_id(entity_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/customers.py:202
  Code: customers = await _sql(f"SELECT * FROM customer WHERE id = '{_safe_id(customer_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/estimates.py:87
  Code: rows = await _sql(f"SELECT * FROM estimate_line_items WHERE estimate_id = '{_safe_id(estimate_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/estimates.py:122
  Code: est_rows = await _sql(f"SELECT * FROM estimates WHERE id = '{_safe_id(estimate_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/estimates.py:131
  Code: est_rows = await _sql(f"SELECT invoice_id FROM estimates WHERE id = '{_safe_id(estimate_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/estimates.py:152
  Code: cust = await _sql(f"SELECT * FROM customer WHERE id = '{_safe_id(est.get('customer_id', ''))}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | REAL_VULNERABILITY   | server/routes/export_import.py:43
  Code: rows = await _sql(f"SELECT * FROM {table}")

[   LOW/  HIGH]   B110 | NOTE_WONTFIX         | server/routes/health.py:72
  Code: except Exception:
  Note: Bare except - needs handling but low severity

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/invoices.py:92
  Code: cust = await _sql(f"SELECT * FROM customer WHERE id = '{_safe_id(body.customer_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/invoices.py:126
  Code: rows = await _sql(f"SELECT * FROM invoices WHERE tenant_id = '{user['tenant_id']}'")
  Note: tenant_id comes from JWT (internal, not user-supplied)

[MEDIUM/   LOW]   B608 | REAL_VULNERABILITY   | server/routes/invoices.py:208
  Code: sql = f"UPDATE invoices SET {', '.join(parts)} WHERE id = '{inv_id}'"

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/invoices.py:223
  Code: f"SELECT * FROM invoices WHERE tenant_id = '{user['tenant_id']}' AND (status = 'overdue' OR ((status = 'sent' OR status = 'partial
  Note: tenant_id comes from JWT (internal, not user-supplied)

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/invoices.py:237
  Code: f"SELECT * FROM invoices WHERE tenant_id = '{user['tenant_id']}' AND (status = 'sent' OR status = 'partial') AND due_date > 0 AND 
  Note: tenant_id comes from JWT (internal, not user-supplied)

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/invoices.py:255
  Code: f"SELECT * FROM invoices WHERE tenant_id = '{user['tenant_id']}' AND (status = 'overdue' OR ((status = 'sent' OR status = 'partial
  Note: tenant_id comes from JWT (internal, not user-supplied)

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/invoices.py:259
  Code: cust = await _sql(f"SELECT * FROM customer WHERE id = '{_safe_id(inv['customer_id'])}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/invoices.py:306
  Code: rows = await _sql(f"SELECT * FROM invoice_line_items WHERE invoice_id = '{_safe_id(invoice_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/invoices.py:357
  Code: invs = await _sql(f"SELECT * FROM invoices WHERE id = '{_safe_id(invoice_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/invoices.py:361
  Code: items = await _sql(f"SELECT * FROM invoice_line_items WHERE invoice_id = '{_safe_id(invoice_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/invoices.py:363
  Code: cust = await _sql(f"SELECT * FROM customer WHERE id = '{_safe_id(inv['customer_id'])}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/invoices.py:413
  Code: f"SELECT amount, method, reference, created_at, notes FROM payment WHERE invoice_id = '{_safe_id(invoice_id)}'"
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/invoices.py:453
  Code: f"SELECT * FROM invoices WHERE id = '{_safe_id(invoice_id)}' AND tenant_id = '{user['tenant_id']}'"
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/invoices.py:459
  Code: cust = await _sql(f"SELECT * FROM customer WHERE id = '{_safe_id(inv['customer_id'])}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/invoices.py:493
  Code: invs = await _sql(f"SELECT * FROM invoices WHERE id = '{_safe_id(invoice_id)}' AND tenant_id = '{user['tenant_id']}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/invoices.py:500
  Code: cust = await _sql(f"SELECT * FROM customer WHERE id = '{_safe_id(inv['customer_id'])}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/invoices.py:537
  Code: f"SELECT * FROM audit_log WHERE tenant_id = '{user['tenant_id']}' "
  Note: tenant_id comes from JWT (internal, not user-supplied)

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/payment_methods.py:31
  Code: f"SELECT * FROM saved_payment_methods WHERE tenant_id = '{user['tenant_id']}' AND customer_id = '{customer_id}'"
  Note: tenant_id comes from JWT (internal, not user-supplied)

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/payment_methods.py:34
  Code: rows = await _sql(f"SELECT * FROM saved_payment_methods WHERE tenant_id = '{user['tenant_id']}'")
  Note: tenant_id comes from JWT (internal, not user-supplied)

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/payments.py:66
  Code: invoices = await _sql(f"SELECT * FROM invoices WHERE id = '{_safe_id(invoice_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/payments.py:67
  Code: payments = await _sql(f"SELECT * FROM payment WHERE invoice_id = '{_safe_id(invoice_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/payments.py:79
  Code: cust = await _sql(f"SELECT * FROM customer WHERE id = '{_safe_id(body.customer_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:61
  Code: rows = await _sql(f"SELECT * FROM customer WHERE id = '{_safe_id(customer_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:80
  Code: rows = await _sql(f"SELECT * FROM customer WHERE email = '{_sanitize_sql(email)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:137
  Code: tickets = await _sql(f"SELECT * FROM ticket WHERE customer_id = '{_safe_id(cid)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:138
  Code: invoices = await _sql(f"SELECT * FROM invoices WHERE customer_id = '{_safe_id(cid)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:139
  Code: appointments = await _sql(f"SELECT * FROM appointment WHERE customer_id = '{_safe_id(cid)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:161
  Code: rows = await _sql(f"SELECT * FROM ticket WHERE customer_id = '{_safe_id(customer['id'])}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:172
  Code: rows = await _sql(f"SELECT * FROM ticket WHERE id = '{_safe_id(ticket_id)}' AND customer_id = '{customer['id']}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:176
  Code: notes = await _sql(f"SELECT * FROM ticket_note WHERE ticket_id = '{_safe_id(ticket_id)}' AND internal = false")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:188
  Code: rows = await _sql(f"SELECT * FROM ticket WHERE id = '{_safe_id(ticket_id)}' AND customer_id = '{customer['id']}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:209
  Code: rows = await _sql(f"SELECT * FROM invoices WHERE customer_id = '{_safe_id(customer['id'])}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:217
  Code: f"SELECT * FROM invoices WHERE id = '{_safe_id(invoice_id)}' AND customer_id = '{customer['id']}'"
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:222
  Code: items = await _sql(f"SELECT * FROM invoice_line_items WHERE invoice_id = '{_safe_id(invoice_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:224
  Code: payments = await _sql(f"SELECT * FROM payment WHERE invoice_id = '{_safe_id(invoice_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:244
  Code: f"SELECT * FROM invoices WHERE id = '{_safe_id(invoice_id)}' AND customer_id = '{customer['id']}'"
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:263
  Code: payments = await _sql(f"SELECT * FROM payment WHERE invoice_id = '{_safe_id(invoice_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:281
  Code: rows = await _sql(f"SELECT * FROM appointment WHERE customer_id = '{_safe_id(customer['id'])}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:323
  Code: f"SELECT * FROM invoices WHERE id = '{_safe_id(invoice_id)}' AND customer_id = '{customer['id']}'"
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:333
  Code: payments = await _sql(f"SELECT * FROM payment WHERE invoice_id = '{_safe_id(invoice_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:340
  Code: line_items = await _sql(f"SELECT * FROM invoice_line_items WHERE invoice_id = '{_safe_id(invoice_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:364
  Code: rows = await _sql(f"SELECT * FROM saved_payment_methods WHERE customer_id = '{_safe_id(customer['id'])}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:383
  Code: f"SELECT * FROM invoices WHERE id = '{_safe_id(invoice_id)}' AND customer_id = '{customer['id']}'"
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:394
  Code: f"SELECT * FROM saved_payment_methods WHERE stripe_payment_method_id = '{_sanitize_sql(payment_method_id)}' AND customer_id = '{_s
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/portal.py:401
  Code: payments = await _sql(f"SELECT * FROM payment WHERE invoice_id = '{_safe_id(invoice_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/pos.py:46
  Code: f"SELECT * FROM counter_sale WHERE id = '{_safe_id(sale_id)}' AND tenant_id = '{user['tenant_id']}'"
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/pos.py:51
  Code: items = await _sql(f"SELECT * FROM counter_sale_line_item WHERE sale_id = '{_safe_id(sale_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/pos.py:60
  Code: f"SELECT * FROM counter_sale WHERE id = '{_safe_id(sale_id)}' AND tenant_id = '{user['tenant_id']}'"
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/pos.py:66
  Code: items = await _sql(f"SELECT * FROM counter_sale_line_item WHERE sale_id = '{_safe_id(sale_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/products.py:133
  Code: rows = await _sql(f"SELECT * FROM inventory_adjustment WHERE product_id = '{_safe_id(product_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/products.py:161
  Code: rows = await _sql(f"SELECT * FROM products WHERE tenant_id = '{_safe_id(user['tenant_id'])}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/products.py:170
  Code: f"SELECT * FROM products WHERE tenant_id = '{_safe_id(user['tenant_id'])}' AND barcode = '{_sanitize_sql(barcode)}'"
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/products.py:181
  Code: rows = await _sql(f"SELECT * FROM products WHERE tenant_id = '{user['tenant_id']}'")
  Note: tenant_id comes from JWT (internal, not user-supplied)

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/products.py:202
  Code: f"SELECT * FROM products WHERE id = '{_safe_id(body.source_product_id)}' AND tenant_id = '{tid}'"
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/products.py:205
  Code: f"SELECT * FROM products WHERE id = '{_safe_id(body.destination_product_id)}' AND tenant_id = '{tid}'"
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/purchase_orders.py:65
  Code: rows = await _sql(f"SELECT * FROM purchase_order WHERE id = '{_safe_id(po_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/purchase_orders.py:69
  Code: items = await _sql(f"SELECT * FROM purchase_order_line_item WHERE purchase_order_id = '{_safe_id(po_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/recurring_invoices.py:28
  Code: rows = await _sql(f"SELECT * FROM recurring_invoice_rules WHERE tenant_id = '{user['tenant_id']}'")
  Note: tenant_id comes from JWT (internal, not user-supplied)

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/recurring_invoices.py:32
  Code: cust = await _sql(f"SELECT first_name, last_name FROM customer WHERE id = '{_safe_id(r.get('customer_id', ''))}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/report_schedules.py:72
  Code: existing = await _sql(f"SELECT * FROM scheduled_reports WHERE id = '{_safe_id(schedule_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/report_schedules.py:125
  Code: schedules = await _sql(f"SELECT * FROM scheduled_reports WHERE id = '{_safe_id(schedule_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | REAL_VULNERABILITY   | server/routes/tenants.py:52
  Code: rows = await _sql(f"SELECT * FROM tenants WHERE id = '{tenant_id}'")

[MEDIUM/   LOW]   B608 | REAL_VULNERABILITY   | server/routes/tenants.py:56
  Code: members = await _sql(f"SELECT * FROM tenant_members WHERE tenant_id = '{tenant_id}'")

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/tenants.py:132
  Code: rows = await _sql(f"SELECT * FROM tenants WHERE slug = '{_safe_id(slug)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/tenants.py:167
  Code: await _sql(f"UPDATE {tbl} SET tenant_id = '{tid}' WHERE tenant_id = ''")
  Note: Whitelisted table names from internal list

[MEDIUM/   LOW]   B608 | REAL_VULNERABILITY   | server/routes/tickets.py:99
  Code: await _sql(f"SELECT id, status, created_at FROM ticket WHERE tenant_id = '{tid}'"), key="created_at"

[MEDIUM/   LOW]   B608 | REAL_VULNERABILITY   | server/routes/tickets.py:105
  Code: f"SELECT id, name, role FROM \"user\" WHERE (role = 'admin' OR role = 'tech') AND active = true AND name != 'admin'"

[MEDIUM/   LOW]   B608 | REAL_VULNERABILITY   | server/routes/tickets.py:112
  Code: f"SELECT COUNT(*) AS cnt FROM ticket WHERE assigned_user_id = '{s['id']}' AND status != 'resolved' AND status != 'closed' AND stat

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/tickets.py:136
  Code: rows = await _sql(f"SELECT * FROM ticket WHERE id = '{_safe_id(ticket_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/tickets.py:139
  Code: cust = await _sql(f"SELECT * FROM customer WHERE id = '{_safe_id(t.get('customer_id', ''))}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/tickets.py:175
  Code: rows = await _sql(f"SELECT * FROM ticket_note WHERE ticket_id = '{_safe_id(ticket_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/tickets.py:214
  Code: rows = await _sql(f"SELECT * FROM ticket_timer WHERE ticket_id = '{_safe_id(ticket_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/tickets.py:255
  Code: rows = await _sql(f"SELECT * FROM ticket_checklist_items WHERE ticket_id = '{_safe_id(ticket_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | REAL_VULNERABILITY   | server/routes/tickets.py:301
  Code: rows = await _sql(f"SELECT * FROM sla_configs WHERE tenant_id = '{tenant_id}'")

[MEDIUM/   LOW]   B608 | REAL_VULNERABILITY   | server/routes/tickets.py:366
  Code: rows = await _sql(f"SELECT * FROM sla_configs WHERE tenant_id = '{tid}'")

[MEDIUM/   LOW]   B608 | REAL_VULNERABILITY   | server/routes/users.py:55
  Code: rows = await _sql(f"SELECT * FROM user_settings WHERE user_id = {{}}", [user["id"]])

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/webhooks.py:50
  Code: inv_rows = await _sql(f"SELECT tenant_id FROM invoices WHERE id = '{_safe_id(invoice_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/webhooks.py:67
  Code: payments = await _sql(f"SELECT * FROM payment WHERE invoice_id = '{_safe_id(invoice_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/webhooks.py:68
  Code: invs = await _sql(f"SELECT * FROM invoices WHERE id = '{_safe_id(invoice_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql

[MEDIUM/   LOW]   B608 | FALSE_POSITIVE       | server/routes/webhooks.py:155
  Code: rows = await _sql(f"SELECT * FROM webhook_subscriptions WHERE id = '{_safe_id(sub_id)}'")
  Note: Already sanitized with _safe_id or _sanitize_sql
