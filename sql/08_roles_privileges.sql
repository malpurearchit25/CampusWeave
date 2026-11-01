-- Administrator demonstration; replace the database/user names for your installation.
-- The automated lab creates and removes an isolated non-login role and records SHOW GRANTS.
-- CREATE ROLE 'campus_reader';
-- GRANT SELECT ON campusweave.* TO 'campus_reader';
-- GRANT 'campus_reader' TO 'a_real_user'@'localhost';
-- SET DEFAULT ROLE 'campus_reader' TO 'a_real_user'@'localhost';
-- REVOKE SELECT ON campusweave.* FROM 'campus_reader';
-- DROP ROLE 'campus_reader';
SHOW GRANTS FOR CURRENT_USER;

-- SQL-standard CREATE ASSERTION is unsupported by MySQL.
-- A conceptual assertion: no faculty has overlapping published periods.
-- CampusWeave implements that invariant through sp_validate_run, publication locking,
-- entry guards and a publication trigger; it does not claim CREATE ASSERTION executes here.
