-- Grant the MarketAtlas source reader a fixed, read-only discovery surface.
-- Deliberately omit public.agent_* operational tables and default privileges.

GRANT USAGE ON SCHEMA audit, bronze, gold, meta, silver TO marketatlas_source_reader;

GRANT SELECT ON ALL TABLES IN SCHEMA audit, bronze, gold, meta, silver
    TO marketatlas_source_reader;
