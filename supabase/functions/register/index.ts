import { serve } from "https://deno.land/std@0.224.0/http/server.ts";
import { createClient } from "@supabase/supabase-js";

async function encrypt(plainText: string, masterKeyHex: string): Promise<string> {
  const keyBytes = hexToBytes(masterKeyHex);
  const key = await crypto.subtle.importKey("raw", keyBytes, { name: "AES-CBC" }, false, ["encrypt"]);
  const iv = crypto.getRandomValues(new Uint8Array(16));
  const encoded = new TextEncoder().encode(plainText);
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-CBC", iv }, key, encoded);
  const combined = new Uint8Array(iv.length + ciphertext.byteLength);
  combined.set(iv, 0);
  combined.set(new Uint8Array(ciphertext), iv.length);
  let binary = "";
  for (let i = 0; i < combined.byteLength; i++) binary += String.fromCharCode(combined[i]);
  return btoa(binary);
}

function hexToBytes(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) bytes[i / 2] = parseInt(hex.substring(i, i + 2), 16);
  return bytes;
}

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return new Response("Method not allowed", { status: 405, headers: corsHeaders });

  try {
    const body = await req.json();
    const { line_user_id, display_name, user_id, password, ca_content, cert_password } = body;

    if (!line_user_id || !user_id || !password || !ca_content || !cert_password) {
      return new Response(JSON.stringify({ error: "Missing required fields" }), {
        status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const mk = Deno.env.get("MASTER_KEY");
    const supaUrl = Deno.env.get("SUPABASE_URL");
    const supaKey = Deno.env.get("SERVICE_ROLE_KEY");
    if (!mk || !supaUrl || !supaKey) {
      return new Response(JSON.stringify({ error: "Configuration error" }), {
        status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const supabase = createClient(supaUrl, supaKey);

    const encrypted = {
      fubon_username: await encrypt(user_id.toUpperCase(), mk),
      fubon_password: await encrypt(password, mk),
      fubon_ca_content: await encrypt(ca_content, mk),
      fubon_ca_password: await encrypt(cert_password, mk),
    };

    const upsertData = {
      name: display_name || user_id,
      line_user_id,
      ...encrypted,
      ct_id: "setup_web",
    };

    const { data: existing } = await supabase
      .from("users")
      .select("id")
      .eq("line_user_id", line_user_id)
      .maybeSingle();

    let result;
    if (existing) {
      result = await supabase.from("users").update(upsertData).eq("line_user_id", line_user_id).select();
    } else {
      result = await supabase.from("users").insert(upsertData).select();
    }

    if (result.error) throw result.error;

    return new Response(JSON.stringify({ success: true, user: result.data }), {
      status: 200, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("Error:", e);
    const msg = e instanceof Error ? e.message : JSON.stringify(e);
    return new Response(JSON.stringify({ error: msg }), {
      status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
