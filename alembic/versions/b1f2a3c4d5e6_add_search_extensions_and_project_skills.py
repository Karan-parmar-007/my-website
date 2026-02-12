"""Add search extensions project_skill table and tsvector

Revision ID: b1f2a3c4d5e6
Revises: a1b2c3d4e5f6
Create Date: 2026-02-11 16:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b1f2a3c4d5e6'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable required extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")

    # 2. Create project_skill M2M link table
    op.create_table(
        'project_skill',
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('skill.id', ondelete='CASCADE'), primary_key=True),
    )

    # 3. Migrate existing skills_used data to project_skill
    op.execute("""
        INSERT INTO project_skill (project_id, skill_id)
        SELECT p.id, s.id
        FROM projects p, unnest(p.skills_used) AS skill_name
        JOIN skill s ON LOWER(s.name) = LOWER(skill_name)
        ON CONFLICT DO NOTHING;
    """)

    # 4. Drop skills_used column from projects
    op.drop_column('projects', 'skills_used')

    # 5. Add trigram GIN indexes on users
    op.execute("CREATE INDEX ix_users_preferred_name_trgm ON users USING gin (preferred_name gin_trgm_ops);")
    op.execute("CREATE INDEX ix_users_email_trgm ON users USING gin (email gin_trgm_ops);")

    # 6. Add search_vector tsvector column on projects
    op.add_column('projects', sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True))

    # 7. Create GIN index on search_vector
    op.execute("CREATE INDEX ix_projects_search_vector ON projects USING gin (search_vector);")

    # 8. Populate search_vector for existing rows (including skill names from project_skill)
    op.execute("""
        UPDATE projects SET search_vector =
            setweight(to_tsvector('english', COALESCE(name, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(short_description, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(long_description, '')), 'C') ||
            setweight(to_tsvector('english', COALESCE(
                (SELECT string_agg(s.name, ' ')
                 FROM project_skill ps JOIN skill s ON s.id = ps.skill_id
                 WHERE ps.project_id = projects.id), ''
            )), 'B');
    """)

    # 9. Create trigger function to auto-update search_vector on project changes
    op.execute("""
        CREATE OR REPLACE FUNCTION projects_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.short_description, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.long_description, '')), 'C') ||
                setweight(to_tsvector('english', COALESCE(
                    (SELECT string_agg(s.name, ' ')
                     FROM project_skill ps JOIN skill s ON s.id = ps.skill_id
                     WHERE ps.project_id = NEW.id), ''
                )), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_projects_search_vector
        BEFORE INSERT OR UPDATE OF name, short_description, long_description
        ON projects FOR EACH ROW
        EXECUTE FUNCTION projects_search_vector_update();
    """)

    # 10. Create trigger to refresh project search_vector when project_skill changes
    op.execute("""
        CREATE OR REPLACE FUNCTION project_skill_search_vector_update() RETURNS trigger AS $$
        DECLARE target_id UUID;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                target_id := OLD.project_id;
            ELSE
                target_id := NEW.project_id;
            END IF;
            -- Touch the project row to fire the UPDATE trigger
            UPDATE projects SET updated_at = now() WHERE id = target_id;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_project_skill_search_vector
        AFTER INSERT OR DELETE ON project_skill
        FOR EACH ROW EXECUTE FUNCTION project_skill_search_vector_update();
    """)


def downgrade() -> None:
    # Drop triggers and functions
    op.execute("DROP TRIGGER IF EXISTS trg_project_skill_search_vector ON project_skill;")
    op.execute("DROP FUNCTION IF EXISTS project_skill_search_vector_update();")
    op.execute("DROP TRIGGER IF EXISTS trg_projects_search_vector ON projects;")
    op.execute("DROP FUNCTION IF EXISTS projects_search_vector_update();")

    # Drop search_vector index and column
    op.execute("DROP INDEX IF EXISTS ix_projects_search_vector;")
    op.drop_column('projects', 'search_vector')

    # Drop trigram indexes on users
    op.execute("DROP INDEX IF EXISTS ix_users_email_trgm;")
    op.execute("DROP INDEX IF EXISTS ix_users_preferred_name_trgm;")

    # Re-create skills_used column and migrate data back
    op.add_column('projects', sa.Column('skills_used', postgresql.ARRAY(sa.VARCHAR()), nullable=True))

    op.execute("""
        UPDATE projects SET skills_used = (
            SELECT array_agg(s.name)
            FROM project_skill ps JOIN skill s ON s.id = ps.skill_id
            WHERE ps.project_id = projects.id
        );
    """)

    # Drop project_skill table
    op.drop_table('project_skill')

    # Extensions are left in place (dropping them could break other things)
