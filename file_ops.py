"""
File Operations - Android File Management Tools
Provides LangChain tools for managing files on Android devices.
Includes specialized tools for extracting app databases.
"""
from typing import Optional
from langchain_core.tools import tool
from .adb_client import ADBClient
import json
import os
import re


class FileManager:
    """Manager for Android file operations via ADB."""
    
    def __init__(self):
        self.adb = ADBClient()


# Initialize global file manager
_file_manager = FileManager()


def _get_device_serial(device_serial: Optional[str] = None) -> tuple[str, Optional[str]]:
    """Get device serial, return (serial, error_json) - error_json is None if success."""
    if not device_serial:
        devices = _file_manager.adb.get_devices()
        if not devices:
            return "", json.dumps({"success": False, "error": "No devices connected"})
        device_serial = devices[0].get('serial') if isinstance(devices[0], dict) else devices[0]
    return device_serial, None


def _format_size(size_bytes: int) -> str:
    """Format file size into human readable format."""
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


def _parse_ls_line(line: str) -> Optional[dict]:
    """Parse a single ls -la output line into file info dict."""
    if line.startswith('total') or not line.strip():
        return None
    
    # Match: permissions links owner group size date name
    match = re.match(
        r'^([drwxlst-]+)\s+(\d+)\s+(\w+)\s+(\w+)\s+(\d+)\s+(\w+\s+\d+\s+[\d:]+)\s+(.+)$',
        line
    )
    if match:
        perms, links, owner, group, size, date, name = match.groups()
        return {
            "name": name,
            "permissions": perms,
            "owner": owner,
            "group": group,
            "size": int(size),
            "size_formatted": _format_size(int(size)),
            "date": date,
            "is_directory": perms.startswith('d'),
            "is_link": perms.startswith('l')
        }
    
    # Fallback: simple parsing
    parts = line.split()
    if len(parts) >= 8:
        try:
            size = int(parts[4])
        except ValueError:
            size = 0
        return {
            "name": " ".join(parts[7:]),
            "permissions": parts[0],
            "size": size,
            "size_formatted": _format_size(size),
            "is_directory": parts[0].startswith('d')
        }
    return None


# =============================================================================
# BASIC FILE OPERATIONS
# =============================================================================

@tool
def list_files(path: str, device_serial: Optional[str] = None) -> str:
    """List files and directories at a path on Android device.
    
    Args:
        path: Directory path on Android device (e.g., '/sdcard/Download')
        device_serial: Device serial number (optional, uses first device if not specified)
    
    Returns:
        JSON string with detailed file listing including permissions, size, dates
    """
    device_serial, error = _get_device_serial(device_serial)
    if error:
        return error
    
    output = _file_manager.adb.shell(f"ls -la '{path}'", device_serial)
    
    if not output or "No such file" in output or "Permission denied" in output:
        return json.dumps({
            "success": False,
            "error": output or f"Cannot access {path}",
            "device": device_serial
        })
    
    files = []
    directories = []
    
    for line in output.strip().split('\n'):
        info = _parse_ls_line(line)
        if info and info["name"] not in ['.', '..']:
            if info.get("is_directory"):
                directories.append(info)
            else:
                files.append(info)
    
    return json.dumps({
        "success": True,
        "path": path,
        "directories": directories,
        "files": files,
        "total_directories": len(directories),
        "total_files": len(files),
        "device": device_serial
    })


@tool
def pull_file(remote_path: str, local_path: str, device_serial: Optional[str] = None) -> str:
    """Pull/download a file from Android device to local machine.
    
    Args:
        remote_path: Path on the Android device (e.g., '/sdcard/file.txt')
        local_path: Destination path on local machine (e.g., '~/Downloads/file.txt')
        device_serial: Device serial number (optional, uses first device if not specified)
    
    Returns:
        JSON string with pull result including file size
    """
    device_serial, error = _get_device_serial(device_serial)
    if error:
        return error
    
    local_path = os.path.expanduser(local_path)
    
    # Create local directory if needed
    local_dir = os.path.dirname(local_path)
    if local_dir and not os.path.exists(local_dir):
        os.makedirs(local_dir)
    
    adb = ADBClient(device_serial)
    success, stdout, stderr = adb._run_adb(["pull", remote_path, local_path], timeout=300)
    
    if success and os.path.exists(local_path):
        file_size = os.path.getsize(local_path)
        return json.dumps({
            "success": True,
            "message": f"Successfully pulled file",
            "remote_path": remote_path,
            "local_path": local_path,
            "size_bytes": file_size,
            "size_formatted": _format_size(file_size),
            "device": device_serial
        })
    else:
        return json.dumps({
            "success": False,
            "error": stderr or stdout or "Failed to pull file",
            "device": device_serial
        })


