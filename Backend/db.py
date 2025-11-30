import logging
from supabase import create_client, Client
from config import settings

# Configuring logging
logger = logging.getLogger(__name__)

# Initializing Supabase Client
try:
    supabase: Client = create_client(settings.supabase_url, settings.supabase_key)
except Exception as e:
    logger.critical(f"Failed to initialize Supabase client: {e}")
    raise

