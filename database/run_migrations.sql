-- Run all migrations in the correct order
-- This file is executed during database initialization

-- Migration files are executed automatically by PostgreSQL in alphabetical order
-- from the /docker-entrypoint-initdb.d/migrations/ directory

-- This file serves as documentation of the migration order:
-- 001_add_url_to_meetings.sql
-- 002_add_members_list_url_to_political_parties.sql
-- 003_add_politician_details.sql
-- 004_add_gcs_uri_to_meetings.sql
-- 005_add_members_introduction_url_to_conferences.sql
-- 006_add_role_to_politician_affiliations.sql
-- 007_create_extracted_conference_members_table.sql
-- 008_create_parliamentary_groups_tables.sql
-- 009_add_processed_at_to_minutes.sql
-- 010_add_name_to_meetings.sql
-- 011_add_organization_code_to_governing_bodies.sql
-- 012_remove_conference_governing_body_fk.sql

-- Note: All migration files in the migrations directory are automatically executed
-- during PostgreSQL initialization in the Docker container
