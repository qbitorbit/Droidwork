# """
# Android Tools Module
# Provides LangChain tools for Android device control via ADB.
# """

# from .adb_client import ADBClient
# from .device_manager import (
#     DeviceManager,
#     list_android_devices,
#     get_device_info,
#     get_device_battery_info,
#     reboot_device,
#     get_device_screen_info,
# )

# __all__ = [
#     # Base client
#     'ADBClient',
    
#     # Device manager
#     'DeviceManager',
    
#     # Device management tools
#     'list_android_devices',
#     'get_device_info',
#     'get_device_battery_info',
#     'reboot_device',
#     'get_device_screen_info',
# ]

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
    # install_apk,  # Not implemented yet
    # uninstall_app,  # Not implemented yet
    # start_app,  # Not implemented yet
    # stop_app,  # Not implemented yet
    # clear_app_data,  # Not implemented yet
)

__all__ = [
    'ADBClient',
    'DeviceManager',
    'list_android_devices',
    'get_device_info',
    'get_device_battery_info',
    'reboot_device',
    'get_device_screen_info',
    'AppController',
    'list_installed_packages',
    'get_app_info',
    # Uncomment as we implement them:
    # 'install_apk',
    # 'uninstall_app',
    # 'start_app',
    # 'stop_app',
    # 'clear_app_data',
]
