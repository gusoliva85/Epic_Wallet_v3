"""F17-T04 password_resets

ID de revisión: b8c4d2e5f3a1
Revisión anterior: a7b3c9d1e4f2
Creada: 2026-11-23

Referencia: 01_Documento_General.md §48.1 · F17-T04

La tabla que hace que un enlace de contraseña nueva valga una sola vez
y por media hora. Los enlaces se generan a mano con
`python -m app.cli recuperar <email>`: no hay ningún endpoint que
alguien de afuera pueda llamar para que se emita uno.

**Esta migración sólo CREA.** Una tabla nueva y vacía al lado de las
que ya están. No borra, no renombra y no toca ninguna fila existente.

Sin `grant` a `authenticated`, igual que `refresh_tokens`: el endpoint
que la usa corre con el rol dueño y ninguna petición de usuario
necesita leerla. La política de RLS está de todos modos, por si una
migración futura de permisos por defecto le da acceso sin que nadie lo
piense.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "b8c4d2e5f3a1"
down_revision: str | None = "a7b3c9d1e4f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _esquema() -> str:
    esquema = context.get_context().version_table_schema
    assert esquema, "la migración necesita un esquema explícito"
    return esquema


def upgrade() -> None:
    e = _esquema()

    op.create_table(
        "password_resets",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=False),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_password_resets"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth.users.id"],
            name="fk_password_resets_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("token_hash", name="uq_password_resets_token_hash"),
        schema=e,
    )

    op.create_index("ix_password_resets_user_id", "password_resets", ["user_id"], schema=e)

    op.execute(f'alter table "{e}".password_resets enable row level security;')
    op.execute(f'alter table "{e}".password_resets force row level security;')
    op.execute(
        f"""
        create policy own_password_resets on "{e}".password_resets
          for all
          using (user_id = (select auth.uid()))
          with check (user_id = (select auth.uid()));
        """
    )


def downgrade() -> None:
    """Borra la tabla que esta misma migración creó.

    El efecto visible es que los enlaces de contraseña nueva que estén
    dando vueltas dejan de servir. No se pierde ningún dato de
    contabilidad ni ninguna sesión abierta.
    """
    e = _esquema()

    op.execute(f'drop policy if exists own_password_resets on "{e}".password_resets;')
    op.drop_index("ix_password_resets_user_id", table_name="password_resets", schema=e)
    op.drop_table("password_resets", schema=e)
