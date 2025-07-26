"""
Account Creator Service

Implements the Instagram account creation workflow with anti-detection measures,
form filling, and account data generation.
"""

import logging
import time
import random
import asyncio
import json
import os
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import string
import re

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, ElementNotInteractableException,
    StaleElementReferenceException, WebDriverException
)

from ..core.interfaces import AccountCreator as AccountCreatorInterface, BaseService, ServiceStatus
from ..models.account_models import AccountData, EmailData, CreationResult, AccountStatus, GenderType
from ..services.anti_detection_module import AntiDetectionModule
from ..services.element_selector import ElementSelector
from ..services.browser_error_handler import BrowserErrorHandler
from ..services.email_service_handler import EmailServiceHandler
from ..services.verification_code_extractor import VerificationCodeExtractor


logger = logging.getLogger(__name__)


class AccountCreator(AccountCreatorInterface, BaseService):
    """
    Implements Instagram account creation workflow with anti-detection measures,
    form filling, and account data generation.
    """
    
    # Instagram signup URL
    SIGNUP_URL = "https://www.instagram.com/accounts/emailsignup/"
    
    # Form field selectors (these may need updates if Instagram changes their UI)
    SELECTORS = {
        "email_field": "//input[@name='emailOrPhone']",
        "full_name_field": "//input[@name='fullName']",
        "username_field": "//input[@name='username']",
        "password_field": "//input[@name='password']",
        "next_button": "//button[contains(text(), 'Next')]",
        "signup_button": "//button[contains(text(), 'Sign up')]",
        "birth_date_month": "//select[@title='Month:']",
        "birth_date_day": "//select[@title='Day:']",
        "birth_date_year": "//select[@title='Year:']",
        "gender_option": "//span[contains(text(), '{gender}')]/preceding-sibling::input",
        "verification_code_field": "//input[@name='confirmationCode']",
        "confirm_button": "//button[contains(text(), 'Confirm')]",
        "skip_button": "//button[contains(text(), 'Skip')]",
        "error_message": "//p[@id='ssfErrorAlert']",
        "captcha_container": "//div[contains(@class, 'captcha')]"
    }
    
    def __init__(self, 
                 browser_manager,
                 email_service: EmailServiceHandler,
                 anti_detection: AntiDetectionModule,
                 element_selector: ElementSelector,
                 error_handler: BrowserErrorHandler,
                 config_manager,
                 verification_extractor: VerificationCodeExtractor,
                 name: str = "AccountCreator"):
        """
        Initialize the account creator service.
        
        Args:
            browser_manager: Browser manager service
            email_service: Email service handler
            anti_detection: Anti-detection module
            element_selector: Element selector service
            error_handler: Browser error handler
            config_manager: Configuration manager
            verification_extractor: Verification code extractor
            name: Service name
        """
        super().__init__(name)
        self.browser_manager = browser_manager
        self.email_service = email_service
        self.anti_detection = anti_detection
        self.element_selector = element_selector
        self.error_handler = error_handler
        self.config_manager = config_manager
        self.verification_extractor = verification_extractor
        
        # Configuration
        self.max_retries = 3
        self.verification_timeout = 300  # seconds
        self.verification_check_interval = 10  # seconds
        self.credentials_file = "config/bots_credentials.json"
        
        # Statistics
        self.successful_creations = 0
        self.failed_creations = 0
        
        logger.info("AccountCreator service initialized")
    
    async def initialize(self) -> bool:
        """Initialize the account creator service."""
        try:
            # Check if credentials file exists, create if not
            if not os.path.exists(self.credentials_file):
                os.makedirs(os.path.dirname(self.credentials_file), exist_ok=True)
                with open(self.credentials_file, 'w') as f:
                    json.dump({"bots": []}, f)
            
            self.status = ServiceStatus.ACTIVE
            logger.info("AccountCreator service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize AccountCreator: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Cleanup service resources."""
        logger.info("Cleaning up AccountCreator service")
        self.status = ServiceStatus.INACTIVE
    
    async def health_check(self) -> bool:
        """Check if service is healthy."""
        return self.status == ServiceStatus.ACTIVE
    
    async def create_account(self) -> CreationResult:
        """
        Create a new Instagram account with anti-detection measures.
        
        Returns:
            CreationResult: Result of the account creation attempt
        """
        start_time = time.time()
        steps_completed = []
        driver = None
        
        try:
            # Generate account data
            account_data = await self.generate_account_data()
            steps_completed.append("account_data_generated")
            
            # Create browser instance
            driver = await self.browser_manager.create_browser_instance()
            if not driver:
                return CreationResult(
                    success=False,
                    error_message="Failed to create browser instance",
                    error_code="BROWSER_CREATION_FAILED",
                    steps_completed=steps_completed
                )
            
            steps_completed.append("browser_created")
            
            # Navigate to Instagram signup page
            driver.get(self.SIGNUP_URL)
            await self.anti_detection.add_random_interaction_delay("page_load")
            steps_completed.append("page_loaded")
            
            # Fill signup form
            await self._fill_signup_form(driver, account_data)
            steps_completed.append("form_filled")
            
            # Submit form and handle initial response
            success = await self._submit_signup_form(driver)
            if not success:
                return CreationResult(
                    success=False,
                    account_data=account_data,
                    error_message="Failed to submit signup form",
                    error_code="FORM_SUBMISSION_FAILED",
                    creation_time_seconds=time.time() - start_time,
                    steps_completed=steps_completed
                )
            
            steps_completed.append("form_submitted")
            
            # Check for captcha
            captcha_detected = await self._check_for_captcha(driver)
            if captcha_detected:
                return CreationResult(
                    success=False,
                    account_data=account_data,
                    error_message="CAPTCHA detected",
                    error_code="CAPTCHA_DETECTED",
                    captcha_encountered=True,
                    creation_time_seconds=time.time() - start_time,
                    steps_completed=steps_completed
                )
            
            # Handle email verification if required
            verification_required = await self._check_verification_required(driver)
            if verification_required:
                steps_completed.append("verification_required")
                verification_success = await self._handle_email_verification(driver, account_data)
                
                if verification_success:
                    steps_completed.append("verification_completed")
                else:
                    return CreationResult(
                        success=False,
                        account_data=account_data,
                        error_message="Email verification failed",
                        error_code="VERIFICATION_FAILED",
                        verification_required=True,
                        creation_time_seconds=time.time() - start_time,
                        steps_completed=steps_completed
                    )
            
            # Skip additional steps (profile picture, contacts, etc.)
            await self._skip_additional_steps(driver)
            steps_completed.append("additional_steps_skipped")
            
            # Validate account creation
            is_valid = await self.validate_account_creation(account_data)
            if not is_valid:
                return CreationResult(
                    success=False,
                    account_data=account_data,
                    error_message="Account validation failed",
                    error_code="VALIDATION_FAILED",
                    creation_time_seconds=time.time() - start_time,
                    steps_completed=steps_completed
                )
            
            # Update account data
            account_data.status = AccountStatus.VERIFIED if verification_required else AccountStatus.CREATED
            account_data.created_at = datetime.now()
            if verification_required:
                account_data.verified_at = datetime.now()
            
            # Save account credentials
            await self._save_account_credentials(account_data)
            steps_completed.append("credentials_saved")
            
            # Update statistics
            self.successful_creations += 1
            self.update_metrics(True, time.time() - start_time)
            
            return CreationResult(
                success=True,
                account_data=account_data,
                verification_required=verification_required,
                creation_time_seconds=time.time() - start_time,
                steps_completed=steps_completed
            )
            
        except Exception as e:
            logger.error(f"Error creating account: {e}")
            self.failed_creations += 1
            self.update_metrics(False)
            
            return CreationResult(
                success=False,
                account_data=account_data if 'account_data' in locals() else None,
                error_message=str(e),
                error_code="UNEXPECTED_ERROR",
                creation_time_seconds=time.time() - start_time,
                steps_completed=steps_completed
            )
            
        finally:
            # Close browser
            if driver:
                await self.browser_manager.close_browser_instance(driver)
    
    async def generate_account_data(self) -> AccountData:
        """
        Generate random account data for Instagram signup.
        
        Returns:
            AccountData: Generated account data
        """
        try:
            # Generate email using email service
            email_data = await self.email_service.create_email()
            email = email_data.get('email_address', f"{self._generate_random_string(8)}@example.com")
            
            # Generate username (Instagram-friendly)
            username = self._generate_username()
            
            # Generate full name
            full_name = self._generate_full_name()
            
            # Generate password (strong but memorable)
            password = self._generate_strong_password()
            
            # Generate birth date (18-45 years old)
            birth_date = self._generate_birth_date(min_age=18, max_age=45)
            
            # Create account data
            account_data = AccountData(
                email=email,
                full_name=full_name,
                username=username,
                password=password,
                birth_date=birth_date,
                gender=random.choice([GenderType.MALE, GenderType.FEMALE]),
                created_at=datetime.now()
            )
            
            logger.info(f"Generated account data for username: {username}")
            return account_data
            
        except Exception as e:
            logger.error(f"Error generating account data: {e}")
            raise
    
    async def validate_account_creation(self, account_data: AccountData) -> bool:
        """
        Validate if account was created successfully.
        
        Args:
            account_data: Account data to validate
            
        Returns:
            bool: True if account is valid
        """
        # Basic validation
        if not account_data.username or not account_data.password or not account_data.email:
            logger.error("Account data missing required fields")
            return False
        
        # Check if account already exists in our database
        existing_accounts = await self._load_existing_accounts()
        for account in existing_accounts:
            if account.get('username') == account_data.username:
                logger.warning(f"Account with username {account_data.username} already exists")
                return False
        
        return True
    
    async def _fill_signup_form(self, driver: WebDriver, account_data: AccountData) -> bool:
        """
        Fill the Instagram signup form with account data using anti-detection measures.
        
        Args:
            driver: WebDriver instance
            account_data: Account data to use
            
        Returns:
            bool: True if form was filled successfully
        """
        try:
            # Wait for page to load
            await self.anti_detection.simulate_page_reading(driver, (3.0, 6.0))
            
            # Fill email field
            email_field = await self.element_selector.wait_and_find_element(
                driver, By.XPATH, self.SELECTORS["email_field"], timeout=10
            )
            await self.anti_detection.simulate_human_typing(email_field, account_data.email)
            await self.anti_detection.add_random_interaction_delay("form_field")
            
            # Fill full name field
            full_name_field = await self.element_selector.wait_and_find_element(
                driver, By.XPATH, self.SELECTORS["full_name_field"]
            )
            await self.anti_detection.simulate_human_typing(full_name_field, account_data.full_name)
            await self.anti_detection.add_random_interaction_delay("form_field")
            
            # Fill username field
            username_field = await self.element_selector.wait_and_find_element(
                driver, By.XPATH, self.SELECTORS["username_field"]
            )
            await self.anti_detection.simulate_human_typing(username_field, account_data.username)
            await self.anti_detection.add_random_interaction_delay("form_field")
            
            # Fill password field
            password_field = await self.element_selector.wait_and_find_element(
                driver, By.XPATH, self.SELECTORS["password_field"]
            )
            await self.anti_detection.simulate_human_typing(password_field, account_data.password)
            await self.anti_detection.add_random_interaction_delay("form_field")
            
            # Click next button
            next_button = await self.element_selector.wait_and_find_element(
                driver, By.XPATH, self.SELECTORS["next_button"]
            )
            await self.anti_detection.simulate_mouse_movement(driver, next_button)
            next_button.click()
            await self.anti_detection.add_random_interaction_delay("page_load")
            
            # Fill birth date fields
            await self._fill_birth_date(driver, account_data.birth_date)
            
            # Select gender
            if account_data.gender:
                gender_selector = self.SELECTORS["gender_option"].format(
                    gender=account_data.gender.value.capitalize()
                )
                gender_option = await self.element_selector.wait_and_find_element(
                    driver, By.XPATH, gender_selector
                )
                await self.anti_detection.simulate_mouse_movement(driver, gender_option)
                gender_option.click()
            
            await self.anti_detection.add_random_interaction_delay("form_field")
            
            logger.info(f"Successfully filled signup form for {account_data.username}")
            return True
            
        except Exception as e:
            logger.error(f"Error filling signup form: {e}")
            return False
    
    async def _fill_birth_date(self, driver: WebDriver, birth_date: date) -> None:
        """
        Fill birth date fields in the signup form.
        
        Args:
            driver: WebDriver instance
            birth_date: Birth date to use
        """
        try:
            # Select month
            month_select = await self.element_selector.wait_and_find_element(
                driver, By.XPATH, self.SELECTORS["birth_date_month"]
            )
            await self.anti_detection.simulate_mouse_movement(driver, month_select)
            month_select.click()
            await self.anti_detection.add_random_interaction_delay("form_field")
            
            # Select month option (value is 1-12)
            month_option = await self.element_selector.wait_and_find_element(
                driver, By.XPATH, f"//option[@value='{birth_date.month}']"
            )
            await self.anti_detection.simulate_mouse_movement(driver, month_option)
            month_option.click()
            await self.anti_detection.add_random_interaction_delay("form_field")
            
            # Select day
            day_select = await self.element_selector.wait_and_find_element(
                driver, By.XPATH, self.SELECTORS["birth_date_day"]
            )
            await self.anti_detection.simulate_mouse_movement(driver, day_select)
            day_select.click()
            await self.anti_detection.add_random_interaction_delay("form_field")
            
            # Select day option
            day_option = await self.element_selector.wait_and_find_element(
                driver, By.XPATH, f"//option[@value='{birth_date.day}']"
            )
            await self.anti_detection.simulate_mouse_movement(driver, day_option)
            day_option.click()
            await self.anti_detection.add_random_interaction_delay("form_field")
            
            # Select year
            year_select = await self.element_selector.wait_and_find_element(
                driver, By.XPATH, self.SELECTORS["birth_date_year"]
            )
            await self.anti_detection.simulate_mouse_movement(driver, year_select)
            year_select.click()
            await self.anti_detection.add_random_interaction_delay("form_field")
            
            # Select year option
            year_option = await self.element_selector.wait_and_find_element(
                driver, By.XPATH, f"//option[@value='{birth_date.year}']"
            )
            await self.anti_detection.simulate_mouse_movement(driver, year_option)
            year_option.click()
            await self.anti_detection.add_random_interaction_delay("form_field")
            
        except Exception as e:
            logger.error(f"Error filling birth date: {e}")
            raise
    
    async def _submit_signup_form(self, driver: WebDriver) -> bool:
        """
        Submit the signup form and handle initial response.
        
        Args:
            driver: WebDriver instance
            
        Returns:
            bool: True if form was submitted successfully
        """
        try:
            # Find and click signup button
            signup_button = await self.element_selector.wait_and_find_element(
                driver, By.XPATH, self.SELECTORS["signup_button"]
            )
            await self.anti_detection.simulate_mouse_movement(driver, signup_button)
            signup_button.click()
            
            # Wait for response
            await self.anti_detection.add_random_interaction_delay("page_load")
            
            # Check for error messages
            try:
                error_message = await self.element_selector.wait_and_find_element(
                    driver, By.XPATH, self.SELECTORS["error_message"], timeout=3
                )
                error_text = error_message.text
                logger.warning(f"Signup error: {error_text}")
                return False
            except (TimeoutException, NoSuchElementException):
                # No error message found, continue
                pass
            
            return True
            
        except Exception as e:
            logger.error(f"Error submitting signup form: {e}")
            return False
    
    async def _check_for_captcha(self, driver: WebDriver) -> bool:
        """
        Check if CAPTCHA is present on the page.
        
        Args:
            driver: WebDriver instance
            
        Returns:
            bool: True if CAPTCHA is detected
        """
        try:
            # Check for common CAPTCHA elements
            captcha_elements = driver.find_elements(By.XPATH, self.SELECTORS["captcha_container"])
            if captcha_elements:
                logger.warning("CAPTCHA detected")
                return True
            
            # Check for reCAPTCHA iframe
            recaptcha_frames = driver.find_elements(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
            if recaptcha_frames:
                logger.warning("reCAPTCHA detected")
                return True
            
            # Check for hCaptcha iframe
            hcaptcha_frames = driver.find_elements(By.XPATH, "//iframe[contains(@src, 'hcaptcha')]")
            if hcaptcha_frames:
                logger.warning("hCaptcha detected")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for CAPTCHA: {e}")
            return False
    
    async def _check_verification_required(self, driver: WebDriver) -> bool:
        """
        Check if email verification is required.
        
        Args:
            driver: WebDriver instance
            
        Returns:
            bool: True if verification is required
        """
        try:
            # Check for verification code field
            try:
                verification_field = await self.element_selector.wait_and_find_element(
                    driver, By.XPATH, self.SELECTORS["verification_code_field"], timeout=5
                )
                if verification_field:
                    logger.info("Email verification required")
                    return True
            except (TimeoutException, NoSuchElementException):
                pass
            
            # Check for text indicating verification
            verification_text_elements = driver.find_elements(
                By.XPATH, "//p[contains(text(), 'verification') or contains(text(), 'confirm')]"
            )
            if verification_text_elements:
                logger.info("Email verification required (text detected)")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for verification requirement: {e}")
            return False
    
    async def _handle_email_verification(self, driver: WebDriver, account_data: AccountData) -> bool:
        """
        Handle email verification process with improved error handling and retry logic.
        
        Args:
            driver: WebDriver instance
            account_data: Account data
            
        Returns:
            bool: True if verification was successful
        """
        try:
            logger.info(f"Starting email verification process for {account_data.email}")
            
            # Wait for verification code
            verification_code = await self._wait_for_verification_code(account_data.email)
            if not verification_code:
                logger.error("Failed to receive verification code")
                return False
            
            logger.info(f"Received verification code: {verification_code}")
            
            # Try to enter verification code with retry logic
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    # Enter verification code
                    verification_field = await self.element_selector.wait_and_find_element(
                        driver, By.XPATH, self.SELECTORS["verification_code_field"], timeout=10
                    )
                    
                    # Clear field first
                    verification_field.clear()
                    await self.anti_detection.add_random_interaction_delay("form_field")
                    
                    # Type verification code with human-like behavior
                    await self.anti_detection.simulate_human_typing(verification_field, verification_code)
                    await self.anti_detection.add_random_interaction_delay("form_field")
                    
                    # Click confirm button
                    confirm_button = await self.element_selector.wait_and_find_element(
                        driver, By.XPATH, self.SELECTORS["confirm_button"], timeout=5
                    )
                    await self.anti_detection.simulate_mouse_movement(driver, confirm_button)
                    confirm_button.click()
                    
                    # Wait for confirmation
                    await self.anti_detection.add_random_interaction_delay("page_load")
                    
                    # Check for error messages
                    try:
                        error_message = await self.element_selector.wait_and_find_element(
                            driver, By.XPATH, self.SELECTORS["error_message"], timeout=3
                        )
                        error_text = error_message.text
                        logger.warning(f"Verification error (attempt {attempt}/{max_attempts}): {error_text}")
                        
                        # Check if error indicates invalid code
                        if "invalid" in error_text.lower() or "incorrect" in error_text.lower():
                            if attempt < max_attempts:
                                # Wait before retrying
                                await asyncio.sleep(2)
                                continue
                            else:
                                return False
                    except (TimeoutException, NoSuchElementException):
                        # No error message found, verification likely successful
                        logger.info("Verification successful - no error messages detected")
                        
                        # Check for success indicators
                        try:
                            # Look for elements that indicate successful verification
                            success_indicators = [
                                "//h1[contains(text(), 'Welcome')]",
                                "//div[contains(text(), 'Account created')]",
                                "//button[contains(text(), 'Continue')]"
                            ]
                            
                            for indicator in success_indicators:
                                try:
                                    element = await self.element_selector.wait_and_find_element(
                                        driver, By.XPATH, indicator, timeout=2
                                    )
                                    if element:
                                        logger.info(f"Verification success indicator found: {indicator}")
                                        return True
                                except (TimeoutException, NoSuchElementException):
                                    continue
                            
                            # If we didn't find specific success indicators but also no errors,
                            # assume success
                            return True
                            
                        except Exception as e:
                            logger.warning(f"Error checking verification success: {e}")
                            # Assume success if no error was shown
                            return True
                    
                    # If we reach here, verification was likely successful
                    return True
                    
                except (TimeoutException, NoSuchElementException) as e:
                    logger.error(f"Error during verification attempt {attempt}/{max_attempts}: {e}")
                    if attempt < max_attempts:
                        # Wait before retrying
                        await asyncio.sleep(2)
                        continue
                    else:
                        return False
            
            # If we reach here, all attempts failed
            return False
            
        except Exception as e:
            logger.error(f"Error handling email verification: {e}")
            return False
    
    async def _wait_for_verification_code(self, email: str) -> Optional[str]:
        """
        Wait for verification code to arrive in email with improved handling.
        
        Args:
            email: Email address to check
            
        Returns:
            Optional[str]: Verification code if found, None otherwise
        """
        start_time = time.time()
        attempts = 0
        max_attempts = self.verification_timeout // self.verification_check_interval
        
        logger.info(f"Waiting for verification code for {email}, timeout: {self.verification_timeout}s")
        
        # Create email result structure for the email service handler
        email_data = {"email_address": email}
        
        while time.time() - start_time < self.verification_timeout:
            try:
                attempts += 1
                remaining_time = int(self.verification_timeout - (time.time() - start_time))
                logger.info(f"Verification attempt {attempts}/{max_attempts}, remaining time: {remaining_time}s")
                
                # Get messages for email
                messages = await self.email_service.get_messages(email_data)
                
                if messages:
                    # First try using the verification code extractor
                    for message in messages:
                        extraction_result = self.verification_extractor.extract_verification_code(message)
                        if extraction_result.code:
                            logger.info(f"Verification code found: {extraction_result.code} (confidence: {extraction_result.confidence:.2f})")
                            return extraction_result.code
                    
                    # If no code found, try extracting multiple codes and pick the highest confidence one
                    all_codes = []
                    for message in messages:
                        multiple_codes = self.verification_extractor.extract_multiple_codes(message)
                        all_codes.extend(multiple_codes)
                    
                    if all_codes:
                        # Sort by confidence and get the highest
                        all_codes.sort(key=lambda x: x.confidence, reverse=True)
                        best_code = all_codes[0]
                        if best_code.confidence > 0.5:  # Only use if confidence is reasonable
                            logger.info(f"Best verification code found: {best_code.code} (confidence: {best_code.confidence:.2f})")
                            return best_code.code
                
                # Wait before checking again
                await asyncio.sleep(self.verification_check_interval)
                
            except Exception as e:
                logger.error(f"Error waiting for verification code: {e}")
                await asyncio.sleep(self.verification_check_interval)
        
        logger.warning(f"Verification timeout for {email} after {attempts} attempts")
        return None
    
    async def _skip_additional_steps(self, driver: WebDriver) -> None:
        """
        Skip additional steps after account creation.
        
        Args:
            driver: WebDriver instance
        """
        try:
            # Look for skip buttons and click them
            skip_buttons = driver.find_elements(By.XPATH, self.SELECTORS["skip_button"])
            for button in skip_buttons:
                try:
                    await self.anti_detection.simulate_mouse_movement(driver, button)
                    button.click()
                    await self.anti_detection.add_random_interaction_delay("button")
                except Exception:
                    continue
            
        except Exception as e:
            logger.error(f"Error skipping additional steps: {e}")
    
    async def _save_account_credentials(self, account_data: AccountData) -> bool:
        """
        Save account credentials to configuration file with secure storage.
        
        Args:
            account_data: Account data to save
            
        Returns:
            bool: True if saved successfully
        """
        try:
            # Validate account data before saving
            if not self._validate_account_data_for_saving(account_data):
                logger.error(f"Invalid account data for {account_data.username}, not saving")
                return False
            
            # Load existing accounts
            existing_accounts = await self._load_existing_accounts()
            
            # Check for duplicates
            for existing in existing_accounts:
                if existing.get("username") == account_data.username:
                    logger.warning(f"Account {account_data.username} already exists, updating")
                    existing_accounts.remove(existing)
                    break
            
            # Add new account with complete data
            new_account = {
                # Basic credentials
                "username": account_data.username,
                "password": account_data.password,
                "email": account_data.email,
                "full_name": account_data.full_name,
                
                # Status and timestamps
                "status": account_data.status.value,
                "created_at": account_data.created_at.isoformat() if account_data.created_at else None,
                "verified_at": account_data.verified_at.isoformat() if account_data.verified_at else None,
                "last_login": account_data.last_login.isoformat() if account_data.last_login else None,
                
                # Additional profile data
                "birth_date": account_data.birth_date.isoformat() if account_data.birth_date else None,
                "gender": account_data.gender.value if account_data.gender else None,
                "phone_number": account_data.phone_number,
                "profile_picture_url": account_data.profile_picture_url,
                "bio": account_data.bio,
                
                # Technical metadata
                "proxy_used": account_data.proxy_used,
                "user_agent_used": account_data.user_agent_used,
                "creation_ip": account_data.creation_ip,
                
                # Additional metadata
                "metadata": account_data.metadata
            }
            
            existing_accounts.append(new_account)
            
            # Create backup of existing file if it exists
            if os.path.exists(self.credentials_file):
                backup_file = f"{self.credentials_file}.bak"
                try:
                    with open(self.credentials_file, 'r') as src, open(backup_file, 'w') as dst:
                        dst.write(src.read())
                    logger.info(f"Created backup of credentials file: {backup_file}")
                except Exception as e:
                    logger.warning(f"Failed to create backup: {e}")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.credentials_file), exist_ok=True)
            
            # Save updated accounts with secure file handling
            temp_file = f"{self.credentials_file}.tmp"
            try:
                # Write to temporary file first
                with open(temp_file, 'w') as f:
                    json.dump({"bots": existing_accounts}, f, indent=2)
                
                # Rename temporary file to actual file (atomic operation)
                os.replace(temp_file, self.credentials_file)
                
                logger.info(f"Saved credentials for {account_data.username}")
                return True
                
            except Exception as e:
                logger.error(f"Error writing credentials file: {e}")
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                return False
            
        except Exception as e:
            logger.error(f"Error saving account credentials: {e}")
            return False
    
    def _validate_account_data_for_saving(self, account_data: AccountData) -> bool:
        """
        Validate account data before saving.
        
        Args:
            account_data: Account data to validate
            
        Returns:
            bool: True if data is valid
        """
        # Check required fields
        if not account_data.username or not account_data.password or not account_data.email:
            logger.error("Missing required account fields (username, password, or email)")
            return False
        
        # Validate username format
        if not re.match(r'^[a-zA-Z0-9_.]{3,30}$', account_data.username):
            logger.error(f"Invalid username format: {account_data.username}")
            return False
        
        # Validate email format
        if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', account_data.email):
            logger.error(f"Invalid email format: {account_data.email}")
            return False
        
        # Validate password strength
        if len(account_data.password) < 8:
            logger.error("Password too short (minimum 8 characters)")
            return False
        
        # Check status
        if not account_data.status:
            logger.warning("Account status not set, defaulting to CREATED")
            account_data.status = AccountStatus.CREATED
        
        # Set creation timestamp if not set
        if not account_data.created_at:
            logger.warning("Creation timestamp not set, using current time")
            account_data.created_at = datetime.now()
        
        return True
    
    async def _load_existing_accounts(self) -> List[Dict[str, Any]]:
        """
        Load existing accounts from configuration file with error handling.
        
        Returns:
            List[Dict[str, Any]]: List of existing accounts
        """
        try:
            if not os.path.exists(self.credentials_file):
                logger.info(f"Credentials file {self.credentials_file} does not exist, returning empty list")
                return []
            
            # Try to load the main file
            try:
                with open(self.credentials_file, 'r') as f:
                    data = json.load(f)
                return data.get("bots", [])
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing credentials file: {e}")
                
                # Try to load from backup
                backup_file = f"{self.credentials_file}.bak"
                if os.path.exists(backup_file):
                    logger.info(f"Attempting to restore from backup: {backup_file}")
                    try:
                        with open(backup_file, 'r') as f:
                            backup_data = json.load(f)
                        
                        # Restore from backup
                        with open(self.credentials_file, 'w') as f:
                            json.dump(backup_data, f, indent=2)
                        
                        logger.info("Successfully restored from backup")
                        return backup_data.get("bots", [])
                        
                    except Exception as backup_error:
                        logger.error(f"Failed to restore from backup: {backup_error}")
                
                # If we get here, both main file and backup failed
                return []
            
        except Exception as e:
            logger.error(f"Error loading existing accounts: {e}")
            return []
    
    async def get_account_by_username(self, username: str) -> Optional[AccountData]:
        """
        Get account data by username.
        
        Args:
            username: Username to look for
            
        Returns:
            Optional[AccountData]: Account data if found, None otherwise
        """
        try:
            existing_accounts = await self._load_existing_accounts()
            
            for account in existing_accounts:
                if account.get("username") == username:
                    # Convert to AccountData object
                    try:
                        return AccountData.from_dict(account)
                    except Exception as e:
                        logger.error(f"Error converting account data: {e}")
                        return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting account by username: {e}")
            return None
    
    async def get_all_accounts(self) -> List[AccountData]:
        """
        Get all accounts.
        
        Returns:
            List[AccountData]: List of all accounts
        """
        try:
            existing_accounts = await self._load_existing_accounts()
            result = []
            
            for account in existing_accounts:
                try:
                    account_data = AccountData.from_dict(account)
                    result.append(account_data)
                except Exception as e:
                    logger.error(f"Error converting account data: {e}")
                    continue
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting all accounts: {e}")
            return []
    
    async def delete_account(self, username: str) -> bool:
        """
        Delete account by username.
        
        Args:
            username: Username to delete
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            existing_accounts = await self._load_existing_accounts()
            
            for i, account in enumerate(existing_accounts):
                if account.get("username") == username:
                    del existing_accounts[i]
                    
                    # Save updated accounts
                    with open(self.credentials_file, 'w') as f:
                        json.dump({"bots": existing_accounts}, f, indent=2)
                    
                    logger.info(f"Deleted account: {username}")
                    return True
            
            logger.warning(f"Account not found for deletion: {username}")
            return False
            
        except Exception as e:
            logger.error(f"Error deleting account: {e}")
            return False
    
    def _generate_username(self) -> str:
        """
        Generate a random Instagram-friendly username.
        
        Returns:
            str: Generated username
        """
        # Username patterns
        patterns = [
            "{word}{number}",
            "{word}_{word}",
            "{word}.{word}",
            "_{word}{number}_",
            "{word}{number}{number}",
            "{word}.{number}",
            "{letter}_{word}",
            "{word}{letter}{number}"
        ]
        
        words = [
            "photo", "insta", "gram", "pic", "snap", "shot", "view", "moment",
            "capture", "lens", "focus", "frame", "image", "pixel", "story",
            "visual", "memory", "scene", "click", "shutter", "filter"
        ]
        
        # Generate username
        pattern = random.choice(patterns)
        username = pattern.format(
            word=random.choice(words),
            number=random.randint(1, 9999),
            letter=random.choice(string.ascii_lowercase)
        )
        
        # Add random suffix if needed
        if len(username) < 8:
            username += str(random.randint(10, 999))
        
        return username
    
    def _generate_full_name(self) -> str:
        """
        Generate a random full name.
        
        Returns:
            str: Generated full name
        """
        first_names = [
            "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph",
            "Thomas", "Charles", "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth",
            "Barbara", "Susan", "Jessica", "Sarah", "Karen", "Emma", "Olivia", "Noah",
            "Liam", "Mason", "Jacob", "Sophia", "Isabella", "Mia", "Charlotte"
        ]
        
        last_names = [
            "Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson",
            "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris",
            "Martin", "Thompson", "Garcia", "Martinez", "Robinson", "Clark", "Rodriguez",
            "Lewis", "Lee", "Walker", "Hall", "Allen", "Young", "King", "Wright"
        ]
        
        return f"{random.choice(first_names)} {random.choice(last_names)}"
    
    def _generate_strong_password(self) -> str:
        """
        Generate a strong but memorable password.
        
        Returns:
            str: Generated password
        """
        # Password components
        words = [
            "photo", "sunset", "ocean", "mountain", "forest", "river", "desert",
            "island", "camera", "picture", "memory", "moment", "capture", "image",
            "scene", "view", "landscape", "portrait", "filter", "frame", "lens"
        ]
        
        special_chars = "!@#$%^&*"
        
        # Generate password
        word1 = random.choice(words).capitalize()
        word2 = random.choice(words)
        number = random.randint(100, 999)
        special = random.choice(special_chars)
        
        return f"{word1}{special}{word2}{number}"
    
    def _generate_birth_date(self, min_age: int = 18, max_age: int = 45) -> date:
        """
        Generate a random birth date within age range.
        
        Args:
            min_age: Minimum age
            max_age: Maximum age
            
        Returns:
            date: Generated birth date
        """
        today = date.today()
        min_date = date(today.year - max_age, today.month, today.day)
        max_date = date(today.year - min_age, today.month, today.day)
        
        # Calculate days between min and max dates
        days_between = (max_date - min_date).days
        
        # Generate random date
        random_days = random.randint(0, days_between)
        random_date = min_date + timedelta(days=random_days)
        
        return random_date
    
    def _generate_random_string(self, length: int) -> str:
        """
        Generate a random string of specified length.
        
        Args:
            length: Length of string
            
        Returns:
            str: Random string
        """
        chars = string.ascii_lowercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))