-- הרצה ב-Supabase Studio > SQL Editor
-- טבלה זו מאחסנת את תוצאות הסריקה היומית שמריץ ה-GitHub Action

create table if not exists screener_results (
  id uuid primary key default gen_random_uuid(),
  ticker text not null,
  price numeric,
  sma20 numeric,
  sma50 numeric,
  sma200 numeric,
  rsi14 numeric,
  avg_volume_20 numeric,
  pct_from_52w_high numeric,
  scan_date date not null default current_date,
  created_at timestamptz default now()
);

create index if not exists idx_screener_scan_date on screener_results(scan_date);

alter table screener_results enable row level security;

-- קריאה פתוחה לכולם (הדשבורד קורא עם anon key)
create policy "public read - screener_results" on screener_results
  for select using (true);

-- שים לב: אין כאן policy לכתיבה (insert/update/delete) עבור anon.
-- ה-GitHub Action כותב באמצעות ה-service_role key (עוקף RLS), שלא נחשף בדפדפן.