@tool
def push_file(local_path: str, remote_path: str, device_serial: Optional[str] = None) -> str:
    """Push/upload a file from local machine to Android device.
    
    Args:
        local_path: Path on local machine (e.g., '~/Downloads/file.txt')
        remote_path: Destination path on Android device (e.g., '/sdcard/file.txt')
        device_serial: Device serial number (optional, uses first device if not specified)
    
    Returns:
        JSON string with push result
    """
    local_path = os.path.expanduser(local_path)
    
    if not os.path.exists(local_path):
        return json.dumps({
            "success": False,
            "error": f"Local file not found: {local_path}"
        })
    
    device_serial, error = _get_device_serial(device_serial)
    if error:
        return error
    
    file_size = os.path.getsize(local_path)
    
    adb = ADBClient(device_serial)
    success, stdout, stderr = adb._run_adb(["push", local_path, remote_path], timeout=300)
    
    if success:
        return json.dumps({
            "success": True,
            "message": f"Successfully pushed file",
            "local_path": local_path,
            "remote_path": remote_path,
            "size_bytes": file_size,
            "size_formatted": _format_size(file_size),
            "device": device_serial
        })
    else:
        return json.dumps({
            "success": False,
            "error": stderr or stdout or "Failed to push file",
            "device": device_serial
        })


@tool
def delete_file(path: str, device_serial: Optional[str] = None) -> str:
    """Delete a file or directory from Android device.
    
    Args:
        path: Path to delete on Android device
        device_serial: Device serial number (optional, uses first device if not specified)
    
    Returns:
        JSON string with deletion result
    """
    device_serial, error = _get_device_serial(device_serial)
    if error:
        return error
    
    # Check if path exists
    check = _file_manager.adb.shell(f"[ -e '{path}' ] && echo 'exists' || echo 'notfound'", device_serial)
    
    if "notfound" in check:
        return json.dumps({
            "success": False,
            "error": f"Path not found: {path}",
            "device": device_serial
        })
    
    # Check if directory
    is_dir = _file_manager.adb.shell(f"[ -d '{path}' ] && echo 'dir' || echo 'file'", device_serial)
    
    if "dir" in is_dir:
        output = _file_manager.adb.shell(f"rm -rf '{path}'", device_serial)
    else:
        output = _file_manager.adb.shell(f"rm '{path}'", device_serial)
    
    # Verify deletion
    check = _file_manager.adb.shell(f"[ -e '{path}' ] && echo 'exists' || echo 'deleted'", device_serial)
    
    if "deleted" in check:
        return json.dumps({
            "success": True,
            "message": f"Successfully deleted {path}",
            "device": device_serial
        })
    else:
        return json.dumps({
            "success": False,
            "error": output or "Failed to delete",
            "device": device_serial
        })


@tool
def create_directory(path: str, device_serial: Optional[str] = None) -> str:
    """Create a directory on Android device.
    
    Args:
        path: Directory path to create on Android device
        device_serial: Device serial number (optional, uses first device if not specified)
    
    Returns:
        JSON string with creation result
    """
    device_serial, error = _get_device_serial(device_serial)
    if error:
        return error
    
    output = _file_manager.adb.shell(f"mkdir -p '{path}'", device_serial)
    
    # Verify creation
    check = _file_manager.adb.shell(f"[ -d '{path}' ] && echo 'created' || echo 'failed'", device_serial)
    
    if "created" in check:
        return json.dumps({
            "success": True,
            "message": f"Successfully created directory {path}",
            "path": path,
            "device": device_serial
        })
    else:
        return json.dumps({
            "success": False,
            "error": output or "Failed to create directory",
            "device": device_serial
        })


