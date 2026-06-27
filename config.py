import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://dxbwjprztwyczkaycjtk.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_IcJ3Qa-7ju8E_ZG8GB2GeA_2kCBXSwo")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
