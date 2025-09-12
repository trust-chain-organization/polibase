-- Execute all migration files in order
-- This file is needed because PostgreSQL doesn't automatically execute files in subdirectories

\echo 'Running migrations...'

\i /docker-entrypoint-initdb.d/02_migrations/001_add_url_to_meetings.sql
\i /docker-entrypoint-initdb.d/02_migrations/002_add_members_list_url_to_political_parties.sql
\i /docker-entrypoint-initdb.d/02_migrations/003_add_politician_details.sql
\i /docker-entrypoint-initdb.d/02_migrations/004_add_gcs_uri_to_meetings.sql
\i /docker-entrypoint-initdb.d/02_migrations/005_add_members_introduction_url_to_conferences.sql
\i /docker-entrypoint-initdb.d/02_migrations/006_add_role_to_politician_affiliations.sql
\i /docker-entrypoint-initdb.d/02_migrations/007_create_extracted_conference_members_table.sql
\i /docker-entrypoint-initdb.d/02_migrations/008_create_parliamentary_groups_tables.sql
\i /docker-entrypoint-initdb.d/02_migrations/009_add_processed_at_to_minutes.sql
\i /docker-entrypoint-initdb.d/02_migrations/010_add_name_to_meetings.sql
\i /docker-entrypoint-initdb.d/02_migrations/011_add_organization_code_to_governing_bodies.sql
\i /docker-entrypoint-initdb.d/02_migrations/012_remove_conference_governing_body_fk.sql
\i /docker-entrypoint-initdb.d/02_migrations/013_create_llm_processing_history.sql
\i /docker-entrypoint-initdb.d/02_migrations/014_create_prompt_versions.sql
\i /docker-entrypoint-initdb.d/02_migrations/015_add_party_position_to_politicians.sql
\i /docker-entrypoint-initdb.d/02_migrations/016_add_created_by_to_llm_processing_history.sql
\i /docker-entrypoint-initdb.d/02_migrations/017_add_process_id_to_minutes.sql
\i /docker-entrypoint-initdb.d/02_migrations/018_add_matching_history_to_speakers.sql
\i /docker-entrypoint-initdb.d/02_migrations/019_add_performance_indexes.sql
\i /docker-entrypoint-initdb.d/02_migrations/020_add_attendees_mapping_to_meetings.sql
\i /docker-entrypoint-initdb.d/02_migrations/021_create_extracted_parliamentary_group_members_table.sql
\i /docker-entrypoint-initdb.d/02_migrations/022_add_proposal_metadata.sql
\i /docker-entrypoint-initdb.d/02_migrations/023_create_extracted_proposal_judges.sql

\echo 'Migrations completed.'