@tool
def file_exists(path: str, device_serial: Optional[str] = None) -> str:
    """Check if a file or directory exists on Android device.
    
    Args:
        path: Path to check on Android device
        device_serial: Device serial number (optional, uses first device if not specified)
    
    Returns:
        JSON string with existence check result
    """
    device_serial, error = _get_device_serial(device_serial)
    if error:
        return error
    
    check = _file_manager.adb.shell(f"[ -e '{path}' ] && echo 'exists' || echo 'notfound'", device_serial)
    exists = "exists" in check
    
    file_type = None
    if exists:
        type_check = _file_manager.adb.shell(f"[ -d '{path}' ] && echo 'directory' || echo 'file'", device_serial)
        file_type = "directory" if "directory" in type_check else "file"
    
    return json.dumps({
        "success": True,
        "exists": exists,
        "path": path,
        "type": file_type,
        "device": device_serial
    })


@tool
def read_file(path: str, max_size: int = 100000, device_serial: Optional[str] = None) -> str:
    """Read contents of a text file from Android device.
    
    Args:
        path: File path on Android device
        max_size: Maximum file size in bytes to read (default: 100KB)
        device_serial: Device serial number (optional, uses first device if not specified)
    
    Returns:
        JSON string with file contents
    """
    device_serial, error = _get_device_serial(device_serial)
    if error:
        return error
    
    # Check if file exists
    check = _file_manager.adb.shell(f"[ -f '{path}' ] && echo 'exists' || echo 'notfound'", device_serial)
    
    if "notfound" in check:
        return json.dumps({
            "success": False,
            "error": f"File not found: {path}",
            "device": device_serial
        })
    
    # Check file size
    size_output = _file_manager.adb.shell(f"wc -c < '{path}'", device_serial)
    try:
        file_size = int(size_output.strip())
    except ValueError:
        file_size = 0
    
    if file_size > max_size:
        return json.dumps({
            "success": False,
            "error": f"File too large ({_format_size(file_size)}). Max: {_format_size(max_size)}. Use pull_file instead.",
            "size_bytes": file_size,
            "device": device_serial
        })
    
    # Read file content
    content = _file_manager.adb.shell(f"cat '{path}'", device_serial)
    
    return json.dumps({
        "success": True,
        "path": path,
        "content": content,
        "size_bytes": file_size,
        "size_formatted": _format_size(file_size),
        "device": device_serial
    })


@tool
def write_file(path: str, content: str, device_serial: Optional[str] = None) -> str:
    """Write text content to a file on Android device.
    
    Args:
        path: File path on Android device
        content: Text content to write
        device_serial: Device serial number (optional, uses first device if not specified)
    
    Returns:
        JSON string with write result
    """
    device_serial, error = _get_device_serial(device_serial)
    if error:
        return error
    
    # Create parent directory if needed
    parent_dir = os.path.dirname(path)
    if parent_dir:
        _file_manager.adb.shell(f"mkdir -p '{parent_dir}'", device_serial)
    
    # Escape content for echo
    escaped_content = content.replace("'", "'\\''")
    
    # Write content
    _file_manager.adb.shell(f"echo '{escaped_content}' > '{path}'", device_serial)
    
    # Verify write
    check = _file_manager.adb.shell(f"[ -f '{path}' ] && echo 'written' || echo 'failed'", device_serial)
    
    if "written" in check:
        size_output = _file_manager.adb.shell(f"wc -c < '{path}'", device_serial)
        try:
            file_size = int(size_output.strip())
        except ValueError:
            file_size = len(content.encode('utf-8'))
        
        return json.dumps({
            "success": True,
            "message": f"Successfully wrote to {path}",
            "path": path,
            "size_bytes": file_size,
            "size_formatted": _format_size(file_size),
            "device": device_serial
        })
    else:
        return json.dumps({
            "success": False,
            "error": "Failed to write file",
            "device": device_serial
        })


