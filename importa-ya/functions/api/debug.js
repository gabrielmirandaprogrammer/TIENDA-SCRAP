// TEMPORAL: diagnostico de variables (solo dice si existen, nunca sus valores)
export async function onRequestGet({ env }) {
  return Response.json({
    MP_ACCESS_TOKEN: Boolean(env.MP_ACCESS_TOKEN),
    SUPABASE_URL: Boolean(env.SUPABASE_URL),
    SUPABASE_SERVICE_ROLE_KEY: Boolean(env.SUPABASE_SERVICE_ROLE_KEY),
    VITE_SUPABASE_URL: Boolean(env.VITE_SUPABASE_URL),
    VITE_SUPABASE_ANON_KEY: Boolean(env.VITE_SUPABASE_ANON_KEY),
  });
}