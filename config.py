"""Configuration module for proyectoRodrigo insurance agent."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Anthropic API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

# YCloud Configuration
YCLOUD_API_KEY = os.getenv("YCLOUD_API_KEY")
YCLOUD_API_BASE_URL = "https://api.ycloud.com/v2"

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Server Configuration
PORT = int(os.getenv("PORT", "8000"))


def validate_config():
    """Validate that all required configuration is present."""
    missing = []

    if not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not YCLOUD_API_KEY:
        missing.append("YCLOUD_API_KEY")
    if not SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not SUPABASE_KEY:
        missing.append("SUPABASE_KEY")

    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    print("Configuration validated successfully")
    print(f"  Claude model: {CLAUDE_MODEL}")
    print(f"  Supabase URL: {SUPABASE_URL[:30]}...")
    print(f"  Server port: {PORT}")
