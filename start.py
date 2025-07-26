#!/usr/bin/env python3
"""
Instagram Auto Signup System - Startup Script

This script provides a convenient way to start the Instagram auto signup system
with various options and configurations.
"""

import asyncio
import sys
import os
import argparse
import logging
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from main import InstagramAutoSignupSystem
from src.core.system_initializer import system_initializer


def setup_argument_parser():
    """Setup command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Instagram Auto Signup System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start.py                    # Start with default settings
  python start.py --config custom   # Use custom configuration
  python start.py --validate-only   # Only validate configuration
  python start.py --verbose         # Enable verbose logging
  python start.py --daemon          # Run as daemon (background)
        """
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="default",
        help="Configuration profile to use (default: default)"
    )
    
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate configuration and exit"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as daemon (background process)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--log-file",
        type=str,
        help="Custom log file path"
    )
    
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output"
    )
    
    return parser


def setup_logging(args):
    """Setup logging based on command line arguments."""
    # Determine log level
    log_level = getattr(logging, args.log_level.upper())
    
    # Setup log format
    if args.no_color:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    else:
        # Add colors for different log levels
        class ColoredFormatter(logging.Formatter):
            COLORS = {
                'DEBUG': '\033[36m',    # Cyan
                'INFO': '\033[32m',     # Green
                'WARNING': '\033[33m',  # Yellow
                'ERROR': '\033[31m',    # Red
                'CRITICAL': '\033[35m', # Magenta
            }
            RESET = '\033[0m'
            
            def format(self, record):
                log_color = self.COLORS.get(record.levelname, '')
                record.levelname = f"{log_color}{record.levelname}{self.RESET}"
                return super().format(record)
        
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Setup handlers
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if args.no_color:
        console_handler.setFormatter(logging.Formatter(log_format))
    else:
        console_handler.setFormatter(ColoredFormatter(log_format))
    
    handlers.append(console_handler)
    
    # File handler
    log_file = args.log_file or "logs/instagram_auto_signup.log"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        format=log_format
    )
    
    # Set specific logger levels
    if args.verbose:
        logging.getLogger("selenium").setLevel(logging.DEBUG)
        logging.getLogger("urllib3").setLevel(logging.DEBUG)
    else:
        logging.getLogger("selenium").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)


def print_banner():
    """Print system banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                Instagram Auto Signup System                  ║
║                                                              ║
║  Automated Instagram account creation with advanced          ║
║  anti-detection, proxy rotation, and email verification     ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


async def validate_system():
    """Validate system configuration and dependencies."""
    print("🔍 Validating system configuration and dependencies...")
    
    result = await system_initializer.initialize_system()
    
    if result.success:
        print("✅ System validation passed")
        if result.warnings:
            print("⚠️  Warnings:")
            for warning in result.warnings:
                print(f"   - {warning}")
        return True
    else:
        print(f"❌ System validation failed: {result.message}")
        if result.failed_components:
            print("Failed components:")
            for component in result.failed_components:
                print(f"   - {component}")
        return False


async def run_system(args):
    """Run the Instagram auto signup system."""
    try:
        print("🚀 Starting Instagram Auto Signup System...")
        
        # Create and initialize system
        system = InstagramAutoSignupSystem()
        
        if not await system.initialize():
            print("❌ System initialization failed")
            return False
        
        print("✅ System initialized successfully")
        print("🔄 Starting account creation process...")
        
        # Run system
        await system.run()
        
        return True
        
    except KeyboardInterrupt:
        print("\n⏹️  Received shutdown signal")
        return True
    except Exception as e:
        print(f"❌ System error: {e}")
        return False


def run_as_daemon():
    """Run the system as a daemon process."""
    try:
        import daemon
        import daemon.pidfile
        
        # Create PID file
        pid_file = daemon.pidfile.PIDLockFile("/tmp/instagram_auto_signup.pid")
        
        # Setup daemon context
        with daemon.DaemonContext(pidfile=pid_file):
            asyncio.run(run_system(None))
            
    except ImportError:
        print("❌ python-daemon package required for daemon mode")
        print("Install with: pip install python-daemon")
        return False
    except Exception as e:
        print(f"❌ Failed to start daemon: {e}")
        return False


async def main():
    """Main entry point."""
    # Parse command line arguments
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args)
    
    # Print banner
    if not args.no_color:
        print_banner()
    
    # Validate system
    if not await validate_system():
        sys.exit(1)
    
    # If validate-only mode, exit after validation
    if args.validate_only:
        print("✅ Validation complete - exiting")
        return
    
    # Run system
    if args.daemon:
        print("🔧 Starting in daemon mode...")
        success = run_as_daemon()
    else:
        success = await run_system(args)
    
    if success:
        print("👋 System shutdown complete")
    else:
        print("❌ System exited with errors")
        sys.exit(1)


if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    # Run main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Startup failed: {e}")
        sys.exit(1)