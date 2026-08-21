-- הרצה ב-Supabase Studio > SQL Editor

create table if not exists stocks (
  id uuid primary key default gen_random_uuid(),
  ticker text,
  current numeric,
  purchase numeric,
  quantity numeric,
  stop_loss numeric,
  take_profit numeric,
  auto_update boolean default false,
  created_at timestamptz default now()
);

create table if not exists sold_stocks (
  id uuid primary key default gen_random_uuid(),
  ticker text,
  purchase numeric,
  sell_price numeric,
  quantity numeric,
  sold_at timestamptz default now()
);

alter table stocks enable row level security;
alter table sold_stocks enable row level security;

-- מדיניות פשוטה: גישה חופשית לכל מי שמחזיק את ה-anon key (שימוש אישי בלבד).
-- אם תוסיף Supabase Auth בהמשך, יש להחליף ל: using (auth.uid() = user_id)
create policy "allow all - stocks" on stocks for all using (true) with check (true);
create policy "allow all - sold_stocks" on sold_stocks for all using (true) with check (true);
