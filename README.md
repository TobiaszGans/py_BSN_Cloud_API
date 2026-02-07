# BSN Cloud API Python Library

A comprehensive Python library for interacting with the BrightSign Network (BSN) Cloud API. This library provides easy-to-use functions for managing BrightSign players remotely. At the moment, most non-DWS-related functions are not supported; this release focuses on remote DWS functionality.

## Features

- **Automatic Authentication** - Handles OAuth2 authentication and automatic token renewal
- **Extensive rDWS API Coverage** – Covers the majority of remote DWS-related BSN Cloud API endpoints
- **File Management** - Upload, download, and manage files on BrightSign players
- **Device Control** - Reboot, configure, and control BrightSign devices remotely
- **Diagnostics** - Run network diagnostics, ping tests, and packet captures
- **Video & Display Control** - Manage video modes and display settings
- **Registry Management** - Read and modify player registry settings
- **Storage Operations** - Manage SD cards and other storage devices
- **Advanced Features** - SSH, DWS, firmware updates, and more

## Installation

```bash
pip install bsn-cloud-api
```

## Quick Start

### Method 1: Using Environment Variables (Recommended)

Create a `.env` file in your project root:

```env
BSN_CLIENT_ID=your_client_id_here
BSN_SECRET=your_client_secret_here
BSN_NETWORK=your_network_name_here
```

Then use the library:

```python
import bsn_cloud_api as bsn

# Get all devices
devices = bsn.get_devices()

# Reboot a player
result = bsn.reboot_device("SERIAL123")

# Upload a file to a player
bsn.put_device_files(
    serial_number="SERIAL123",
    local_file_path="video.mp4",
    file_path="media/videos"
)
```

### Method 2: Programmatic Configuration

```python
import bsn_cloud_api as bsn

# Configure credentials in code
bsn.configure(
    client_id="your_client_id",
    secret="your_secret",
    network="your_network"
)

# Now use the API
devices = bsn.get_devices()
```

### Method 3: System Environment Variables

Set environment variables in your system:

```bash
export BSN_CLIENT_ID="your_client_id"
export BSN_SECRET="your_secret"
export BSN_NETWORK="your_network"
```

Then use the library without any configuration.

## Authentication

The library automatically handles authentication for you:

The library automatically manages OAuth2 authentication for all API requests.

Lazy Initialization – No authentication or network requests are made until the first API call.

Automatic Login – Authentication is performed automatically when required.

Token Validity Checking – Before every API request, the library verifies that a valid access token is available.

Automatic Token Refresh – If the access token has expired, a new token is fetched automatically.

Time-Based Expiration – Token validity is determined using the expiration timestamp returned by the OAuth provider.

Network Selection – The configured BSN network is selected automatically after authentication.

Most authentication-related failures are returned as dictionaries containing an error key. Network-level issues (such as connectivity problems) may still raise exceptions from the underlying HTTP library.

You do not need to call login() manually in normal usage — authentication is handled transparently.

## API Credentials

To get your BSN Cloud API credentials:

1. Log in to https://adminpanel.bsn.cloud
2. Select your network
3. Navigate to **Settings** → **Applications**
4. Create a new Application or use an existing one
5. Copy your **Client ID**, **Client Secret**

## Usage Examples

### Device Management

```python
# Get all devices
devices = bsn.get_devices()

# Get devices filtered by site
devices = bsn.get_devices(description="London HQ")

# Get specific device info
device = bsn.get_device("SERIAL123")

# Reboot a device
bsn.reboot_device("SERIAL123")

# Factory reset a device
bsn.reboot_device("SERIAL123", factory_reset=True)
```

### File Operations

