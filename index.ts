// Supabase Edge Function - מתווך (proxy) לשליפת שערי מניות מ-Yahoo Finance
// פותר את בעיית ה-CORS שמונעת מהדפדפן לקרוא ישירות ל-Yahoo.
//
// פריסה (מתוך Supabase Studio, בלי צורך ב-CLI):
// Studio → Edge Functions → Create a new function → שם: yahoo-quote
// הדבק את התוכן הזה ולחץ Deploy.
//
// או מה-CLI: supabase functions deploy yahoo-quote

import { serve } from "https://deno.land/std@0.203.0/http/server.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const { ticker } = await req.json();
    if (!ticker) {
      return new Response(JSON.stringify({ error: "ticker is required" }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?includePrePost=true`;
    const res = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0" },
    });

    if (!res.ok) {
      return new Response(JSON.stringify({ error: "upstream error", status: res.status }), {
        status: 502,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const data = await res.json();
    return new Response(JSON.stringify(data), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
