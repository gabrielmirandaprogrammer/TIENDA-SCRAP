from supabase_config import supabase

resultado = (
    supabase
    .table("proveedores")
    .select("*")
    .execute()
)

print(resultado.data)