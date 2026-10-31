SET ROLE marketatlas_writer;

-- Rename only the serving pointer. Retained builds, snapshots, facts and
-- original publication time remain unchanged.
DO $migration$
BEGIN
    LOCK TABLE atlas.publication IN SHARE ROW EXCLUSIVE MODE;
    IF EXISTS (SELECT 1 FROM atlas.publication WHERE publication_name = 'default')
       AND EXISTS (SELECT 1 FROM atlas.publication WHERE publication_name = 'synthetic_fixture') THEN
        RAISE EXCEPTION 'Both legacy and synthetic_fixture publications exist; refusing to replace either pointer';
    END IF;

    UPDATE atlas.publication
    SET publication_name = 'synthetic_fixture'
    WHERE publication_name = 'default';

    -- Prevent an older fixture producer from silently recreating the old name.
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'atlas.publication'::regclass
          AND conname = 'publication_explicit_fixture_name'
    ) THEN
        ALTER TABLE atlas.publication
            ADD CONSTRAINT publication_explicit_fixture_name
            CHECK (publication_name <> 'default');
    END IF;
END
$migration$;

RESET ROLE;
