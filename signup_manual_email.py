#!/usr/bin/env python3
"""
Instagram signup with manual email code entry.
You open temp-mail.org in another browser and enter the code when prompted.
"""

import asyncio
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import sys
sys.path.insert(0, '.')

from src.services.human_behavior import HumanBehavior


async def main():
    print("=" * 50)
    print("INSTAGRAM SIGNUP - MANUAL EMAIL")
    print("=" * 50)
    
    # Ask for email
    print("\n1. Go to https://temp-mail.org/fr/ in your browser")
    print("2. Copy the email address shown")
    email = input("\nPaste the email address here: ").strip()
    
    if not email or '@' not in email:
        print("Invalid email")
        return
    
    # Generate creds
    username = f"u{random.randint(1000000, 9999999)}_{random.randint(10,99)}"
    password = f"Pass{random.randint(10000, 99999)}!"
    full_name = f"User {random.randint(100, 999)}"
    
    print(f"\nCredentials:")
    print(f"  Email: {email}")
    print(f"  Username: {username}")
    print(f"  Password: {password}")
    
    # Start browser
    print("\nStarting browser...")
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1920,1080')
    
    driver = uc.Chrome(options=options, headless=False)
    human = HumanBehavior(driver)
    wait = WebDriverWait(driver, 20)
    
    try:
        print("\nLoading Instagram...")
        driver.get("https://www.instagram.com/accounts/emailsignup/")
        await asyncio.sleep(5)
        
        await human.browse_around(2)
        
        print("\nFilling form...")
        
        email_field = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//input[@name='emailOrPhone']")
        ))
        await human.human_type(email_field, email)
        await human.random_delay(1, 2)
        
        name_field = driver.find_element(By.XPATH, "//input[@name='fullName']")
        await human.human_type(name_field, full_name, mistakes=True)
        await human.random_delay(0.8, 1.5)
        
        username_field = driver.find_element(By.XPATH, "//input[@name='username']")
        await human.human_type(username_field, username)
        await human.random_delay(1, 2)
        
        password_field = driver.find_element(By.XPATH, "//input[@name='password']")
        await human.human_type(password_field, password)
        await human.random_delay(1.5, 2.5)
        
        await human.browse_around(1)
        
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
            
            await human.browse_around(1)
            
            for btn in driver.find_elements(By.TAG_NAME, 'button'):
                txt = btn.text.strip().lower()
                if txt in ['next', 'suivant', 'weiter']:
                    await human.human_click(btn)
                    print("✅ Next clicked")
                    break
            
            await asyncio.sleep(5)
        
        # Check current state
        driver.save_screenshot("current_state.png")
        print("\nScreenshot saved: current_state.png")
        
        page = driver.page_source.lower()
        
        if 'code' in page or 'confirm' in page or 'verification' in page:
            print("\n🎉 VERIFICATION PAGE REACHED!")
            print("\nCheck temp-mail.org for the Instagram code")
            code = input("Enter the 6-digit code: ").strip()
            
            if code and len(code) == 6:
                # Find input and enter code
                inputs = driver.find_elements(By.TAG_NAME, 'input')
                for inp in inputs:
                    try:
                        if inp.is_displayed() and inp.get_attribute('type') not in ['hidden', 'submit']:
                            inp.clear()
                            await human.human_type(inp, code, mistakes=False)
                            print(f"✅ Code entered")
                            break
                    except:
                        continue
                
                await human.random_delay(1, 2)
                
                # Click confirm/next
                for btn in driver.find_elements(By.TAG_NAME, 'button'):
                    try:
                        if btn.is_displayed() and btn.is_enabled():
                            txt = btn.text.lower()
                            if 'next' in txt or 'confirm' in txt or 'suivant' in txt or btn.get_attribute('type') == 'submit':
                                await human.human_click(btn)
                                print("✅ Confirm clicked")
                                break
                    except:
                        continue
                
                await asyncio.sleep(8)
                
                # Check result
                final_url = driver.current_url
                print(f"\nFinal URL: {final_url}")
                
                if 'signup' not in final_url.lower():
                    print("\n" + "=" * 50)
                    print("🎉 ACCOUNT CREATED SUCCESSFULLY!")
                    print("=" * 50)
                    print(f"Email: {email}")
                    print(f"Username: {username}")
                    print(f"Password: {password}")
                    
                    # Save credentials
                    with open('created_accounts.txt', 'a') as f:
                        f.write(f"{email}:{username}:{password}\n")
                    print("\nSaved to created_accounts.txt")
                else:
                    print("❌ Something went wrong")
                    driver.save_screenshot("error.png")
        
        elif 'captcha' in page or 'challenge' in page:
            print("❌ CAPTCHA detected")
            driver.save_screenshot("captcha.png")
        else:
            print("? Unknown state - check the browser")
        
        input("\nPress Enter to close browser...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        driver.save_screenshot("error.png")
    
    finally:
        driver.quit()


if __name__ == "__main__":
    asyncio.run(main())
