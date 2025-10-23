"""
Executor routes intents to macOS-specific implementations.
Handles dry-run mode and error recovery.
"""
import logging
from pathlib import Path
from typing import Optional

from .schema import Intent, ExecutionResult
from .config import config
from .utils import run_osascript, run_shell_command, logger


class MacOSExecutor:
    """Execute intents on macOS using AppleScript and shell commands."""

    def __init__(self, dry_run: bool = False):
        """
        Initialize executor.

        Args:
            dry_run: If True, only print what would be executed
        """
        self.dry_run = dry_run
        self.scripts_dir = config.EXECUTOR_DIR / "macos"
        logger.info(f"Executor initialized (dry_run={dry_run})")

    def execute(self, intent: Intent) -> ExecutionResult:
        """
        Execute intent.

        Args:
            intent: Intent to execute

        Returns:
            ExecutionResult
        """
        logger.info(f"Executing intent: {intent.intent}")

        try:
            if intent.intent == "system_setting":
                return self._execute_system_setting(intent)
            elif intent.intent == "web_search":
                return self._execute_web_search(intent)
            elif intent.intent == "write_note":
                return self._execute_write_note(intent)
            elif intent.intent == "control_app":
                return self._execute_control_app(intent)
            elif intent.intent == "play_music":
                return self._execute_play_music(intent)
            elif intent.intent == "clarify":
                return ExecutionResult(
                    success=True,
                    message="Clarification needed",
                    output=intent.speak_back
                )
            else:
                return ExecutionResult(
                    success=False,
                    message=f"Unknown intent: {intent.intent}",
                    error="Intent not implemented"
                )

        except Exception as e:
            logger.error(f"Execution error: {e}")
            return ExecutionResult(
                success=False,
                message="Execution failed",
                error=str(e)
            )

    def _execute_system_setting(self, intent: Intent) -> ExecutionResult:
        """Execute system setting changes."""
        slots = intent.slots
        setting = slots.get("setting")

        if setting == "volume":
            value = slots.get("value", 50)
            if self.dry_run:
                msg = f"[DRY RUN] Set volume to {value}%"
                logger.info(msg)
                return ExecutionResult(success=True, message=msg, output=msg)

            script_path = self.scripts_dir / "system.applescript"
            success, stdout, stderr = run_osascript(script_path, value)

            if success:
                return ExecutionResult(
                    success=True,
                    message=f"Volume set to {value}%",
                    output=stdout
                )
            else:
                return ExecutionResult(
                    success=False,
                    message="Failed to set volume",
                    error=stderr
                )

        return ExecutionResult(
            success=False,
            message=f"Unknown setting: {setting}",
            error="Setting not implemented"
        )

    def _execute_web_search(self, intent: Intent) -> ExecutionResult:
        """Execute web search."""
        slots = intent.slots
        query = slots.get("query", "")

        if not query:
            return ExecutionResult(
                success=False,
                message="No query provided",
                error="Missing query parameter"
            )

        # Use Google search
        search_url = f"https://www.google.com/search?q={query}"

        if self.dry_run:
            msg = f"[DRY RUN] Open URL: {search_url}"
            logger.info(msg)
            return ExecutionResult(success=True, message=msg, output=msg)

        script_path = self.scripts_dir / "safari.applescript"
        success, stdout, stderr = run_osascript(script_path, search_url)

        if success:
            return ExecutionResult(
                success=True,
                message=f"Opened search for: {query}",
                output=stdout
            )
        else:
            return ExecutionResult(
                success=False,
                message="Failed to open browser",
                error=stderr
            )

    def _execute_write_note(self, intent: Intent) -> ExecutionResult:
        """Execute note creation."""
        slots = intent.slots
        title = slots.get("title", "Quick Note")
        body = slots.get("body", "")

        if self.dry_run:
            msg = f"[DRY RUN] Create note: title='{title}', body='{body}'"
            logger.info(msg)
            return ExecutionResult(success=True, message=msg, output=msg)

        script_path = self.scripts_dir / "notes.applescript"
        success, stdout, stderr = run_osascript(script_path, title, body)

        if success:
            return ExecutionResult(
                success=True,
                message=f"Note created: {title}",
                output=stdout
            )
        else:
            return ExecutionResult(
                success=False,
                message="Failed to create note",
                error=stderr
            )

    def _execute_control_app(self, intent: Intent) -> ExecutionResult:
        """Execute app control."""
        slots = intent.slots
        app = slots.get("app", "")
        action = slots.get("action", "open")

        if not app:
            return ExecutionResult(
                success=False,
                message="No app specified",
                error="Missing app parameter"
            )

        if action == "open" or action == "open_url":
            # If URL is provided, use Safari script
            url = slots.get("url", "")
            if url:
                if self.dry_run:
                    msg = f"[DRY RUN] Open URL in {app}: {url}"
                    logger.info(msg)
                    return ExecutionResult(success=True, message=msg, output=msg)

                script_path = self.scripts_dir / "safari.applescript"
                success, stdout, stderr = run_osascript(script_path, url)
            else:
                # Just open the app
                if self.dry_run:
                    msg = f"[DRY RUN] Open app: {app}"
                    logger.info(msg)
                    return ExecutionResult(success=True, message=msg, output=msg)

                success, stdout, stderr = run_shell_command(f"open -a '{app}'")

            if success:
                return ExecutionResult(
                    success=True,
                    message=f"Opened {app}",
                    output=stdout
                )
            else:
                return ExecutionResult(
                    success=False,
                    message=f"Failed to open {app}",
                    error=stderr
                )

        return ExecutionResult(
            success=False,
            message=f"Unknown action: {action}",
            error="Action not implemented"
        )

    def _execute_play_music(self, intent: Intent) -> ExecutionResult:
        """Execute music playback control."""
        slots = intent.slots
        action = slots.get("action", "play")

        if self.dry_run:
            msg = f"[DRY RUN] Music action: {action}"
            logger.info(msg)
            return ExecutionResult(success=True, message=msg, output=msg)

        # Use osascript to control Music app
        if action == "play":
            cmd = 'osascript -e \'tell application "Music" to play\''
        elif action == "pause":
            cmd = 'osascript -e \'tell application "Music" to pause\''
        elif action == "next":
            cmd = 'osascript -e \'tell application "Music" to next track\''
        elif action == "previous":
            cmd = 'osascript -e \'tell application "Music" to previous track\''
        else:
            return ExecutionResult(
                success=False,
                message=f"Unknown music action: {action}",
                error="Action not supported"
            )

        success, stdout, stderr = run_shell_command(cmd)

        if success:
            return ExecutionResult(
                success=True,
                message=f"Music {action} executed",
                output=stdout
            )
        else:
            return ExecutionResult(
                success=False,
                message=f"Failed to {action} music",
                error=stderr
            )


def create_executor(dry_run: bool = False) -> MacOSExecutor:
    """Factory function to create executor."""
    return MacOSExecutor(dry_run=dry_run)
