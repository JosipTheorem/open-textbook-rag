-- Generated from Alembic migrations. Do not edit manually.

BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade -> 0001_create_schemas

CREATE SCHEMA IF NOT EXISTS textbook;

CREATE SCHEMA IF NOT EXISTS sandbox;

INSERT INTO alembic_version (version_num)
VALUES ('0001_create_schemas');

COMMIT;
