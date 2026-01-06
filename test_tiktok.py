#!/usr/bin/env python3
"""TikTok account creation test."""

import asyncio
import random
import sys
sys.path.insert(0, '.')

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.services.human_behavior import HumanBehavior


async def main():
    email = input("Email from temp-mail.org: ").strip()
    
    username = f"user{random.randint(100000, 999999)}"
    password = f"Pass{random.randint(10000, 99999)}!@"
    
    print(f"\nEmail: {email}")
    print(f"Username: {username}")
    print(f"Password: {password}")
    
    print("\nStarting browser...")
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--window-size=1920,1080')
    
    driver = uc.Chrome(options=options, headless=False)
    human = HumanBehavior(driver)
    wait = WebDriverWait(driver, 20)
    
    try:
        print("Loading TikTok signup...")
        driver.get("https://www.tiktok.com/signup/phone-or-email/email")
        await asyncio.sleep(5)
        
        await human.browse_around(2)
        
        # Select birthday (month/day/year dropdowns)
        print("Setting birthday...")
        
        # Find month selector
        try:
            month_div = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//div[contains(@class, 'month')]//div[contains(@class, 'select')]")
            ))
            month_div.click()
            await asyncio.sleep(0.5)
            # Select random month
            months = driver.find_elements(By.XPATH, "//div[contains(@class, 'option')]")
            if months:
                random.choice(months[1:12]).click()
            await asyncio.sleep(0.5)
        except:
            print("Month selector not found, trying alternative...")
        
        # Try to find selects
        selects = driver.find_elements(By.TAG_NAME, 'select')
        if selects:
            print(f"Found {len(selects)} select elements")
        
        driver.save_screenshot("tiktok_page.png")
        print("Screenshot: tiktok_page.png")
        
        # Look for email input
        try:
            email_input = driver.find_element(By.XPATH, "//input[@name='email' or @type='email' or @placeholder='Email']")
            await human.human_type(email_input, email)
            print("Email entered")
        except Exception as e:
            print(f"Email input not found: {e}")
        
        await asyncio.sleep(2)
        
        # Look for password
        try:
            pwd_input = driver.find_element(By.XPATH, "//input[@type='password']")
            await human.human_type(pwd_input, password)
            print("Password entered")
        except:
            print("Password input not found")
        
        await asyncio.sleep(2)
        driver.save_screenshot("tiktok_filled.png")
        
        # Find signup button
        try:
            signup_btn = driver.find_element(By.XPATH, "//button[@type='submit' or contains(text(), 'Sign up') or contains(text(), 'Next')]")
            await human.human_click(signup_btn)
            print("Signup clicked")
        except:
            print("Signup button not found")
        
        await asyncio.sleep(5)
        driver.save_screenshot("tiktok_result.png")
        
        print(f"\nCurrent URL: {driver.current_url}")
        
        page = driver.page_source.lower()
        if 'captcha' in page or 'verify' in page:
            print("Captcha or verification detected")
        
        print("\nBrowser stays open 60s...")
        await asyncio.sleep(60)
        
    except Exception as e:
        print(f"Error: {e}")
        driver.save_screenshot("tiktok_error.png")
    finally:
        driver.quit()


if __name__ == "__main__":
    asyncio.run(main())
