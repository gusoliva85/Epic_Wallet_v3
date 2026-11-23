"""F17-T02 refresh_tokens

ID de revisión: a7b3c9d1e4f2
Revisión anterior: f1a2b3c4d5e6
Creada: 2026-11-23

Referencia: 02_Documento_Tecnico.md §8 · F17-T02

La tabla que sostiene una sesión de treinta días y, sobre todo, la que
permite **cortarla**. El token de acceso dura una hora y se verifica
con la clave pública, sin preguntarle a nadie: no hay forma de
revocarlo. Lo que sí se puede revocar es esto.

**Esta migración sólo CREA.** Una tabla nueva y vacía al lado de las
que ya están. No borra, no renombra y no toca ninguna fila existente.

La clave foránea apunta a `auth.users` y no a `profiles` —como hacen
las tablas de datos— porque una sesión es de la identidad, no del
perfil. En la práctica da igual: `profiles.id` **es** el uuid de
`auth.users`, así que la cascada llega por los dos lados.

Sin `grant` a `authenticated`, a propósito: estos endpoints corren con
el rol dueño, y ninguna petición de usuario necesita leer esta tabla.
La política de RLS está igual, por si una migración futura de permisos
por defecto le da acceso sin que nadie lo piense.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "a7b3c9d1e4f2"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _esquema() -> str:
    esquema = context.get_context().version_table_schema
    assert esquema, "la migración necesita un esquema explícito"
    return esquema


def upgrade() -> None:
    e = _esquema()

    op.create_table(
        "refresh_tokens",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=False),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=False), nullable=False),
        # SHA-256 en hexadecimal: 64 caracteres fijos. El token en
        # claro no se guarda en ningún lado.
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        # Todos los tokens que descienden del mismo login comparten
        # familia. Es lo que permite cortar una cadena entera cuando
        # aparece un token repetido, sin voltear las demás sesiones.
        sa.Column("familia", sa.dialects.postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["auth.users.id"],
            name="fk_refresh_tokens_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
        schema=e,
    )

    op.create_index("ix_refresh_tokens_familia", "refresh_tokens", ["familia"], schema=e)
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], schema=e)

    op.execute(f'alter table "{e}".refresh_tokens enable row level security;')
    op.execute(f'alter table "{e}".refresh_tokens force row level security;')
    op.execute(
        f"""
        create policy own_refresh_tokens on "{e}".refresh_tokens
          for all
          using (user_id = (select auth.uid()))
          with check (user_id = (select auth.uid()));
        """
    )


def downgrade() -> None:
    """Borra la tabla que esta misma migración creó.

    El efecto visible es que **todas las sesiones abiertas se caen**:
    cada uno vuelve a entrar con su contraseña. No se pierde ningún
    dato de contabilidad; acá no vive nada más que huellas de tokens.
    """
    e = _esquema()

    op.execute(f'drop policy if exists own_refresh_tokens on "{e}".refresh_tokens;')
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens", schema=e)
    op.drop_index("ix_refresh_tokens_familia", table_name="refresh_tokens", schema=e)
    op.drop_table("refresh_tokens", schema=e)
