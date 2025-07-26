#!/usr/bin/env python3
"""
Configuration validation script for Instagram Auto Signup System.

This script validates the system configuration and provides detailed
feedback about any issues or recommendations.
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Any

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.system_initializer import system_initializer


def print_header():
    """Print validation header."""
    print("=" * 60)
    print("Instagram Auto Signup System - Configuration Validator")
    print("=" * 60)
    print()


def print_section(title: str):
    """Print section header."""
    print(f"\n📋 {title}")
    print("-" * (len(title) + 4))


def print_success(message: str):
    """Print success message."""
    print(f"✅ {message}")


def print_warning(message: str):
    """Print warning message."""
    print(f"⚠️  {message}")


def print_error(message: str):
    """Print error message."""
    print(f"❌ {message}")


def print_info(message: str):
    """Print info message."""
    print(f"ℹ️  {message}")


def validate_file_structure():
    """Validate required file structure."""
    print_section("File Structure Validation")
    
    required_files = [
        "config/system_config.json",
        "config/bots_credentials.json",
        "src/__init__.py",
        "main.py"
    ]
    
    required_dirs = [
        "src",
        "config",
        "tests"
    ]
    
    all_valid = True
    
    # Check required files
    for file_path in required_files:
        if os.path.exists(file_path):
            print_success(f"Found: {file_path}")
        else:
            print_error(f"Missing: {file_path}")
            all_valid = False
    
    # Check required directories
    for dir_path in required_dirs:
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            print_success(f"Directory exists: {dir_path}")
        else:
            print_error(f"Missing directory: {dir_path}")
            all_valid = False
    
    # Check optional directories
    optional_dirs = ["logs", "temp", "screenshots", "data"]
    for dir_path in optional_dirs:
        if os.path.exists(dir_path):
            print_info(f"Optional directory exists: {dir_path}")
        else:
            print_warning(f"Optional directory missing (will be created): {dir_path}")
    
    return all_valid


def validate_json_files():
    """Validate JSON configuration files."""
    print_section("JSON Configuration Validation")
    
    json_files = [
        "config/system_config.json",
        "config/bots_credentials.json"
    ]
    
    all_valid = True
    
    for file_path in json_files:
        if not os.path.exists(file_path):
            print_error(f"File not found: {file_path}")
            all_valid = False
            continue
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            print_success(f"Valid JSON: {file_path}")
            
            # Check file permissions
            if os.access(file_path, os.R_OK):
                print_info(f"Readable: {file_path}")
            else:
                print_error(f"Not readable: {file_path}")
                all_valid = False
            
            if os.access(file_path, os.W_OK):
                print_info(f"Writable: {file_path}")
            else:
                print_warning(f"Not writable: {file_path}")
            
        except json.JSONDecodeError as e:
            print_error(f"Invalid JSON in {file_path}: {e}")
            all_valid = False
        except Exception as e:
            print_error(f"Error reading {file_path}: {e}")
            all_valid = False
    
    return all_valid


def validate_system_config():
    """Validate system configuration content."""
    print_section("System Configuration Content Validation")
    
    config_file = "config/system_config.json"
    
    if not os.path.exists(config_file):
        print_error(f"Configuration file not found: {config_file}")
        return False
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print_error(f"Cannot read configuration: {e}")
        return False
    
    all_valid = True
    
    # Required configuration keys
    required_keys = {
        "creation_interval": (int, float),
        "max_concurrent_creations": int,
        "browser_type": str,
        "email_services": list,
        "proxies": list
    }
    
    # Check required keys
    for key, expected_type in required_keys.items():
        if key not in config:
            print_error(f"Missing required key: {key}")
            all_valid = False
        else:
            value = config[key]
            if isinstance(expected_type, tuple):
                if not isinstance(value, expected_type):
                    print_error(f"Invalid type for {key}: expected {expected_type}, got {type(value)}")
                    all_valid = False
                else:
                    print_success(f"Valid key: {key} = {value}")
            else:
                if not isinstance(value, expected_type):
                    print_error(f"Invalid type for {key}: expected {expected_type}, got {type(value)}")
                    all_valid = False
                else:
                    print_success(f"Valid key: {key} = {value}")
    
    # Validate specific values
    if "creation_interval" in config:
        if config["creation_interval"] <= 0:
            print_error("creation_interval must be greater than 0")
            all_valid = False
        elif config["creation_interval"] < 60:
            print_warning(f"creation_interval is very low ({config['creation_interval']}s) - may cause rate limiting")
    
    if "max_concurrent_creations" in config:
        if config["max_concurrent_creations"] <= 0:
            print_error("max_concurrent_creations must be greater than 0")
            all_valid = False
        elif config["max_concurrent_creations"] > 10:
            print_warning(f"max_concurrent_creations is high ({config['max_concurrent_creations']}) - may cause resource issues")
    
    if "browser_type" in config:
        valid_browsers = ["chrome", "firefox", "edge"]
        if config["browser_type"] not in valid_browsers:
            print_error(f"Invalid browser_type: {config['browser_type']}. Must be one of: {valid_browsers}")
            all_valid = False
    
    # Validate email services
    if "email_services" in config:
        if not config["email_services"]:
            print_error("email_services cannot be empty")
            all_valid = False
        else:
            for i, service in enumerate(config["email_services"]):
                if not isinstance(service, dict):
                    print_error(f"Email service {i} must be a dictionary")
                    all_valid = False
                    continue
                
                if "name" not in service:
                    print_error(f"Email service {i} missing 'name' field")
                    all_valid = False
                else:
                    print_success(f"Email service: {service['name']}")
                
                if "priority" not in service:
                    print_warning(f"Email service {i} missing 'priority' field")
                elif not isinstance(service["priority"], int):
                    print_error(f"Email service {i} priority must be an integer")
                    all_valid = False
    
    # Validate proxies
    if "proxies" in config:
        if not config["proxies"]:
            print_warning("No proxies configured - system will use direct connection")
        else:
            for i, proxy in enumerate(config["proxies"]):
                if not isinstance(proxy, dict):
                    print_error(f"Proxy {i} must be a dictionary")
                    all_valid = False
                    continue
                
                required_proxy_fields = ["ip", "port"]
                for field in required_proxy_fields:
                    if field not in proxy:
                        print_error(f"Proxy {i} missing '{field}' field")
                        all_valid = False
                
                if "ip" in proxy and "port" in proxy:
                    print_success(f"Proxy: {proxy['ip']}:{proxy['port']}")
                
                if "type" in proxy:
                    valid_types = ["http", "https", "socks4", "socks5"]
                    if proxy["type"] not in valid_types:
                        print_warning(f"Proxy {i} has unsupported type: {proxy['type']}")
    
    return all_valid


def validate_credentials_file():
    """Validate credentials file structure."""
    print_section("Credentials File Validation")
    
    creds_file = "config/bots_credentials.json"
    
    if not os.path.exists(creds_file):
        print_error(f"Credentials file not found: {creds_file}")
        return False
    
    try:
        with open(creds_file, 'r') as f:
            creds = json.load(f)
    except Exception as e:
        print_error(f"Cannot read credentials file: {e}")
        return False
    
    all_valid = True
    
    # Check structure
    if "bots" not in creds:
        print_error("Credentials file missing 'bots' key")
        all_valid = False
    else:
        bots = creds["bots"]
        if not isinstance(bots, list):
            print_error("'bots' must be a list")
            all_valid = False
        else:
            print_success(f"Found {len(bots)} bot accounts")
            
            # Validate each bot account
            for i, bot in enumerate(bots):
                if not isinstance(bot, dict):
                    print_error(f"Bot {i} must be a dictionary")
                    all_valid = False
                    continue
                
                required_fields = ["username", "password", "email"]
                for field in required_fields:
                    if field not in bot:
                        print_warning(f"Bot {i} missing '{field}' field")
                    else:
                        if field == "password":
                            print_info(f"Bot {i} has {field}: [HIDDEN]")
                        else:
                            print_info(f"Bot {i} has {field}: {bot[field]}")
    
    return all_valid


def check_dependencies():
    """Check Python dependencies."""
    print_section("Python Dependencies Check")
    
    required_packages = [
        "selenium",
        "requests",
        "aiohttp",
        "psutil"
    ]
    
    all_available = True
    
    for package in required_packages:
        try:
            __import__(package)
            print_success(f"Package available: {package}")
        except ImportError:
            print_error(f"Package missing: {package}")
            all_available = False
    
    # Check optional packages
    optional_packages = [
        "webdriver_manager",
        "fake_useragent",
        "python-daemon"
    ]
    
    for package in optional_packages:
        try:
            __import__(package)
            print_info(f"Optional package available: {package}")
        except ImportError:
            print_warning(f"Optional package missing: {package}")
    
    return all_available


async def run_system_validation():
    """Run full system validation."""
    print_section("Full System Validation")
    
    try:
        result = await system_initializer.initialize_system()
        
        if result.success:
            print_success("System validation passed")
            if result.warnings:
                print_info("Warnings found:")
                for warning in result.warnings:
                    print_warning(warning)
            return True
        else:
            print_error(f"System validation failed: {result.message}")
            if result.failed_components:
                print_info("Failed components:")
                for component in result.failed_components:
                    print_error(component)
            return False
    
    except Exception as e:
        print_error(f"System validation error: {e}")
        return False


def print_recommendations():
    """Print configuration recommendations."""
    print_section("Recommendations")
    
    recommendations = [
        "Keep creation_interval >= 300 seconds to avoid rate limiting",
        "Use multiple proxy servers for better reliability",
        "Configure multiple email services for fallback",
        "Monitor system logs regularly for issues",
        "Keep browser drivers updated",
        "Use headless mode for better performance",
        "Enable performance optimization for adaptive behavior",
        "Backup configuration files regularly"
    ]
    
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")


async def main():
    """Main validation function."""
    print_header()
    
    validation_results = []
    
    # Run all validations
    validation_results.append(("File Structure", validate_file_structure()))
    validation_results.append(("JSON Files", validate_json_files()))
    validation_results.append(("System Config", validate_system_config()))
    validation_results.append(("Credentials File", validate_credentials_file()))
    validation_results.append(("Dependencies", check_dependencies()))
    validation_results.append(("System Validation", await run_system_validation()))
    
    # Print summary
    print_section("Validation Summary")
    
    all_passed = True
    for name, result in validation_results:
        if result:
            print_success(f"{name}: PASSED")
        else:
            print_error(f"{name}: FAILED")
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All validations passed! System is ready to run.")
    else:
        print("⚠️  Some validations failed. Please fix the issues before running the system.")
    
    # Print recommendations
    print_recommendations()
    
    return all_passed


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 Validation cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Validation error: {e}")
        sys.exit(1)