@tool
def file_stats(path: str, device_serial: Optional[str] = None) -> str:
    """Get detailed statistics for a file or directory on Android device.
    
    Args:
        path: Path on Android device
        device_serial: Device serial number (optional, uses first device if not specified)
    
    Returns:
        JSON string with detailed file/directory statistics
    """
    device_serial, error = _get_device_serial(device_serial)
    if error:
        return error
    
    # Check if exists
    check = _file_manager.adb.shell(f"[ -e '{path}' ] && echo 'exists' || echo 'notfound'", device_serial)
    
    if "notfound" in check:
        return json.dumps({
            "success": False,
            "error": f"Path not found: {path}",
            "device": device_serial
        })
    
    # Get type
    type_check = _file_manager.adb.shell(f"[ -d '{path}' ] && echo 'directory' || echo 'file'", device_serial)
    is_directory = "directory" in type_check
    
    # Get ls info
    ls_output = _file_manager.adb.shell(f"ls -la '{path}'", device_serial)
    
    stats = {
        "success": True,
        "path": path,
        "type": "directory" if is_directory else "file",
        "device": device_serial
    }
    
    # Parse first relevant line
    for line in ls_output.strip().split('\n'):
        info = _parse_ls_line(line)
        if info:
            stats.update({
                "permissions": info.get("permissions"),
                "owner": info.get("owner"),
                "group": info.get("group"),
                "size_bytes": info.get("size"),
                "size_formatted": info.get("size_formatted"),
                "modified": info.get("date")
            })
            break
    
    # For directories, get counts
    if is_directory:
        try:
            file_count = _file_manager.adb.shell(f"find '{path}' -type f 2>/dev/null | wc -l", device_serial)
            dir_count = _file_manager.adb.shell(f"find '{path}' -type d 2>/dev/null | wc -l", device_serial)
            stats["file_count"] = int(file_count.strip())
            stats["directory_count"] = max(0, int(dir_count.strip()) - 1)  # Exclude self
        except ValueError:
            pass
    
    return json.dumps(stats)


# =============================================================================
# APP DATABASE OPERATIONS
# =============================================================================

@tool
def list_app_databases(package_name: str, device_serial: Optional[str] = None) -> str:
    """List all database files for an Android app.
    
    Requires debuggable app or rooted device.
    
    Args:
        package_name: App package name (e.g., 'com.example.app')
        device_serial: Device serial number (optional, uses first device if not specified)
    
    Returns:
        JSON string with list of database files
    """
    device_serial, error = _get_device_serial(device_serial)
    if error:
        return error
    
    adb = ADBClient(device_serial)
    databases = []
    method_used = None
    
    # Method 1: Try run-as (works for debuggable apps)
    success, stdout, stderr = adb._run_adb([
        "shell", "run-as", package_name, "ls", "-la", "databases/"
    ], timeout=30)
    
    if success and stdout and "not debuggable" not in stderr.lower():
        method_used = "run-as"
        for line in stdout.strip().split('\n'):
            info = _parse_ls_line(line)
            if info and info["name"] not in ['.', '..']:
                databases.append(info)
    else:
        # Method 2: Try with su (requires root)
        db_path = f"/data/data/{package_name}/databases/"
        success, stdout, stderr = adb._run_adb([
            "shell", "su", "-c", f"ls -la {db_path}"
        ], timeout=30)
        
        if success and stdout and "Permission denied" not in stdout:
            method_used = "root"
            for line in stdout.strip().split('\n'):
                info = _parse_ls_line(line)
                if info and info["name"] not in ['.', '..']:
                    databases.append(info)
    
    if not databases:
        return json.dumps({
            "success": False,
            "error": "Cannot list databases. App may not be debuggable and device may not be rooted.",
            "package": package_name,
            "device": device_serial
        })
    
    # Filter to show only actual database files
    db_files = [db for db in databases if db["name"].endswith(('.db', '.sqlite', '.sqlite3')) 
                or '-journal' not in db["name"]]
    
    return json.dumps({
        "success": True,
        "package": package_name,
        "databases": db_files,
        "count": len(db_files),
        "access_method": method_used,
        "device": device_serial
    })


