"""Android Tools Module"""

from .adb_client import ADBClient
from .device_manager import (
    DeviceManager,
    list_android_devices,
    get_device_info,
    get_device_battery_info,
    reboot_device,
    get_device_screen_info,
)
from .app_control import (
    AppController,
    list_installed_packages,
    get_app_info,
    install_apk,
    uninstall_app,
    start_app,
    stop_app,
    clear_app_data,
)
from .file_ops import (
    FileManager,
    list_files,
    pull_file,
    push_file,
    delete_file,
    create_directory,
    file_exists,
    read_file,
    write_file,
    file_stats,
    list_app_databases,
    pull_app_database,
)

__all__ = [
    # ADB Client
    'ADBClient',
    # Device Manager
    'DeviceManager',
    'list_android_devices',
    'get_device_info',
    'get_device_battery_info',
    'reboot_device',
    'get_device_screen_info',
    # App Control
    'AppController',
    'list_installed_packages',
    'get_app_info',
    'install_apk',
    'uninstall_app',
    'start_app',
    'stop_app',
    'clear_app_data',
    # File Operations
    'FileManager',
    'list_files',
    'pull_file',
    'push_file',
    'delete_file',
    'create_directory',
    'file_exists',
    'read_file',
    'write_file',
    'file_stats',
    'list_app_databases',
    'pull_app_database',
]
