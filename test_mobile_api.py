#!/usr/bin/env python3
"""Test Instagram signup via mobile API - bypasses web captcha."""

import asyncio
import aiohttp
import random
import string
import uuid
import hashlib
import json
import sys
sys.path.insert(0, '.')

from src.services.email_service_handler import EmailServiceHandler


class InstagramMobileAPI:
    """Instagram mobile API client."""
    
    def __init__(self):
        self.api_url = "https://i.instagram.com/api/v1"
        self.user_agent = "Instagram 275.0.0.27.98 Android (33/13; 420dpi; 1080x2400; samsung; SM-G991B; o1s; exynos2100; en_US; 458229237)"
        self.device_id = self._generate_device_id()
        self.uuid = str(uuid.uuid4())
        self.phone_id = str(uuid.uuid4())
        self.session = None
        
    def _generate_device_id(self):
        seed = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        return 'android-' + hashlib.md5(seed.encode()).hexdigest()[:16]
    
    def _generate_signature(self, data):
        # Instagram signature key (public)
        sig_key = "9193488027538fd3450b83b7d05286d4ca9599a0f7eeed90d8c85925698a05dc"
        return hashlib.sha256((sig_key + data).encode()).hexdigest()
    
    async def initialize(self):
        # Randomize device info
        devices = [
            ("Instagram 275.0.0.27.98 Android (33/13; 420dpi; 1080x2400; samsung; SM-G991B; o1s; exynos2100; en_US; 458229237)", "567067343352427"),
            ("Instagram 269.0.0.18.75 Android (31/12; 440dpi; 1080x2340; Google; Pixel 6; oriole; tensor; en_US; 436384447)", "567067343352427"),
            ("Instagram 272.0.0.16.73 Android (30/11; 480dpi; 1080x2280; OnePlus; IN2023; OnePlus8Pro; qcom; en_US; 445932073)", "567067343352427"),
            ("Instagram 268.0.0.18.72 Android (29/10; 420dpi; 1080x2220; Xiaomi; Mi 11; venus; qcom; en_US; 432217846)", "567067343352427"),
        ]
        
        ua, app_id = random.choice(devices)
        self.user_agent = ua
        
        self.session = aiohttp.ClientSession(
            headers={
                'User-Agent': self.user_agent,
                'X-IG-App-ID': app_id,
                'X-IG-Device-ID': self.device_id,
                'X-IG-Android-ID': self.device_id,
                'X-Pigeon-Session-Id': str(uuid.uuid4()),
                'X-Pigeon-Rawclienttime': str(random.uniform(1700000000, 1800000000)),
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Accept-Language': 'en-US',
                'Accept-Encoding': 'gzip, deflate',
                'X-FB-HTTP-Engine': 'Liger',
                'X-IG-Connection-Type': 'WIFI',
                'X-IG-Capabilities': '3brTvwE=',
                'X-IG-App-Locale': 'en_US',
                'X-IG-Device-Locale': 'en_US',
                'X-IG-Mapped-Locale': 'en_US',
                'X-Bloks-Version-Id': 'e538d4591f238824118bfcb9528c8d005f2ea3becd947a3973c030ac971bb88e',
            }
        )
    
    async def cleanup(self):
        if self.session:
            await self.session.close()
    
    async def check_email(self, email):
        """Check if email is available."""
        data = {
            'email': email,
            'qe_id': str(uuid.uuid4()),
            'device_id': self.device_id,
        }
        
        try:
            async with self.session.post(
                f"{self.api_url}/users/check_email/",
                data=data
            ) as resp:
                result = await resp.json()
                print(f"Email check: {result}")
                return result.get('available', False)
        except Exception as e:
            print(f"Email check error: {e}")
            return True
    
    async def create_account(self, email, username, password, full_name):
        """Create account via mobile API."""
        
        # First, get signup config
        try:
            async with self.session.get(f"{self.api_url}/si/fetch_headers/") as resp:
                headers_data = await resp.text()
                print(f"Headers: {resp.status}")
        except:
            pass
        
        await asyncio.sleep(1)
        
        # Signup data
        data = {
            'email': email,
            'enc_password': f'#PWD_INSTAGRAM:0:{int(asyncio.get_event_loop().time())}:{password}',
            'username': username,
            'first_name': full_name,
            'device_id': self.device_id,
            'guid': self.uuid,
            'phone_id': self.phone_id,
            'waterfall_id': str(uuid.uuid4()),
            'adid': str(uuid.uuid4()),
            'qe_id': str(uuid.uuid4()),
            'year': str(random.randint(1990, 2000)),
            'month': str(random.randint(1, 12)),
            'day': str(random.randint(1, 28)),
            'force_sign_up_code': '',
            'tos_version': 'row',
            'has_sms_consent': 'true',
        }
        
        print(f"\nSending signup request...")
        print(f"Username: {username}")
        print(f"Email: {email}")
        
        try:
            async with self.session.post(
                f"{self.api_url}/accounts/create/",
                data=data
            ) as resp:
                result = await resp.json()
                print(f"\nResponse status: {resp.status}")
                print(f"Response: {json.dumps(result, indent=2)}")
                
                if result.get('account_created'):
                    return {'success': True, 'user_id': result.get('created_user', {}).get('pk')}
                elif 'challenge' in str(result).lower():
                    return {'success': False, 'reason': 'challenge', 'data': result}
                else:
                    return {'success': False, 'reason': result.get('message', 'unknown'), 'data': result}
                    
        except Exception as e:
            print(f"Signup error: {e}")
            return {'success': False, 'reason': str(e)}


async def main():
    print("=" * 50)
    print("INSTAGRAM MOBILE API TEST")
    print("=" * 50)
    
    # Create email
    email_handler = EmailServiceHandler()
    await email_handler.initialize()
    
    email_data = await email_handler.create_email()
    if not email_data:
        print("❌ Email failed")
        return
    print(f"✅ Email: {email_data['email_address']}")
    
    # Generate creds
    username = f"u{random.randint(1000000, 9999999)}_{random.randint(10,99)}"
    password = f"Pass{random.randint(10000, 99999)}!"
    full_name = f"User {random.randint(100, 999)}"
    
    # Mobile API
    api = InstagramMobileAPI()
    await api.initialize()
    
    try:
        # Check email
        print("\nChecking email availability...")
        available = await api.check_email(email_data['email_address'])
        
        if available:
            print("✅ Email available")
        
        await asyncio.sleep(2)
        
        # Create account
        result = await api.create_account(
            email_data['email_address'],
            username,
            password,
            full_name
        )
        
        if result.get('success'):
            print("\n🎉 ACCOUNT CREATED!")
        else:
            print(f"\n❌ Failed: {result.get('reason')}")
            
    finally:
        await api.cleanup()
        await email_handler.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
