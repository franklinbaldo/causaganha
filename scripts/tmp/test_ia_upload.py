import os
import httpx
import asyncio
from djen_backup.credentials import get_ia_s3_auth

async def test_ia_upload():
    try:
        auth = get_ia_s3_auth()
        print(f"Auth header derived successfully: {auth[:10]}...")
        
        # Try a HEAD request to a known bucket to verify credentials
        # Bucket: causaganha-dashboard
        url = "https://s3.us.archive.org/causaganha-dashboard/ia-state.json"
        
        async with httpx.AsyncClient() as client:
            resp = await client.head(url, headers={"Authorization": auth})
            print(f"HEAD request status: {resp.status_code}")
            if resp.status_code == 200:
                print("✅ Credentials verified (Read access worked with auth)")
            else:
                print(f"❌ Failed to verify credentials: {resp.status_code}")
                print(resp.text)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Ensure env vars are set if not already
    # (The shell that runs this should have them from .env)
    asyncio.run(test_ia_upload())
