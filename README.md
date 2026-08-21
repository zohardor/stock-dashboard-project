# דשבורד מניות - Stop Loss / Take Profit + סקרינר עצמאי

## מבנה הפרויקט
```
index.html                     - הדשבורד הראשי (פותחים בדפדפן / מארחים ב-GitHub Pages)
supabase-schema.sql             - טבלאות stocks + sold_stocks
screener-schema.sql             - טבלת screener_results
screener/screener.py            - סקריפט הסינון היומי
screener/requirements.txt       - תלויות Python
.github/workflows/screener.yml  - תזמון אוטומטי ל-GitHub Actions
```

## התקנה - שלב אחר שלב

### 1. Supabase
1. צור פרויקט חדש ב-supabase.com
2. ב-SQL Editor, הרץ קודם את `supabase-schema.sql`, ואז את `screener-schema.sql`
3. ב-Settings → API, שמור לצדך:
   - `Project URL`
   - `anon public key`
   - `service_role key` (סודי - לא לחשוף בדפדפן!)

### 2. עדכון index.html
פתח את `index.html` בעורך טקסט, מצא בראש תגית ה-`<script>`:
```js
const SUPABASE_URL = "https://YOUR-PROJECT.supabase.co";
const SUPABASE_ANON_KEY = "YOUR-ANON-KEY";
```
והחלף בערכים האמיתיים (Project URL + anon key בלבד, לא service key).

### 3. GitHub
1. צור repository חדש (יכול להיות פרטי)
2. העלה את כל התוכן של התיקייה הזו (כולל `.github/workflows/screener.yml`)
3. ב-Settings → Secrets and variables → Actions, הוסף שני secrets:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY` (ה-service_role key, לא ה-anon key)
4. אפשר להריץ ידנית: לשונית Actions → Daily Stock Screener → Run workflow

### 4. פרסום עם GitHub Pages (אופציונלי)
Settings → Pages → Source: הענף הראשי → Save.
תקבל כתובת קבועה כמו `https://USERNAME.github.io/REPO-NAME/`

## הערות אבטחה
- מדיניות ה-RLS שהוגדרה היא "גישה חופשית לקריאה/כתיבה" בטבלאות stocks/sold_stocks -
  מתאים לשימוש אישי עם קישור לא-מפורסם. לשימוש רחב יותר, מומלץ להוסיף Supabase Auth.
- טבלת screener_results ניתנת לקריאה בלבד מהדפדפן (anon key) - הכתיבה מתבצעת
  אך ורק דרך ה-service key ב-GitHub Action, שלא נחשף ללקוח.
- ה-service_role key **לעולם** לא נכנס ל-index.html או לכל קובץ שמתפרסם בדפדפן.
