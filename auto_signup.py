#!/usr/bin/env python3
"""
Instagram Auto Signup - Quick Start Script

This script provides a simple way to start the Instagram auto signup system
with default settings.
"""

import asyncio
import sys
import os
import logging
import argparse
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from main import InstagramAutoSignupSystem


def setup_logging():
    """Setup logging configuration."""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/instagram_auto_signup.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def print_banner():
    """Print system banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                Instagram Auto Signup System                  ║
║                                                              ║
║  Automated Instagram account creation with advanced          ║
║  anti-detection, proxy rotation, and email verification      ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


async def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Instagram Auto Signup System")
    parser.add_argument("--accounts", type=int, default=1, help="Number of accounts to create")
    parser.add_argument("--continuous", action="store_true", help="Run in continuous mode")
    parser.add_argument("--interval", type=int, default=300, help="Interval between account creations in seconds")
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    # Print banner
    print_banner()
    
    # Create and initialize system
    print("🚀 Starting Instagram Auto Signup System...")
    system = InstagramAutoSignupSystem()
    
    if not await system.initialize():
        print("❌ System initialization failed")
        return False
    
    print("✅ System initialized successfully")
    
    # Run system
    if args.continuous:
        print(f"🔄 Starting continuous account creation with {args.interval}s interval...")
        system.main_controller.start_continuous_creation()
        
        try:
            # Wait for keyboard interrupt
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n⏹️  Stopping account creation...")
            system.main_controller.stop_creation()
    else:
        print(f"🔄 Creating {args.accounts} account(s)...")
        
        for i in range(args.accounts):
            if i > 0:
                print(f"⏳ Waiting {args.interval} seconds before next account creation...")
                await asyncio.sleep(args.interval)
            
            print(f"📝 Creating account {i+1}/{args.accounts}...")
            result = await system.main_controller._create_single_account()
            
            if result:
                print("✅ Account created successfully")
            else:
                print("❌ Account creation failed")
    
    # Shutdown system
    print("👋 Shutting down...")
    await system.shutdown()
    
    return True


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)