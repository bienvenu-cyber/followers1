# Instagram Auto Signup System

Automated Instagram account creation with advanced anti-detection, proxy rotation, and email verification.

## Features

- **Automated Account Creation**: Create Instagram accounts automatically with minimal human intervention
- **Anti-Detection Measures**: Simulate human behavior to avoid bot detection
- **Proxy Rotation**: Automatically rotate proxies to avoid IP bans
- **Email Verification**: Handle email verification codes automatically
- **Performance Optimization**: Adaptive system that learns from successes and failures
- **Resource Management**: Intelligent management of proxies and user agents
- **Comprehensive Logging**: Detailed logs for troubleshooting and analysis
- **Configuration Management**: Flexible configuration with hot-reload capability

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/instagram-auto-signup.git
   cd instagram-auto-signup
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure the system:
   - Edit `config/system_config.json` to set your preferences
   - Add proxies and email services in the configuration file

## Usage

### Quick Start

To create a single account:

```bash
python auto_signup.py
```

To create multiple accounts:

```bash
python auto_signup.py --accounts 5
```

To run in continuous mode:

```bash
python auto_signup.py --continuous
```

### Advanced Usage

For more control over the system:

```bash
python start.py
```

This provides additional options like:

- `--config`: Use a custom configuration profile
- `--validate-only`: Only validate configuration and exit
- `--verbose`: Enable verbose logging
- `--daemon`: Run as a background process

### Configuration Validation

To validate your configuration:

```bash
python validate_config.py
```

## Configuration

The system is configured through JSON files:

- `config/system_config.json`: Main system configuration
- `config/bots_credentials.json`: Stores created account credentials

### Example Configuration

```json
{
  "creation_interval": 300,
  "max_concurrent_creations": 3,
  "browser_type": "chrome",
  "headless": true,
  "email_services": [
    {"name": "temp-mail", "priority": 1},
    {"name": "10minutemail", "priority": 2}
  ],
  "proxies": [
    {"ip": "192.168.1.1", "port": 8080, "type": "http"},
    {"ip": "192.168.1.2", "port": 8080, "type": "http"}
  ]
}
```

## Directory Structure

- `src/`: Source code
  - `core/`: Core system components
  - `services/`: Service implementations
  - `managers/`: Resource managers
  - `models/`: Data models
  - `ui/`: User interface components
- `tests/`: Test files
- `config/`: Configuration files
- `logs/`: Log files

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational purposes only. Use responsibly and in accordance with Instagram's Terms of Service.