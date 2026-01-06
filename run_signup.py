#!/usr/bin/env python3
"""
Instagram Auto Signup - Single account creation with captcha solving.
"""

import asyncio
import sys
import json
import random
import time
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.managers.browser_manager import BrowserManager
from src.managers.proxy_pool_manager import ProxyPoolManager
from src.managers.user_agent_rotator import UserAgentRotator
from src.services.email_service_handler import EmailServiceHandler
from src.services.captcha_solver import CaptchaSolver
from src.services.audio_captcha_solver import AudioCaptchaSolver
from src.services.human_behavior import HumanBehavior
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC


async def create_account(capsolver_key: str = None, wit_keys: list = None):
    """Create a single Instagram account."""
    
    print("=" * 50)
    print("INSTAGRAM AUTO SIGNUP")
    print("=" * 50)
    
    # Load config
    with open('config/system_config.json') as f:
        config = json.load(f)
    
    api_key = capsolver_key or config.get('capsolver_api_key', '')
    wit_api_keys = wit_keys or config.get('wit_api_keys', [])
    
    # Init services
    proxy_mgr = ProxyPoolManager()
    await proxy_mgr.initialize()
    
    ua_rotator = UserAgentRotator()
    await ua_rotator.initialize()
    
    browser_mgr = BrowserManager(proxy_mgr, ua_rotator)
    await browser_mgr.initialize()
    
    email_handler = EmailServiceHandler()
    await email_handler.initialize()
    
    # Use audio solver (free) if wit.ai keys available, otherwise paid solver
    audio_solver = None
    captcha_solver = None
    
    if wit_api_keys:
        audio_solver = AudioCaptchaSolver(wit_api_keys)
        await audio_solver.initialize()
        print("Using FREE audio captcha solver (wit.ai)")
    elif api_key:
        captcha_solver = CaptchaSolver(api_key)
        await captcha_solver.initialize()
        print("Using paid captcha solver")
    
    # Create email
    print("\n[1/6] Creating email...")
    email_data = await email_handler.create_email()
    if not email_data:
        print("❌ Email creation failed")
        return None
    print(f"✅ Email: {email_data['email_address']}")
    
    # Generate credentials
    username = f"user{random.randint(100000, 999999)}"
    password = f"Pass{random.randint(10000, 99999)}!"
    full_name = f"User {random.randint(100, 999)}"
    
    # Create browser
    print("\n[2/6] Starting browser...")
    instance = await browser_mgr.create_browser_instance()
    if not instance:
        print("❌ Browser failed")
        return None
    
    driver = instance.driver
    wait = WebDriverWait(driver, 20)
    human = HumanBehavior(driver)
    
    result = None
    
    try:
        # Load signup page
        print("\n[3/6] Loading Instagram...")
        driver.get("https://www.instagram.com/accounts/emailsignup/")
        await asyncio.sleep(4)
        
        # Browse around first like a human
        print("Simulating human behavior...")
        await human.browse_around(duration=random.uniform(2, 4))
        
        # Fill form
        print("\n[4/6] Filling form...")
        
        # Random scroll first
        await human.random_scroll()
        await human.random_delay(0.5, 1.5)
        
        email_field = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[@name='emailOrPhone']")
        ))
        await human.human_type(email_field, email_data['email_address'], mistakes=False)
        await human.random_delay(0.8, 1.5)
        
        # Random mouse movement
        await human.random_mouse_movement()
        
        name_field = driver.find_element(By.XPATH, "//input[@name='fullName']")
        await human.human_type(name_field, full_name, mistakes=True)
        await human.random_delay(0.5, 1.2)
        
        username_field = driver.find_element(By.XPATH, "//input[@name='username']")
        await human.human_type(username_field, username, mistakes=False)
        await human.random_delay(0.8, 1.5)
        
        # Scroll a bit
        await human.random_scroll()
        
        password_field = driver.find_element(By.XPATH, "//input[@name='password']")
        await human.human_type(password_field, password, mistakes=False)
        await human.random_delay(1.0, 2.0)
        
        # Browse around before submit
        await human.browse_around(duration=random.uniform(1, 2))
        
        # Submit
        submit_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
        await human.human_click(submit_btn)
        print("✅ Form submitted")
        await asyncio.sleep(random.uniform(4, 6))
        
        # Birthday
        selects = driver.find_elements(By.TAG_NAME, 'select')
        if len(selects) >= 3:
            await human.random_delay(0.5, 1.0)
            Select(selects[0]).select_by_value(str(random.randint(1, 12)))
            await human.random_delay(0.3, 0.8)
            Select(selects[1]).select_by_value(str(random.randint(1, 28)))
            await human.random_delay(0.3, 0.8)
            Select(selects[2]).select_by_value(str(random.randint(1990, 2000)))
            print("✅ Birthday filled")
            await human.random_delay(1.0, 2.0)
            
            # Browse before clicking next
            await human.browse_around(duration=random.uniform(1, 2))
            
            for btn in driver.find_elements(By.TAG_NAME, 'button'):
                txt = btn.text.strip().lower()
                if txt in ['next', 'suivant', 'weiter']:
                    await human.human_click(btn)
                    print("✅ Next clicked")
                    break
            
            await asyncio.sleep(random.uniform(4, 6))
        
        # Check for captcha
        print("\n[5/6] Checking for captcha...")
        page = driver.page_source.lower()
        
        if 'captcha' in page or 'challenge' in page:
            print("⚠️ CAPTCHA detected")
            
            # Try free audio solver first
            if audio_solver:
                print("Solving with FREE audio method (wit.ai)...")
                token = await audio_solver.solve(driver)
                
                if token:
                    print("✅ Captcha solved with audio!")
                    await asyncio.sleep(3)
                else:
                    print("❌ Audio solver failed")
                    driver.save_screenshot("audio_failed.png")
                    return None
            
            # Fall back to paid solver
            elif captcha_solver and api_key:
                print("Solving with paid service...")
                token = await captcha_solver.solve_from_page(driver, driver.current_url)
                
                if token:
                    captcha_solver.inject_token(driver, token)
                    await asyncio.sleep(2)
                    
                    # Click submit/verify button
                    for btn in driver.find_elements(By.TAG_NAME, 'button'):
                        if btn.is_enabled() and btn.is_displayed():
                            btn.click()
                            break
                    
                    await asyncio.sleep(5)
                    print("✅ Captcha solved")
                else:
                    print("❌ Captcha solving failed")
                    driver.save_screenshot("captcha_failed.png")
                    return None
            else:
                print("❌ No captcha solver configured")
                print("\nOptions:")
                print("1. FREE: Get wit.ai API keys at https://wit.ai/apps")
                print("   Add to config: \"wit_api_keys\": [\"YOUR_KEY\"]")
                print("2. PAID: Get Capsolver/2Captcha key")
                driver.save_screenshot("captcha_needed.png")
                return None
        
        # Wait for verification code
        print("\n[6/6] Waiting for verification code...")
        page = driver.page_source.lower()
        
        if 'code' in page or 'confirm' in page or 'verification' in page:
            start = time.time()
            code = None
            
            while time.time() - start < 120:
                messages = await email_handler.get_messages(email_data)
                
                for msg in messages:
                    subject = msg.get('subject', '')
                    match = re.search(r'\b(\d{6})\b', subject)
                    if match:
                        code = match.group(1)
                        break
                
                if code:
                    break
                
                elapsed = int(time.time() - start)
                if elapsed % 15 == 0:
                    print(f"  Waiting... {elapsed}s")
                await asyncio.sleep(5)
            
            if code:
                print(f"✅ Code received: {code}")
                
                # Enter code
                inputs = driver.find_elements(By.TAG_NAME, 'input')
                for inp in inputs:
                    if inp.is_displayed():
                        inp.clear()
                        inp.send_keys(code)
                        break
                
                await asyncio.sleep(1)
                
                # Confirm
                for btn in driver.find_elements(By.TAG_NAME, 'button'):
                    if btn.is_enabled() and btn.is_displayed():
                        btn.click()
                        break
                
                await asyncio.sleep(8)
                
                # Check success
                if 'signup' not in driver.current_url.lower():
                    print("\n" + "=" * 50)
                    print("🎉 ACCOUNT CREATED SUCCESSFULLY!")
                    print("=" * 50)
                    
                    result = {
                        'email': email_data['email_address'],
                        'username': username,
                        'password': password,
                        'status': 'created'
                    }
                    
                    # Save to credentials file
                    try:
                        with open('config/bots_credentials.json', 'r') as f:
                            creds = json.load(f)
                    except:
                        creds = {'bots': []}
                    
                    creds['bots'].append(result)
                    
                    with open('config/bots_credentials.json', 'w') as f:
                        json.dump(creds, f, indent=2)
                    
                    print(f"\nCredentials saved!")
                else:
                    print("❌ Account creation may have failed")
                    driver.save_screenshot("failed.png")
            else:
                print("❌ Verification code not received")
        else:
            print("❌ Did not reach verification page")
            driver.save_screenshot("unknown_state.png")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        driver.save_screenshot("error.png")
    
    finally:
        await browser_mgr.close_browser_instance(instance)
        await email_handler.cleanup()
        if audio_solver:
            await audio_solver.cleanup()
        if captcha_solver:
            await captcha_solver.cleanup()
    
    if result:
        print(f"\nEmail: {result['email']}")
        print(f"Username: {result['username']}")
        print(f"Password: {result['password']}")
    
    return result


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Instagram Auto Signup')
    parser.add_argument('--key', type=str, help='Capsolver API key (paid)')
    parser.add_argument('--wit', type=str, help='wit.ai API key (FREE)', action='append')
    parser.add_argument('--count', type=int, default=1, help='Number of accounts to create')
    args = parser.parse_args()
    
    wit_keys = args.wit if args.wit else None
    
    for i in range(args.count):
        print(f"\n{'='*50}")
        print(f"CREATING ACCOUNT {i+1}/{args.count}")
        print(f"{'='*50}")
        
        result = await create_account(args.key, wit_keys)
        
        if i < args.count - 1:
            wait_time = random.randint(60, 180)
            print(f"\nWaiting {wait_time}s before next account...")
            await asyncio.sleep(wait_time)


if __name__ == "__main__":
    asyncio.run(main())
