#!/usr/bin/env python3
"""Test with undetected-chromedriver - better bot evasion."""

import asyncio
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import sys
sys.path.insert(0, '.')

from src.services.email_service_handler import EmailServiceHandler
from src.services.human_behavior import HumanBehavior


async def main():
    print("=" * 50)
    print("UNDETECTED CHROME TEST")
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
    username = f"user{random.randint(100000, 999999)}"
    password = f"Pass{random.randint(10000, 99999)}!"
    full_name = f"User {random.randint(100, 999)}"
    
    # Undetected Chrome
    print("\nStarting undetected Chrome...")
    
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    driver = uc.Chrome(options=options, headless=False)  # headless=False is better for evasion
    
    human = HumanBehavior(driver)
    wait = WebDriverWait(driver, 20)
    
    try:
        print("\nLoading Instagram...")
        driver.get("https://www.instagram.com/accounts/emailsignup/")
        await asyncio.sleep(5)
        
        # Human behavior
        await human.browse_around(3)
        
        print("\nFilling form...")
        
        email_field = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[@name='emailOrPhone']")
        ))
        await human.human_type(email_field, email_data['email_address'])
        await human.random_delay(1, 2)
        
        await human.random_mouse_movement()
        
        name_field = driver.find_element(By.XPATH, "//input[@name='fullName']")
        await human.human_type(name_field, full_name, mistakes=True)
        await human.random_delay(0.8, 1.5)
        
        username_field = driver.find_element(By.XPATH, "//input[@name='username']")
        await human.human_type(username_field, username)
        await human.random_delay(1, 2)
        
        await human.random_scroll()
        
        password_field = driver.find_element(By.XPATH, "//input[@name='password']")
        await human.human_type(password_field, password)
        await human.random_delay(1.5, 2.5)
        
        await human.browse_around(2)
        
        # Submit
        submit_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
        await human.human_click(submit_btn)
        print("✅ Form submitted")
        await asyncio.sleep(6)
        
        # Birthday
        selects = driver.find_elements(By.TAG_NAME, 'select')
        if len(selects) >= 3:
            print("Birthday page...")
            await human.random_delay(1, 2)
            Select(selects[0]).select_by_value(str(random.randint(1, 12)))
            await human.random_delay(0.5, 1)
            Select(selects[1]).select_by_value(str(random.randint(1, 28)))
            await human.random_delay(0.5, 1)
            Select(selects[2]).select_by_value(str(random.randint(1990, 2000)))
            print("✅ Birthday filled")
            
            await human.browse_around(2)
            
            for btn in driver.find_elements(By.TAG_NAME, 'button'):
                txt = btn.text.strip().lower()
                if txt in ['next', 'suivant', 'weiter']:
                    await human.human_click(btn)
                    print("✅ Next clicked")
                    break
            
            await asyncio.sleep(6)
        
        # Check result
        page = driver.page_source.lower()
        url = driver.current_url.lower()
        
        print(f"\nCurrent URL: {url}")
        
        # Check what page we're on
        if 'verification' in page or 'code' in page or 'confirm' in url:
            print("🎉 VERIFICATION PAGE REACHED!")
            driver.save_screenshot("verification_page.png")
            
            # Wait for email code
            print("\nWaiting for verification code from email...")
            code = await email_handler.get_verification_code(email_data, timeout=120)
            
            if code:
                print(f"✅ Got code: {code}")
                # Enter code
                inputs = driver.find_elements(By.TAG_NAME, 'input')
                for inp in inputs:
                    if inp.is_displayed() and inp.get_attribute('type') != 'hidden':
                        inp.clear()
                        await human.human_type(inp, code, mistakes=False)
                        break
                
                await human.random_delay(1, 2)
                
                # Click confirm
                for btn in driver.find_elements(By.TAG_NAME, 'button'):
                    if btn.is_displayed() and btn.is_enabled():
                        txt = btn.text.lower()
                        if 'next' in txt or 'confirm' in txt or 'suivant' in txt:
                            await human.human_click(btn)
                            break
                
                await asyncio.sleep(5)
                print(f"Final URL: {driver.current_url}")
                driver.save_screenshot("after_code.png")
            else:
                print("❌ No code received - Instagram might not deliver to temp emails")
        
        elif 'captcha' in page or 'challenge' in page or 'arkose' in page:
            print("❌ CAPTCHA triggered")
            driver.save_screenshot("captcha.png")
        else:
            print("? Unknown state")
            driver.save_screenshot("unknown.png")
        
        # Keep browser open to see
        print("\nBrowser stays open for 30s...")
        await asyncio.sleep(30)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        driver.save_screenshot("undetected_error.png")
    
    finally:
        driver.quit()
        await email_handler.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
