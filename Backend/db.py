import logging
from supabase import create_client, Client
from config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Supabase Client
try:
    supabase: Client = create_client(settings.supabase_url, settings.supabase_key)
except Exception as e:
    logger.critical(f"Failed to initialize Supabase client: {e}")
    raise

