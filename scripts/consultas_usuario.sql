-- ===================================================================
-- Todo lo cargado por una cuenta, para mirar en el SQL Editor de
-- Supabase. SÓLO LECTURA: ni un insert, ni un update, ni un delete.
--
-- Reemplazá el id de abajo por el de la cuenta que quieras mirar.
-- Para encontrarlo por correo:
--     select id, email, created_at from auth.users order by created_at;
-- ===================================================================

\set uid '9d5feb95-a34b-4e1a-928e-164a1a5fe45f'

-- ------------------------------------------------- 1 · los movimientos
-- Lo que pediste: todos sus movimientos, del más nuevo al más viejo,
-- con el nombre de la categoría y el mes al que pertenecen.
select t.transaction_date      as fecha,
       t.transaction_type      as tipo,
       c.name                  as categoria,
       t.amount                as importe,
       t.description           as descripcion,
       m.year || '-' || lpad(m.month::text, 2, '0') as mes,
       t.created_at            as cargado
  from public.transactions t
  join public.categories   c on c.id = t.category_id
  join public.months       m on m.id = t.month_id
 where t.user_id = '9d5feb95-a34b-4e1a-928e-164a1a5fe45f'
 order by t.transaction_date desc, t.created_at desc;

-- ------------------------------------------------------- 2 · sus meses
select year, month, status,
       income_total, expense_total, saving_total, closing_balance,
       created_at, updated_at
  from public.months
 where user_id = '9d5feb95-a34b-4e1a-928e-164a1a5fe45f'
 order by year desc, month desc;

-- ------------------------------- 3 · los totales por categoría del mes
select m.year, m.month, c.name as categoria, c.type as tipo,
       mct.total_amount, mct.is_manual_summary
  from public.monthly_category_totals mct
  join public.months     m on m.id = mct.month_id
  join public.categories c on c.id = mct.category_id
 where mct.user_id = '9d5feb95-a34b-4e1a-928e-164a1a5fe45f'
 order by m.year desc, m.month desc, mct.total_amount desc;

-- --------------------------------------------------- 4 · su perfil
select id, display_name, opening_balance, timezone, created_at, updated_at
  from public.profiles
 where id = '9d5feb95-a34b-4e1a-928e-164a1a5fe45f';

-- ------------------------------------------------ 5 · sus categorías
select id, name, type, active, sort_order, created_at
  from public.categories
 where user_id = '9d5feb95-a34b-4e1a-928e-164a1a5fe45f'
 order by type, sort_order;

-- ---------------------------------------- 6 · inversiones y pasivos
select * from public.investments
 where user_id = '9d5feb95-a34b-4e1a-928e-164a1a5fe45f';

select * from public.liabilities
 where user_id = '9d5feb95-a34b-4e1a-928e-164a1a5fe45f';

-- ------------------------------------------------ 7 · preferencias
select key, value, updated_at
  from public.app_settings
 where user_id = '9d5feb95-a34b-4e1a-928e-164a1a5fe45f';

-- ------------------------------- 8 · vencimientos (tabla nueva, F13)
select * from public.category_dues
 where user_id = '9d5feb95-a34b-4e1a-928e-164a1a5fe45f';

-- ------------------------------------------- 9 · resumen de una línea
select (select count(*) from public.transactions            where user_id = '9d5feb95-a34b-4e1a-928e-164a1a5fe45f') as movimientos,
       (select count(*) from public.months                  where user_id = '9d5feb95-a34b-4e1a-928e-164a1a5fe45f') as meses,
       (select count(*) from public.categories              where user_id = '9d5feb95-a34b-4e1a-928e-164a1a5fe45f') as categorias,
       (select count(*) from public.monthly_category_totals where user_id = '9d5feb95-a34b-4e1a-928e-164a1a5fe45f') as totales,
       (select count(*) from public.investments             where user_id = '9d5feb95-a34b-4e1a-928e-164a1a5fe45f') as inversiones,
       (select coalesce(sum(amount), 0) from public.transactions
         where user_id = '9d5feb95-a34b-4e1a-928e-164a1a5fe45f' and transaction_type = 'expense') as total_egresos,
       (select coalesce(sum(amount), 0) from public.transactions
         where user_id = '9d5feb95-a34b-4e1a-928e-164a1a5fe45f' and transaction_type = 'income') as total_ingresos;
