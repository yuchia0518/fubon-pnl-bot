import { serve } from "https://deno.land/std@0.224.0/http/server.ts";
import { createClient } from "@supabase/supabase-js";

// AES-256-CBC encrypt, output compatible with Python crypto_utils.decrypt()
async function encrypt(plainText: string, masterKeyHex: string): Promise<string> {
  const keyBytes = hexToBytes(masterKeyHex);
  const key = await crypto.subtle.importKey(
    "raw", keyBytes, { name: "AES-CBC" }, false, ["encrypt"]
  );
  const iv = crypto.getRandomValues(new Uint8Array(16));
  const encoded = new TextEncoder().encode(plainText);
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-CBC", iv }, key, encoded);
  // Combine iv + ciphertext (same format as Python: base64(iv + ciphertext))
  const combined = new Uint8Array(iv.length + ciphertext.byteLength);
  combined.set(iv, 0);
  combined.set(new Uint8Array(ciphertext), iv.length);
  let binary = '';
  const bytes = new Uint8Array(combined);
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function hexToBytes(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substring(i, i + 2), 16);
  }
  return bytes;
}

serve(async (req) => {
  if (req.method !== "POST") {
    return new Response("Method not allowed", { status: 405 });
  }

  const mk = Deno.env.get("MASTER_KEY");
  if (!mk) {
    console.error("MASTER_KEY not set");
    return new Response(JSON.stringify({ error: "Configuration error" }), {
      status: 500, headers: { "Content-Type": "application/json" },
    });
  }

  try {
    const body = await req.json();
    const { name, line_user_id, fubon_username, fubon_password, fubon_ca_content, fubon_ca_password } = body;

    if (!name || !line_user_id || !fubon_username || !fubon_password || !fubon_ca_content || !fubon_ca_password) {
      return new Response(JSON.stringify({ error: "Missing required fields" }), {
        status: 400, headers: { "Content-Type": "application/json" },
      });
    }

    const supaUrl = Deno.env.get("SUPABASE_URL")!;
    const supaKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
    if (!supaUrl || !supaKey) {
      console.error("Supabase credentials not configured");
      return new Response(JSON.stringify({ error: "Configuration error" }), {
        status: 500, headers: { "Content-Type": "application/json" },
      });
    }

    const supabase = createClient(supaUrl, supaKey);

    const encrypted = {
      fubon_username: await encrypt(fubon_username, mk),
      fubon_password: await encrypt(fubon_password, mk),
      fubon_ca_content: await encrypt(fubon_ca_content, mk),
      fubon_ca_password: await encrypt(fubon_ca_password, mk),
    };

    const { data, error } = await supabase
      .from("users")
      .upsert({
        name,
        line_user_id,
        ...encrypted,
        ct_id: "setup_web",
      }, { onConflict: "line_user_id" })
      .select();

    if (error) throw error;

    return new Response(JSON.stringify({ success: true, user: data }), {
      status: 200, headers: { "Content-Type": "application/json" },
    });
  } catch (e) {
    console.error("Unhandled error:", e);
    return new Response(JSON.stringify({ error: "Internal server error" }), {
      status: 500, headers: { "Content-Type": "application/json" },
    });
  }
});
