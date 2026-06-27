-- annex.sql — base annexe interne (généré par build_db.py)
-- NE PAS éditer à la main : source de vérité = data/canonical.py
PRAGMA foreign_keys = OFF;

DROP TABLE IF EXISTS customer_claims;
CREATE TABLE customer_claims (
    id INTEGER PRIMARY KEY,
    customer_ref TEXT,
    shipment_ref TEXT,
    type TEXT,
    opened_at TEXT,
    closed_at TEXT,
    status TEXT
);
INSERT INTO customer_claims (id, customer_ref, shipment_ref, type, opened_at, closed_at, status) VALUES (1, 'C003', 'SH-2060', 'Billing dispute', '2026-01-11', '2026-01-18', 'closed');
INSERT INTO customer_claims (id, customer_ref, shipment_ref, type, opened_at, closed_at, status) VALUES (2, 'C003', 'SH-2061', 'Temperature breach', '2026-04-09', '2026-04-26', 'closed');
INSERT INTO customer_claims (id, customer_ref, shipment_ref, type, opened_at, closed_at, status) VALUES (3, 'C005', 'SH-2065', 'Billing dispute', '2026-01-22', '2026-02-07', 'closed');
INSERT INTO customer_claims (id, customer_ref, shipment_ref, type, opened_at, closed_at, status) VALUES (4, 'C015', 'SH-2057', 'Wrong quantity', '2026-01-21', '2026-02-10', 'closed');
INSERT INTO customer_claims (id, customer_ref, shipment_ref, type, opened_at, closed_at, status) VALUES (5, 'C011', 'SH-2070', 'Temperature breach', '2025-10-20', '2025-11-19', 'closed');
INSERT INTO customer_claims (id, customer_ref, shipment_ref, type, opened_at, closed_at, status) VALUES (6, 'C009', 'SH-2075', 'Wrong quantity', '2026-03-30', '2026-04-22', 'closed');
INSERT INTO customer_claims (id, customer_ref, shipment_ref, type, opened_at, closed_at, status) VALUES (7, 'C010', NULL, 'Damaged goods', '2025-09-10', '2025-09-18', 'closed');
INSERT INTO customer_claims (id, customer_ref, shipment_ref, type, opened_at, closed_at, status) VALUES (8, 'C014', 'SH-2064', 'Damaged goods', '2025-08-31', '2025-09-19', 'closed');
INSERT INTO customer_claims (id, customer_ref, shipment_ref, type, opened_at, closed_at, status) VALUES (9, 'C017', 'SH-2069', 'Damaged goods', '2026-04-27', '2026-05-01', 'closed');
INSERT INTO customer_claims (id, customer_ref, shipment_ref, type, opened_at, closed_at, status) VALUES (10, 'C013', 'SH-2065', 'Damaged goods', '2026-04-22', '2026-05-12', 'closed');
INSERT INTO customer_claims (id, customer_ref, shipment_ref, type, opened_at, closed_at, status) VALUES (11, 'C016', 'SH-2065', 'Damaged goods', '2025-09-09', '2025-09-27', 'closed');
INSERT INTO customer_claims (id, customer_ref, shipment_ref, type, opened_at, closed_at, status) VALUES (12, 'C006', 'SH-2075', 'Wrong quantity', '2025-11-10', '2025-12-06', 'closed');

DROP TABLE IF EXISTS sla_penalty_log;
CREATE TABLE sla_penalty_log (
    id INTEGER PRIMARY KEY,
    customer_ref TEXT,
    shipment_ref TEXT,
    hours_late INTEGER,
    penalty_amount INTEGER,
    month TEXT
);
INSERT INTO sla_penalty_log (id, customer_ref, shipment_ref, hours_late, penalty_amount, month) VALUES (1, 'C003', 'SH-2063', 1, 2000, '2026-02');
INSERT INTO sla_penalty_log (id, customer_ref, shipment_ref, hours_late, penalty_amount, month) VALUES (2, 'C017', 'SH-2056', 5, 5000, '2025-10');
INSERT INTO sla_penalty_log (id, customer_ref, shipment_ref, hours_late, penalty_amount, month) VALUES (3, 'C011', 'SH-2060', 8, 8000, '2026-01');
INSERT INTO sla_penalty_log (id, customer_ref, shipment_ref, hours_late, penalty_amount, month) VALUES (4, 'C017', 'SH-2071', 2, 4000, '2026-05');
INSERT INTO sla_penalty_log (id, customer_ref, shipment_ref, hours_late, penalty_amount, month) VALUES (5, 'C002', 'SH-2073', 6, 6000, '2026-02');
INSERT INTO sla_penalty_log (id, customer_ref, shipment_ref, hours_late, penalty_amount, month) VALUES (6, 'C003', 'SH-2076', 6, 9000, '2025-11');

DROP TABLE IF EXISTS legacy_contacts;
CREATE TABLE legacy_contacts (
    id INTEGER PRIMARY KEY,
    raw_name TEXT,
    email TEXT,
    phone TEXT,
    notes TEXT
);
INSERT INTO legacy_contacts (id, raw_name, email, phone, notes) VALUES (1, 'Med Pharma SARL', 'contact@medpharma.com', '01 42 11 22 33', 'Ancien contact - voir compte principal pharma');
INSERT INTO legacy_contacts (id, raw_name, email, phone, notes) VALUES (2, 'MEDPHARMA (old)', 'old.billing@medpharma.com', '01 42 11 22 30', 'Doublon probable - a fusionner');
INSERT INTO legacy_contacts (id, raw_name, email, phone, notes) VALUES (3, 'FreshMarket SA', 'achats@freshmarket.fr', '04 91 00 11 22', '');
INSERT INTO legacy_contacts (id, raw_name, email, phone, notes) VALUES (4, 'SANCHEZ', 'michelle07@rossi.com', '0486656489', '');
INSERT INTO legacy_contacts (id, raw_name, email, phone, notes) VALUES (5, 'DELAHAYE', 'meuniercapucine@benard.org', '+33 (0)2 57 62 74 92', 'verifier');
INSERT INTO legacy_contacts (id, raw_name, email, phone, notes) VALUES (6, 'LÉVY', 'llebon@wagner.com', '0545154712', 'contact perdu');
INSERT INTO legacy_contacts (id, raw_name, email, phone, notes) VALUES (7, 'BOUVIER S.A.', 'dumaslucy@benoit.net', '0604495654', 'verifier');
INSERT INTO legacy_contacts (id, raw_name, email, phone, notes) VALUES (8, 'MARTINEZ S.A.R.L.', 'devauxrobert@da.fr', '04 56 49 96 89', 'old');
INSERT INTO legacy_contacts (id, raw_name, email, phone, notes) VALUES (9, 'RAYNAUD PELTIER SARL', 'coulonjules@perrot.com', '+33 2 72 59 04 76', 'verifier');
INSERT INTO legacy_contacts (id, raw_name, email, phone, notes) VALUES (10, 'PELTIER ET FILS', 'simone88@lejeune.com', '+33 2 32 05 47 72', 'RAS');
INSERT INTO legacy_contacts (id, raw_name, email, phone, notes) VALUES (11, 'LEDUC PHILIPPE SA', 'sevrard@langlois.org', '+33 (0)4 15 96 37 82', '');

