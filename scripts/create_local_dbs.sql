-- Run this script as a PostgreSQL superuser (or role with CREATEDB/CREATEROLE).
-- Values below match the defaults from .env.local.example.

CREATE USER app_user WITH PASSWORD 'app_password';
CREATE DATABASE app_db OWNER app_user;

CREATE USER portal_user WITH PASSWORD 'portal_password';
CREATE DATABASE portal_db OWNER portal_user;
