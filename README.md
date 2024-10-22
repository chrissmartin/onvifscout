# ONVIF Scout

A comprehensive ONVIF device discovery and analysis tool that helps you find, authenticate, and examine ONVIF-compatible devices on your network. ONVIF Scout provides robust device detection, credential testing, and detailed capability analysis with an intuitive command-line interface.

## 🌟 Features

### Device Discovery

- Uses WS-Discovery protocol for device detection
- Supports multiple network interfaces
- Configurable timeout and retry settings
- Automatic response parsing and validation

### Authentication Probe

- Concurrent credential testing with configurable workers
- Support for both Basic and Digest authentication
- Automatic auth type detection
- Built-in retry mechanism for reliability
- Progress tracking for long operations

### Feature Detection

- Comprehensive capability analysis
- Service enumeration
- Device information retrieval
- PTZ capabilities detection
- Media profile inspection
- Analytics support detection

### User Interface

- Color-coded console output
- Progress bars for long operations
- Detailed debug logging option
- Clean, organized results display
- Support for quiet mode

## 📋 Requirements

- Python 3.8 or higher
- Network access to ONVIF devices
- Required packages:
  - colorama >= 0.4.6
  - requests >= 2.32.3

## 🚀 Installation

### Using pip (Recommended)

```bash
pip install onvifscout
```

### From Source

```bash
# Clone the repository
git clone https://github.com/chrissmartin/onvifscout.git
cd onvifscout

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Linux/MacOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

## 🛠️ Usage

### Basic Command

```bash
onvifscout
```

### Command-Line Options

```
Optional arguments:
  -h, --help            Show this help message
  --timeout SECS        Discovery timeout in seconds (default: 3)
  --max-workers NUM     Maximum concurrent authentication attempts (default: 5)
  --usernames LIST      Comma-separated list of usernames to try
  --passwords LIST      Comma-separated list of passwords to try
  --skip-auth          Skip authentication probe
  --skip-features      Skip feature detection
  --no-color           Disable colored output
  --quiet              Suppress non-essential output
  --debug              Enable debug logging
```

### Example Commands

```bash
# Extended discovery timeout and more concurrent workers
onvifscout --timeout 5 --max-workers 10

# Custom credential lists
onvifscout --usernames admin,root,operator --passwords admin,12345,password123

# Quick discovery only (skip auth and feature detection)
onvifscout --skip-auth --skip-features

# Debug mode with extended timeout
onvifscout --debug --timeout 10

# Quiet mode with custom credentials
onvifscout --quiet --usernames admin --passwords admin,12345
```

### Default Credentials

The tool tests the following default credentials unless otherwise specified:

- Usernames: `admin`, `root`, `service`
- Passwords: `admin`, `12345`, `password`

## 📁 Project Structure

```
onvifscout/
├── onvifscout/
│   ├── __init__.py        # Package initialization
│   ├── main.py            # CLI entry point
│   ├── auth.py            # Authentication handling
│   ├── discovery.py       # Device discovery
│   ├── features.py        # Feature detection
│   ├── models.py          # Data models
│   ├── utils.py           # Utilities and logging
│   └── help_formatter.py  # Help message formatting
├── setup.py               # Package configuration
├── requirements.txt       # Dependencies
└── README.md             # Documentation
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests, create issues, or suggest improvements.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

## ✉️ Contact

Project Link: [https://github.com/chrissmartin/onvifscout](https://github.com/chrissmartin/onvifscout)
