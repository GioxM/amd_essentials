# device_id_collector.py
# Description:
# This script collects a user-provided label for a connected device and retrieves its
# unique hardware ID (serial number for USB or serial devices on macOS). The data is appended
# to a text file named 'device_info.txt'. The script supports both USB devices (using system_profiler)
# and serial devices (using pyserial). It lists all available devices for user selection.
#
# Usage:
# 1. Install pyserial if using serial support: `pip install pyserial`
# 2. Run the script: `python device_id_collector.py`
# 3. Enter the device label and select the device when prompted.
# 4. Check 'device_info.txt' for the saved information.
# 5. If errors occur (e.g., no devices found), an error message is displayed.

import os
import sys
import subprocess
try:
    from serial.tools import list_ports
except ImportError:
    print("Warning: 'pyserial' library not found for serial device support. Install it with: pip install pyserial")
    list_ports = None  # Disable serial support if not installed

def get_usb_devices_macos():
    """
    Retrieves a list of USB devices and their serial numbers on macOS using system_profiler.
    
    Returns:
        list: List of dictionaries with device details (type, name, serial_number).
    """
    try:
        command = "system_profiler SPUSBDataType -detailLevel mini"
        output = subprocess.check_output(command, shell=True, text=True).strip()
        devices = []
        current_device = {}
        for line in output.splitlines():
            line = line.strip()
            if line and ":" in line:
                key, value = [part.strip() for part in line.split(":", 1)]
                if key == "Product":
                    current_device = {"type": "USB", "name": value}
                elif key == "Serial Number" and current_device:
                    current_device["serial_number"] = value
                    devices.append(current_device)
                    current_device = {}
        return devices
    except subprocess.CalledProcessError as e:
        print(f"DEBUG: system_profiler command failed: {e}")
        return []

def get_serial_devices_macos():
    """
    Retrieves a list of serial devices and their serial numbers on macOS using pyserial.
    
    Returns:
        list: List of dictionaries with device details (type, name, serial_number).
    """
    if list_ports is None:
        print("DEBUG: Serial device support disabled (pyserial not installed).")
        return []
    
    try:
        ports = list(list_ports.comports())
        devices = []
        for port in ports:
            serial_num = port.serial_number if port.serial_number else port.device  # Fall back to device path
            devices.append({
                "type": "Serial",
                "name": port.description,
                "serial_number": serial_num
            })
        return devices
    except Exception as e:
        print(f"DEBUG: pyserial failed: {e}")
        return []

def get_hardware_id():
    """
    Retrieves the hardware ID for a connected device. Lists both USB and serial devices
    on macOS and returns the selected device's serial number.
    
    Returns:
        str: The hardware ID (serial number) if found, otherwise an empty string.
    """
    os_type = sys.platform.lower()
    print(f"DEBUG: Detected platform: {os_type}")
    
    if os_type == "darwin":  # macOS
        usb_devices = get_usb_devices_macos()
        serial_devices = get_serial_devices_macos()
        all_devices = usb_devices + serial_devices
        
        if not all_devices:
            print("Error: No USB or serial devices found. Ensure the device is connected.")
            return ""
        
        # Display available devices
        print("Available devices:")
        for i, device in enumerate(all_devices, 1):
            serial = device.get("serial_number", "No serial number")
            print(f"{i}. [{device['type']}] {device['name']} (Serial: {serial})")
        
        # Prompt user to select a device
        try:
            choice = int(input(f"Enter the number of the device to use (1-{len(all_devices)}): "))
            if 1 <= choice <= len(all_devices):
                selected_device = all_devices[choice - 1]
                serial = selected_device.get("serial_number", "")
                if serial:
                    print(f"DEBUG: Selected hardware ID: {serial}")
                    return serial
                else:
                    print("Error: Selected device has no serial number.")
                    return ""
            else:
                print("Error: Invalid selection.")
                return ""
        except ValueError:
            print("Error: Please enter a valid number.")
            return ""
    
    elif os_type == "win32" or os_type == "cygwin":  # Windows
        print("Warning: Device enumeration not implemented for Windows.")
        return ""
    
    elif os_type == "linux":  # Linux
        print("Warning: Device enumeration not implemented for Linux.")
        return ""
    
    else:
        print(f"DEBUG: Unsupported platform: {os_type}")
        return ""

if __name__ == "__main__":
    # Prompt the user for the device label
    label = input("Enter the label that is on the device that is currently connected: ").strip()
    
    # Retrieve the hardware ID
    hardware_id = get_hardware_id()
    
    if not hardware_id:
        print("Error: Could not retrieve hardware ID for the selected device.")
        sys.exit(1)
    
    # Define the output text file
    filename = "device_info.txt"
    
    # Append the label and hardware ID to the file
    try:
        with open(filename, "a") as f:
            f.write(f"Label: {label}\n")
            f.write(f"Hardware ID: {hardware_id}\n")
            f.write("\n")  # Add blank line for readability
        print(f"Information successfully appended to {filename}")
    except PermissionError:
        print(f"Error: Could not write to {filename}. Ensure you have write permissions in the current directory.")
        sys.exit(1)