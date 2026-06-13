#!/usr/bin/env python3
"""SYLENTH Agent - Quick Test Script"""
import sys

def test_all():
    print("🧪 SYLENTH Agent - Quick Test")
    print("="*50)
    
    # Test imports
    try:
        import aiogram, openai, aiohttp
        from database import init_db
        from config import BOT_TOKEN, ADMIN_ID
        print("✅ All imports OK")
        print(f"✅ ADMIN_ID: {ADMIN_ID}")
        return 0
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(test_all())
