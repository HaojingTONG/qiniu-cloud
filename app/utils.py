"""
Utility functions for AppleScript execution and logging.
"""
import logging
import subprocess
from typing import Tuple
from pathlib import Path

from .config import config


# Setup logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_osascript(script_path: Path, *args) -> Tuple[bool, str, str]:
    """
    Execute AppleScript file with arguments.

    Args:
        script_path: Path to .applescript file
        *args: Arguments to pass to the script

    Returns:
        (success, stdout, stderr)
    """
    try:
        cmd = ["osascript", str(script_path)] + [str(arg) for arg in args]
        logger.debug(f"Running: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        success = result.returncode == 0
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if success:
            logger.info(f"AppleScript executed successfully: {stdout}")
        else:
            logger.error(f"AppleScript failed: {stderr}")

        return success, stdout, stderr

    except subprocess.TimeoutExpired:
        logger.error("AppleScript execution timed out")
        return False, "", "Timeout after 30 seconds"
    except Exception as e:
        logger.error(f"AppleScript execution error: {e}")
        return False, "", str(e)


def run_shell_command(cmd: str) -> Tuple[bool, str, str]:
    """
    Execute shell command.

    Args:
        cmd: Shell command string

    Returns:
        (success, stdout, stderr)
    """
    try:
        logger.debug(f"Running shell: {cmd}")

        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )

        success = result.returncode == 0
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        return success, stdout, stderr

    except Exception as e:
        logger.error(f"Shell command error: {e}")
        return False, "", str(e)
