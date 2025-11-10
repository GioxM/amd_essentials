### Guide: Collecting Device Label and Hardware ID with Python

This guide explains how to use the `device_id_collector.py` Python script, which prompts the user to enter a label for a connected device, retrieves the system's hardware ID (motherboard serial number), and saves both to a text file. The script is designed with senior-level code quality, including cross-platform compatibility, error handling, and detailed comments for maintainability.

#### Purpose
The script collects a user-provided device label (e.g., a model number or custom name on the device) and pairs it with the system's hardware ID. The hardware ID is typically the motherboard serial number, retrieved using platform-specific commands:
- **Windows**: Uses `wmic bios get serialnumber`.
- **macOS**: Uses `ioreg` to fetch the platform serial number.
- **Linux**: Uses `dmidecode` to get the baseboard serial number (may require `sudo`).

The output is saved to `device_info.txt` in the current working directory.

#### Prerequisites
- **Python 3**: Ensure Python 3.6+ is installed (`python --version` to check).
- **Linux Permissions**: On Linux, `dmidecode` may require root privileges. Run the script with `sudo` if needed.
- **Dependencies**: No external Python libraries are required; the script uses standard libraries (`os`, `sys`).

#### How to Run the Script
1. **Save the Script**:
   - Copy the code into a file named `device_id_collector.py`.
2. **Navigate to the Directory**:
   - Open a terminal or command prompt and navigate to the directory containing `device_id_collector.py` (e.g., `cd /path/to/script`).
3. **Run the Script**:
   - On **Windows/macOS**: `python device_id_collector.py`
   - On **Linux**: `python device_id_collector.py` or `sudo python device_id_collector.py` if permission errors occur.
4. **Enter the Device Label**:
   - When prompted, type the label visible on the device (e.g., "Model XYZ123") and press Enter.
5. **Check the Output**:
   - The script creates or overwrites `device_info.txt` in the same directory, containing the label and hardware ID.
   - Example content of `device_info.txt`:
     ```
     Label: Model XYZ123
     Hardware ID: ABC123456789
     ```
6. **Handle Errors**:
   - If the hardware ID cannot be retrieved (e.g., due to permissions or unsupported OS), the script will display an error and exit.
   - On Linux, if you see a permissions error, rerun with `sudo`.

#### Troubleshooting
- **Permission Denied (Linux)**: Run with `sudo` or ensure the user has access to `dmidecode`.
- **No Hardware ID**: If the hardware ID is empty, verify the system commands (`wmic`, `ioreg`, or `dmidecode`) are available and functional.
- **File Not Created**: Ensure you have write permissions in the current directory.
- **Unsupported OS**: The script supports Windows, macOS, and Linux. Other OSes will result in an error.

#### Security Notes
- On Linux, running with `sudo` may be required, but use caution as it grants elevated privileges.
- The script writes to a file in the current directory; ensure the directory is secure to avoid unauthorized access to `device_info.txt`.

#### Extending the Script
- **Multiple Devices**: Modify the script to append to `device_info.txt` instead of overwriting by changing the file mode from `"w"` to `"a"`.
- **Additional Metadata**: Add fields like timestamp or user ID by extending the input prompts and file output.
- **Alternative IDs**: Replace the motherboard serial with other identifiers (e.g., CPU ID or MAC address) by modifying the `get_hardware_id` function.