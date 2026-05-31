-- Executed once by postgres:16-alpine on first container start.
-- Creates all nine service databases within the single shared PostgreSQL instance.
-- docker-entrypoint-initdb.d runs scripts in alphabetical order; this file
-- is mounted as /docker-entrypoint-initdb.d/init.sql.

CREATE DATABASE inventory;
CREATE DATABASE party;
CREATE DATABASE sellout;
CREATE DATABASE sellin;
CREATE DATABASE performance;
CREATE DATABASE commission_rules;
CREATE DATABASE commission_calc;
CREATE DATABASE payout;
CREATE DATABASE audit;