```python
# List files on SD card
files = bsn.get_device_files("SERIAL123", storage_type="sd", path="media")

# Upload a file
bsn.put_device_files(
    serial_number="SERIAL123",
    local_file_path="/local/path/video.mp4",
    storage_type="sd",
    file_path="media/videos",
    dest_filename="intro.mp4"
)

# Create a directory
bsn.create_device_directory("SERIAL123", "media/videos")

# Delete a file
bsn.delete_device_file("SERIAL123", "media/old_video.mp4")

# Rename a file
bsn.rename_device_file("SERIAL123", "media/video.mp4", "intro.mp4")
```

### Diagnostics

```python
# Run full network diagnostics
diagnostics = bsn.get_device_diagnostics("SERIAL123")

# Ping a server
ping_result = bsn.get_device_ping("SERIAL123", "8.8.8.8")

# DNS lookup
dns_result = bsn.get_device_dns_lookup("SERIAL123", "google.com")

# Traceroute
trace = bsn.get_device_traceroute("SERIAL123", "google.com")

# Get network configuration
network_config = bsn.get_device_network_config("SERIAL123", interface="eth0")

# Start packet capture
bsn.start_device_packet_capture("SERIAL123", duration=60)
```

### Video & Display Control

```python
# Get current video mode
mode = bsn.get_device_video_mode("SERIAL123")

# Set video mode to 1080p60
bsn.set_device_video_mode("SERIAL123", "1920x1080x60p")

# Get display brightness (Moka displays only)
brightness = bsn.get_display_brightness("SERIAL123")

# Set display brightness
bsn.set_display_brightness("SERIAL123", 75)

# Control display power
bsn.set_display_power_settings("SERIAL123", "standby")

# Set volume
bsn.set_display_volume("SERIAL123", 50)
```

### Registry Operations

```python
# Get entire registry
registry = bsn.get_device_registry("SERIAL123")

# Get specific registry key
value = bsn.get_device_registry_key("SERIAL123", "networking", "dhcp")

# Set registry value
bsn.set_device_registry_key("SERIAL123", "networking", "dhcp", "yes")

# Delete registry key
bsn.delete_device_registry_key("SERIAL123", "customsection", "customkey")

# Flush registry to disk
bsn.flush_device_registry("SERIAL123")
```

### Screenshots & Custom Commands

```python
# Take a screenshot
snapshot = bsn.take_device_snapshot("SERIAL123")
thumbnail = snapshot['data']['result']['remoteSnapshotThumbnail']

# Send custom UDP command
bsn.send_device_custom_command("SERIAL123", "next", return_immediately=True)

# Download firmware
bsn.download_device_firmware(
    "SERIAL123",
    "https://example.com/firmware.bsfw"
)
```

## API Documentation

