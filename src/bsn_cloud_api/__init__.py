"""
BSN Cloud API - Python library for BrightSign Network Cloud API

A comprehensive library for interacting with BrightSign players remotely
through the BSN Cloud API, including control, diagnostics, file management,
video settings, and more.

Example usage:
    import bsn_cloud_api as bsn
    
    # Configure credentials
    bsn.configure(
        client_id="your_client_id",
        secret="your_secret",
        network="your_network"
    )
    
    # Get all devices
    devices = bsn.get_devices()
    
    # Reboot a device
    bsn.reboot_device("SERIAL123")
"""

__version__ = "1.0.0"
__author__ = "Tobiasz Gans"
__email__ = "tobgan@icloud.com"
__license__ = "MIT"

# Import main API module
from .api import (
    # Configuration
    configure,
    login,
    
    # Device Management
    get_devices,
    get_setups,
    
    # DWS Password Control
    get_device_local_dws_status,
    set_device_local_dws,
    reset_device_ssh_host_keys,
    reset_device_dws_default_certs,
    get_device_password,
    put_device_password,
    
    # Storage/File Endpoints
    get_device_files,
    put_device_files,
    create_device_directory,
    rename_device_file,
    delete_device_file,
    
    # Diagnostic Endpoints
    get_device_diagnostics,
    get_device_dns_lookup,
    get_device_ping,
    get_device_traceroute,
    get_device_network_config,
    put_device_network_config,
    get_device_network_neighborhood,
    get_device_packet_capture_status,
    start_device_packet_capture,
    stop_device_packet_capture,
    get_device_telnet_status,
    put_device_telnet_config,
    get_device_ssh_status,
    put_device_ssh_config,
    
    # Other Endpoints
    reformat_device_storage,
    reprovision_device,
    take_device_snapshot,
    send_device_custom_command,
    download_device_firmware,
    
    # Video Endpoints
    get_device_video_mode,
    get_device_video_output,
    get_device_video_edid,
    get_device_video_power_save,
    set_device_video_power_save,
    get_device_video_modes,
    get_device_video_current_mode,
    set_device_video_mode,
    
    # Advanced Endpoints
    get_device_property_lock,
    set_device_property_lock,
    
    # Registry Endpoints
    get_device_registry,
    get_device_registry_key,
    set_device_registry_key,
    delete_device_registry_key,
    flush_device_registry,
    get_device_recovery_url,
    set_device_recovery_url,
    
    # Display Control Endpoints
    get_display_control_all,
    get_display_brightness,
    set_display_brightness,
    get_display_contrast,
    set_display_contrast,
    get_display_always_connected,
    set_display_always_connected,
    get_display_always_on,
    set_display_always_on,
    update_display_firmware,
    get_display_info,
    get_display_power_settings,
    set_display_power_settings,
    get_display_standby_timeout,
    set_display_standby_timeout,
    get_display_sd_connection,
    set_display_sd_connection,
    get_display_video_output,
    set_display_video_output,
    get_display_volume,
    set_display_volume,
    get_display_white_balance,
    set_display_white_balance,
)

__all__ = [
    # Configuration
    'configure',
    'login',
    
    # Device Management
    'get_devices',
    'get_setups',
    
    # Control Endpoints

    'get_device_local_dws_status',
    'set_device_local_dws',
    'reset_device_ssh_host_keys',
    'reset_device_dws_default_certs',
    'get_device_password',
    'put_device_password',
    
    # Storage/File Endpoints
    'get_device_files',
    'put_device_files',
    'create_device_directory',
    'rename_device_file',
    'delete_device_file',
    
    # Diagnostic Endpoints
    'get_device_diagnostics',
    'get_device_dns_lookup',
    'get_device_ping',
    'get_device_traceroute',
    'get_device_network_config',
    'put_device_network_config',
    'get_device_network_neighborhood',
    'get_device_packet_capture_status',
    'start_device_packet_capture',
    'stop_device_packet_capture',
    'get_device_telnet_status',
    'put_device_telnet_config',
    'get_device_ssh_status',
    'put_device_ssh_config',
    
    # Other Endpoints
    'reformat_device_storage',
    'reprovision_device',
    'take_device_snapshot',
    'send_device_custom_command',
    'download_device_firmware',
    
    # Video Endpoints
    'get_device_video_mode',
    'get_device_video_output',
    'get_device_video_edid',
    'get_device_video_power_save',
    'set_device_video_power_save',
    'get_device_video_modes',
    'get_device_video_current_mode',
    'set_device_video_mode',
    
    # Advanced Endpoints
    'get_device_property_lock',
    'set_device_property_lock',
    
    # Registry Endpoints
    'get_device_registry',
    'get_device_registry_key',
    'set_device_registry_key',
    'delete_device_registry_key',
    'flush_device_registry',
    'get_device_recovery_url',
    'set_device_recovery_url',
    
    # Display Control Endpoints
    'get_display_control_all',
    'get_display_brightness',
    'set_display_brightness',
    'get_display_contrast',
    'set_display_contrast',
    'get_display_always_connected',
    'set_display_always_connected',
    'get_display_always_on',
    'set_display_always_on',
    'update_display_firmware',
    'get_display_info',
    'get_display_power_settings',
    'set_display_power_settings',
    'get_display_standby_timeout',
    'set_display_standby_timeout',
    'get_display_sd_connection',
    'set_display_sd_connection',
    'get_display_video_output',
    'set_display_video_output',
    'get_display_volume',
    'set_display_volume',
    'get_display_white_balance',
    'set_display_white_balance',
]
