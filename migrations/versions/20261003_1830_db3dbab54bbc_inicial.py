"""inicial · el esquema `auth`, que antes ponía el proveedor

ID de revisión: db3dbab54bbc
Revisión anterior:
Creada: 2026-10-03 18:30:23.002003-03:00
Reescrita: 2026-11-23 · F16-T01

POR QUÉ ESTO VA ACÁ Y NO EN UNA MIGRACIÓN NUEVA

La migración que sigue (`a1c4e7f20b83`, profiles) declara una clave
foránea contra `auth.users` y, dos migraciones después, un trigger que
dispara al dar de alta un usuario. O sea: el esquema `auth` tiene que
existir **antes** de la segunda migración de la cadena. Una migración
nueva sólo puede ir al final, donde no sirve.

Esta revisión era un `pass` —el punto de partida vacío de Alembic— y
es el único lugar donde el shim entra sin reordenar la cadena. Las
otras once migraciones y las nueve políticas RLS quedan intactas, que
es exactamente lo que pide la fase.

QUÉ ES UN SHIM Y POR QUÉ ALCANZA CON TAN POCO

El acoplamiento al proveedor anterior eran tres cosas: la tabla
`auth.users`, la función `auth.uid()` y su servicio de login. Las dos
primeras se recrean acá, con la misma forma y el mismo nombre. La
tercera la reemplaza la Fase 17.

`auth.uid()` lee `request.jwt.claims`, la misma variable de sesión que
`core/db.py` ya viene seteando en cada transacción. Como el nombre y
el comportamiento son idénticos, las políticas RLS no se enteran del
cambio: siguen diciendo `where user_id = auth.uid()` y siguen
funcionando.

EN SQLITE NO HACE NADA

SQLite no tiene esquemas, ni roles, ni RLS. Las pruebas de cálculo que
corren ahí no necesitan nada de esto.
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "db3dbab54bbc"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _es_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _es_postgres():
        return

    conexion = op.get_bind()

    # ---------------------------------------------------------------
    # 1 · El esquema
    # ---------------------------------------------------------------
    op.execute("create schema if not exists auth;")

    # ---------------------------------------------------------------
    # 2 · Los dos roles
    #
    # `create role` no admite `if not exists`, así que se pregunta
    # primero. Son roles sin login: nadie se conecta como ellos, la
    # aplicación los adopta con `set local role` dentro de una
    # transacción y los suelta al terminar.
    # ---------------------------------------------------------------
    for rol in ("anon", "authenticated"):
        existe = conexion.execute(
            text("select 1 from pg_roles where rolname = :r"), {"r": rol}
        ).scalar()
        if not existe:
            op.execute(f"create role {rol} nologin;")

    # Sin esto `set local role authenticated` falla con «permission
    # denied to set role». El usuario de la aplicación tiene que ser
    # miembro del rol que quiere adoptar — es el permiso que antes
    # venía dado de fábrica y que acá hay que otorgar a mano.
    usuario = conexion.execute(text("select current_user")).scalar()
    op.execute(f'grant authenticated to "{usuario}";')
    op.execute(f'grant anon to "{usuario}";')

    op.execute("grant usage on schema auth to anon, authenticated;")

    # ---------------------------------------------------------------
    # 3 · La tabla de cuentas
    #
    # Lo que `profiles` necesita para su clave foránea, lo que la Fase
    # 17 necesita para autenticar, y `raw_user_meta_data`, que lee el
    # trigger `crear_perfil_y_categorias` para sacar el nombre a
    # mostrar. Esa última no estaba en el plan y la encontró la prueba
    # de alta: sin ella el trigger falla con «record "new" has no
    # field "raw_user_meta_data"» y la cuenta nueva nace sin perfil y
    # sin sus 21 categorías.
    #
    # `encrypted_password` guarda un hash bcrypt, con el mismo formato
    # que el proveedor anterior — por eso nadie tiene que resetear su
    # contraseña cuando los datos se muden.
    # ---------------------------------------------------------------
    op.execute(
        """
        create table if not exists auth.users (
            id                 uuid primary key default gen_random_uuid(),
            email              text        not null unique,
            encrypted_password text        not null,
            email_confirmed_at timestamptz,
            raw_user_meta_data jsonb       not null default '{}'::jsonb,
            created_at         timestamptz not null default now()
        );
        """
    )

    # ---------------------------------------------------------------
    # 4 · La función que sostiene todas las políticas RLS
    #
    # Va ANTES del RLS de abajo: la política de `auth.users` la
    # llama, y Postgres valida la expresión al crear la política.
    #
    # `stable` y no `volatile`: dentro de una consulta el valor no
    # cambia, así que Postgres puede evaluarla una sola vez en lugar de
    # una por fila. Con `volatile` cada política pagaría la llamada en
    # cada fila examinada.
    #
    # El `true` de `current_setting` es «no revientes si no está
    # definida»: devuelve nulo. Sin sesión, `auth.uid()` es nulo y las
    # políticas no dejan ver ninguna fila, que es lo correcto.
    # ---------------------------------------------------------------
    op.execute(
        """
        create or replace function auth.uid() returns uuid
        language sql stable
        as $$
          select nullif(
            current_setting('request.jwt.claims', true)::json ->> 'sub',
            ''
          )::uuid
        $$;
        """
    )
    op.execute("grant execute on function auth.uid() to anon, authenticated;")

    # ---------------------------------------------------------------
    # 5 · Que una cuenta no pueda leer la fila de otra, ni su hash
    # ---------------------------------------------------------------
    op.execute("alter table auth.users enable row level security;")
    op.execute("alter table auth.users force row level security;")
    op.execute("drop policy if exists own_user on auth.users;")
    op.execute(
        """
        create policy own_user on auth.users
          for select
          to authenticated
          using (id = (select auth.uid()));
        """
    )
    op.execute("grant select on auth.users to authenticated;")


def downgrade() -> None:
    if not _es_postgres():
        return

    # El esquema entero, con la tabla y la función adentro. Los roles
    # se dejan: pueden ser de otra base del mismo servidor, y en
    # Postgres los roles son globales, no del esquema.
    op.execute("drop schema if exists auth cascade;")