For complete API documentation, see the [BSN Cloud API Documentation](https://docs.brightsign.biz/developers/cloud-apis).

### Available Functions by Category

#### Authentication
- `configure()` - Set credentials programmatically
- `login()` - Manual login (automatic when needed)

Most API failures are returned as dictionaries containing an `error` key. Network-level errors may still raise exceptions from the underlying HTTP library.
The API session is lazily initialized. No authentication or network requests occur until the first API call is made.

#### Device Management
- `get_devices()` - List all devices
- `get_setups()` - List setups/presentations

#### Control Endpoints
- `reboot_device()` - Reboot or factory reset
- `get_device_password()` - Get DWS password status
- `put_device_password()` - Set DWS password
- `get_device_local_dws_status()` - Check local DWS status
- `set_device_local_dws()` - Enable/disable local DWS
- `reset_device_ssh_host_keys()` - Reset SSH keys
- `reset_device_dws_default_certs()` - Reset DWS certificates

#### Storage/File Endpoints
- `get_device_files()` - List files
- `put_device_files()` - Upload files
- `create_device_directory()` - Create directories
- `rename_device_file()` - Rename files
- `delete_device_file()` - Delete files

#### Diagnostic Endpoints
- `get_device_diagnostics()` - Full network diagnostics
- `get_device_dns_lookup()` - DNS resolution test
- `get_device_ping()` - Ping test
- `get_device_traceroute()` - Traceroute
- `get_device_network_config()` - Network configuration
- `put_device_network_config()` - Update network settings
- `get_device_network_neighborhood()` - Discover nearby players
- `get_device_packet_capture_status()` - Packet capture status
- `start_device_packet_capture()` - Start packet capture
- `stop_device_packet_capture()` - Stop packet capture
- `get_device_telnet_status()` - Telnet configuration
- `put_device_telnet_config()` - Configure telnet
- `get_device_ssh_status()` - SSH configuration
- `put_device_ssh_config()` - Configure SSH

#### Other Endpoints
- `reformat_device_storage()` - Format storage device
- `reprovision_device()` - Re-provision player
- `take_device_snapshot()` - Take screenshot
- `send_device_custom_command()` - Send custom UDP command
- `download_device_firmware()` - Update firmware

#### Video Endpoints
- `get_device_video_mode()` - Convenience method that returns the currently active video mode
- `get_device_video_output()` - Get output information
- `get_device_video_edid()` - Get EDID data
- `get_device_video_power_save()` - Power save status
- `set_device_video_power_save()` - Enable/disable power save
- `get_device_video_modes()` - List available modes 
- `get_device_video_current_mode()` - Exposes the full BSN API and allows querying best, active, configured, or current modes.
- `set_device_video_mode()` - Change video mode

#### Registry Endpoints
- `get_device_registry()` - Get full registry
- `get_device_registry_key()` - Get specific key
- `set_device_registry_key()` - Set registry value
- `delete_device_registry_key()` - Delete registry key
- `flush_device_registry()` - Flush to disk
- `get_device_recovery_url()` - Get recovery URL
- `set_device_recovery_url()` - Set recovery URL

#### Advanced Endpoints
- `get_device_property_lock()` - Property lock status
- `set_device_property_lock()` - Configure property lock

#### Display Control Endpoints (Moka displays only)
- `get_display_control_all()` - All display settings
- `get_display_brightness()` / `set_display_brightness()` - Brightness
- `get_display_contrast()` / `set_display_contrast()` - Contrast
- `get_display_volume()` / `set_display_volume()` - Volume
- `get_display_power_settings()` / `set_display_power_settings()` - Power
- `get_display_white_balance()` / `set_display_white_balance()` - Color
- `get_display_video_output()` / `set_display_video_output()` - Output
- `get_display_always_connected()` / `set_display_always_connected()` - Connection
- `get_display_always_on()` / `set_display_always_on()` - Always on
- `update_display_firmware()` - Firmware update
- `get_display_info()` - Display information
- And more...

## Error Handling

The library returns error dictionaries when requests fail:

```python
result = bsn.get_device_files("INVALID_SERIAL", storage_type="sd")

if "error" in result:
    print(f"Error {result['error']}: {result['details']}")
else:
    # Success - process result
    files = result['data']['result']
```

## Requirements

- Python 3.10+
- `requests` - HTTP library
- `python-dotenv` - Environment variable management

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: https://github.com/TobiaszGans/py_BSN_Cloud_API/issues
- BSN Cloud API Documentation: https://docs.brightsign.biz/developers/cloud-apis
- BrightSign Support: https://support.brightsign.biz

## Design Philosophy

- Simple functional API (no client objects required)
- Single global authenticated session per process
- Thin wrapper around BSN Cloud API responses
- Minimal abstraction: responses closely match API output

## Not Yet Supported

- Multi-network concurrent sessions
- Async / asyncio interface
- Automatic retry on rate limits


## Changelog

### Version 1.0.0 (Initial Release)
- Complete implementation of BSN Cloud API endpoints
- Automatic authentication and token renewal
- Support for all device control operations
- File management capabilities
- Network diagnostics tools
- Video and display control
- Registry management
- Display control for Moka displays

## Author

Tobiasz Gans

## Acknowledgments

- BrightSign for providing the BSN Cloud API