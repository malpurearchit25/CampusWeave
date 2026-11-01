# Rubric evidence map

| Rubric | Marks | Concrete evidence |
| --- | --- | --- |
| Requirement analysis and complete ER diagram | 15 | PROJECT_REPORT sections 1-2; ER_complete.svg; academic/scheduling detail diagrams; metadata-derived dictionary. |
| Schema design and normalization | 15 | sql/01_schema.sql; report section 3; candidate keys, functional dependencies, 1NF-3NF decomposition and mapping table. |
| SQL and PL/SQL implementation | 20 | Query showcase; sp_validate_run; sp_publish_run called by the UI; insert/update/delete guards; automatic audit trigger; separate Oracle PL/SQL lab. |
| Query optimization and transaction processing | 15 | Controlled 60,000-row EXPLAIN benchmark; evidence.json; live rollback/savepoint lab; failed-write rollback and concurrent publication tests. |
| Architecture and application functionality | 15 | architecture.svg; running Flask/MySQL application; authenticated catalog CRUD; cross-semester scheduler; weekly grid, publication, archive, CSV and print; tests. |
| Report, demonstration and viva | 20 | CampusWeave_Report.pdf; editable PROJECT_REPORT.md; eight-minute demo plan; viva answers; UI screenshots and test results. |

This is an evidence map, not a promise of marks. The institution decides scoring. MySQL and Oracle dialects are clearly distinguished; the Oracle companion has been executed on Oracle 21c and includes rerunnable evidence.
