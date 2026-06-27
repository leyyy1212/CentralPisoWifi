from supabase import create_client

SUPABASE_URL = "https://dxbwjprztwyczkaycjtk.supabase.co"
SUPABASE_KEY = "sb_publishable_IcJ3Qa-7ju8E_ZG8GB2GeA_2kCBXSwo"

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

response = supabase.table("vouchers").select("*").execute()

print(response.data)