@tool
def pull_app_database(
    package_name: str, 
    db_name: str, 
    local_dir: str = "~/Downloads",
    device_serial: Optional[str] = None
) -> str:
    """Pull/extract an app's SQLite database to local machine.
    
    Requires debuggable app or rooted device.
    Copies the database from app's private storage to your Mac.
    
    Args:
        package_name: App package name (e.g., 'com.example.app')
        db_name: Database filename (e.g., 'app.db', 'data.sqlite')
        local_dir: Local directory to save to (default: ~/Downloads)
        device_serial: Device serial number (optional, uses first device if not specified)
    
    Returns:
        JSON string with pull result and local path
    """
    device_serial, error = _get_device_serial(device_serial)
    if error:
        return error
    
    local_dir = os.path.expanduser(local_dir)
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)
    
    # Paths
    db_remote_path = f"/data/data/{package_name}/databases/{db_name}"
    temp_path = f"/sdcard/temp_{package_name}_{db_name}"
    local_path = os.path.join(local_dir, f"{package_name}_{db_name}")
    
    adb = ADBClient(device_serial)
    method_used = None
    
    # Method 1: Try run-as (works for debuggable apps)
    success, stdout, stderr = adb._run_adb([
        "shell", "run-as", package_name, "cat", f"databases/{db_name}"
    ], timeout=60)
    
    if success and stdout and "not debuggable" not in stderr.lower():
        # Write directly using run-as + cat piped to sdcard
        success, stdout, stderr = adb._run_adb([
            "shell", f"run-as {package_name} cat databases/{db_name} > {temp_path}"
        ], timeout=60)
        method_used = "run-as"
    
    if not method_used:
        # Method 2: Try with su (requires root)
        success, stdout, stderr = adb._run_adb([
            "shell", "su", "-c", f"cp {db_remote_path} {temp_path}"
        ], timeout=60)
        
        if success:
            method_used = "root"
    
    if not method_used:
        # Method 3: Try run-as with cp
        success, stdout, stderr = adb._run_adb([
            "shell", "run-as", package_name, "cp", f"databases/{db_name}", temp_path
        ], timeout=60)
        
        if success:
            method_used = "run-as-cp"
    
    # Make temp file readable and pull
    adb._run_adb(["shell", "chmod", "644", temp_path], timeout=10)
    success, stdout, stderr = adb._run_adb(["pull", temp_path, local_path], timeout=120)
    
    # Cleanup temp file
    adb._run_adb(["shell", "rm", "-f", temp_path], timeout=10)
    
    if success and os.path.exists(local_path):
        file_size = os.path.getsize(local_path)
        
        # Also try to pull journal/wal files if they exist
        for suffix in ['-journal', '-wal', '-shm']:
            journal_temp = f"/sdcard/temp_{package_name}_{db_name}{suffix}"
            journal_local = f"{local_path}{suffix}"
            
            if method_used == "run-as":
                adb._run_adb([
                    "shell", f"run-as {package_name} cat databases/{db_name}{suffix} > {journal_temp} 2>/dev/null"
                ], timeout=30)
            elif method_used == "root":
                adb._run_adb([
                    "shell", "su", "-c", f"cp {db_remote_path}{suffix} {journal_temp} 2>/dev/null"
                ], timeout=30)
            
            adb._run_adb(["shell", "chmod", "644", journal_temp], timeout=5)
            adb._run_adb(["pull", journal_temp, journal_local], timeout=30)
            adb._run_adb(["shell", "rm", "-f", journal_temp], timeout=5)
        
        return json.dumps({
            "success": True,
            "message": f"Successfully pulled database",
            "package": package_name,
            "database": db_name,
            "local_path": local_path,
            "size_bytes": file_size,
            "size_formatted": _format_size(file_size),
            "access_method": method_used,
            "device": device_serial
        })
    else:
        return json.dumps({
            "success": False,
            "error": "Failed to pull database. App may not be debuggable and device may not be rooted.",
            "details": stderr or stdout,
            "package": package_name,
            "database": db_name,
            "device": device_serial
        })
