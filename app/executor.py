"""
Executor routes intents to macOS-specific implementations.
Handles dry-run mode and error recovery.
"""
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Optional

from .schema import Intent, ExecutionResult
from .config import config
from .utils import run_osascript, run_shell_command, logger
from .llm import get_llm_client


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

    def _is_safe_path(self, path: str) -> tuple[bool, str]:
        """
        检查文件路径是否安全（不在系统目录中）。
        (Check if file path is safe - not in system directories)

        Args:
            path: 文件路径 (File path)

        Returns:
            tuple[bool, str]: (是否安全, 错误信息) (is_safe, error_message)
        """
        # 展开用户路径 (Expand user path)
        expanded_path = os.path.expanduser(path)
        abs_path = os.path.abspath(expanded_path)

        # 系统保护目录列表 (System protected directories)
        protected_dirs = [
            "/System",
            "/Library",
            "/usr",
            "/bin",
            "/sbin",
            "/etc",
            "/var",
            "/private",
            "/Applications"  # 保护应用程序目录 (Protect Applications folder)
        ]

        # 检查路径是否在保护目录中 (Check if path is in protected directories)
        for protected in protected_dirs:
            if abs_path.startswith(protected):
                return False, f"Access to system directory denied: {protected}"

        return True, ""

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
            elif intent.intent == "write_article":
                return self._execute_write_article(intent)
            elif intent.intent == "file_read":
                return self._execute_file_read(intent)
            elif intent.intent == "file_write":
                return self._execute_file_write(intent)
            elif intent.intent == "file_move":
                return self._execute_file_move(intent)
            elif intent.intent == "file_copy":
                return self._execute_file_copy(intent)
            elif intent.intent == "file_delete":
                return self._execute_file_delete(intent)
            elif intent.intent == "file_list":
                return self._execute_file_list(intent)
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

    def _execute_write_article(self, intent: Intent) -> ExecutionResult:
        """
        执行文章写作：调用 LLM 生成文章并保存到本地文件。
        (Execute article writing: call LLM to generate article and save to local file)
        """
        slots = intent.slots
        topic = slots.get("topic", "")
        tone = slots.get("tone", "informative")
        length = slots.get("length", 1000)

        if not topic:
            return ExecutionResult(
                success=False,
                message="No topic provided",
                error="Missing topic parameter"
            )

        if self.dry_run:
            msg = f"[DRY RUN] Generate article on: {topic} ({length} chars, {tone} tone)"
            logger.info(msg)
            return ExecutionResult(success=True, message=msg, output=msg)

        try:
            # 调用 LLM 生成文章 (Call LLM to generate article)
            logger.info(f"Generating article on topic: {topic}")
            llm_client = get_llm_client()
            article_data = llm_client.generate_article(topic, tone, length)

            # 写入文件 (Write to file)
            file_path = self._write_article_file(
                article_data["title"],
                article_data["content"]
            )

            # 可选：打开文件 (Optional: open file)
            script_path = self.scripts_dir / "open_file.applescript"
            if script_path.exists():
                run_osascript(script_path, file_path)

            return ExecutionResult(
                success=True,
                message=f"Article created: {article_data['title']}",
                output=f"File saved to: {file_path}\nSummary: {article_data['summary']}",
                file_path=file_path
            )

        except Exception as e:
            logger.error(f"Article writing failed: {e}")
            return ExecutionResult(
                success=False,
                message="Failed to generate article",
                error=str(e)
            )

    def _write_article_file(self, title: str, content: str) -> str:
        """
        将文章写入本地 Markdown 文件。
        (Write article to local Markdown file)

        Args:
            title: 文章标题 (Article title)
            content: 文章内容 (Article content in Markdown)

        Returns:
            str: 文件路径 (File path)
        """
        # 创建保存目录 (Create save directory)
        folder = os.path.expanduser("~/Documents/VoiceOS_Articles")
        os.makedirs(folder, exist_ok=True)

        # 生成安全文件名 (Generate safe filename)
        # 保留中文字符，只替换特殊字符 (Keep Chinese chars, replace only special chars)
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
        safe_title = safe_title.strip()[:100]  # 限制长度 (Limit length)

        # 生成唯一文件名 (Generate unique filename)
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_title}_{timestamp}.md"
        file_path = os.path.join(folder, filename)

        # 写入文件 (Write file)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Article saved to: {file_path}")
        return file_path

    def _execute_file_read(self, intent: Intent) -> ExecutionResult:
        """
        执行文件读取。
        (Execute file read operation)
        """
        slots = intent.slots
        path = slots.get("path", "")

        if not path:
            return ExecutionResult(
                success=False,
                message="No file path provided",
                error="Missing path parameter"
            )

        # 安全检查 (Safety check)
        is_safe, error_msg = self._is_safe_path(path)
        if not is_safe:
            return ExecutionResult(
                success=False,
                message="File access denied",
                error=error_msg
            )

        # 展开路径 (Expand path)
        expanded_path = os.path.expanduser(path)

        if self.dry_run:
            msg = f"[DRY RUN] Read file: {expanded_path}"
            logger.info(msg)
            return ExecutionResult(success=True, message=msg, output=msg)

        try:
            # 检查文件是否存在 (Check if file exists)
            if not os.path.isfile(expanded_path):
                return ExecutionResult(
                    success=False,
                    message=f"File not found: {path}",
                    error="File does not exist"
                )

            # 读取文件 (Read file)
            with open(expanded_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 限制输出长度，避免 TTS 播报过长 (Limit output for TTS)
            preview = content[:500] + ("..." if len(content) > 500 else "")

            return ExecutionResult(
                success=True,
                message=f"Read file: {path}",
                output=f"Content ({len(content)} chars):\n{preview}"
            )

        except Exception as e:
            logger.error(f"File read failed: {e}")
            return ExecutionResult(
                success=False,
                message=f"Failed to read file: {path}",
                error=str(e)
            )

    def _execute_file_write(self, intent: Intent) -> ExecutionResult:
        """
        执行文件写入。
        (Execute file write operation)
        """
        slots = intent.slots
        path = slots.get("path", "")
        content = slots.get("content", "")

        if not path:
            return ExecutionResult(
                success=False,
                message="No file path provided",
                error="Missing path parameter"
            )

        # 安全检查 (Safety check)
        is_safe, error_msg = self._is_safe_path(path)
        if not is_safe:
            return ExecutionResult(
                success=False,
                message="File access denied",
                error=error_msg
            )

        # 展开路径 (Expand path)
        expanded_path = os.path.expanduser(path)

        if self.dry_run:
            msg = f"[DRY RUN] Write file: {expanded_path} ({len(content)} chars)"
            logger.info(msg)
            return ExecutionResult(success=True, message=msg, output=msg)

        try:
            # 确保目录存在 (Ensure directory exists)
            os.makedirs(os.path.dirname(expanded_path), exist_ok=True)

            # 写入文件 (Write file)
            with open(expanded_path, "w", encoding="utf-8") as f:
                f.write(content)

            return ExecutionResult(
                success=True,
                message=f"File written: {path}",
                output=f"Wrote {len(content)} characters to {path}",
                file_path=expanded_path
            )

        except Exception as e:
            logger.error(f"File write failed: {e}")
            return ExecutionResult(
                success=False,
                message=f"Failed to write file: {path}",
                error=str(e)
            )

    def _execute_file_move(self, intent: Intent) -> ExecutionResult:
        """
        执行文件移动。
        (Execute file move operation)
        """
        slots = intent.slots
        src = slots.get("src", "")
        dest = slots.get("dest", "")

        if not src or not dest:
            return ExecutionResult(
                success=False,
                message="Source or destination path missing",
                error="Missing src or dest parameter"
            )

        # 安全检查 (Safety check)
        is_safe_src, error_msg_src = self._is_safe_path(src)
        is_safe_dest, error_msg_dest = self._is_safe_path(dest)

        if not is_safe_src:
            return ExecutionResult(
                success=False,
                message="Source access denied",
                error=error_msg_src
            )

        if not is_safe_dest:
            return ExecutionResult(
                success=False,
                message="Destination access denied",
                error=error_msg_dest
            )

        # 展开路径 (Expand paths)
        expanded_src = os.path.expanduser(src)
        expanded_dest = os.path.expanduser(dest)

        if self.dry_run:
            msg = f"[DRY RUN] Move: {expanded_src} -> {expanded_dest}"
            logger.info(msg)
            return ExecutionResult(success=True, message=msg, output=msg)

        try:
            # 检查源文件是否存在 (Check if source exists)
            if not os.path.exists(expanded_src):
                return ExecutionResult(
                    success=False,
                    message=f"Source not found: {src}",
                    error="Source does not exist"
                )

            # 如果目标是目录，保留原文件名 (If dest is directory, keep filename)
            if os.path.isdir(expanded_dest):
                expanded_dest = os.path.join(
                    expanded_dest,
                    os.path.basename(expanded_src)
                )

            # 移动文件 (Move file)
            shutil.move(expanded_src, expanded_dest)

            return ExecutionResult(
                success=True,
                message=f"Moved: {src} -> {dest}",
                output=f"File moved from {src} to {expanded_dest}",
                file_path=expanded_dest
            )

        except Exception as e:
            logger.error(f"File move failed: {e}")
            return ExecutionResult(
                success=False,
                message=f"Failed to move file",
                error=str(e)
            )

    def _execute_file_copy(self, intent: Intent) -> ExecutionResult:
        """
        执行文件复制。
        (Execute file copy operation)
        """
        slots = intent.slots
        src = slots.get("src", "")
        dest = slots.get("dest", "")

        if not src or not dest:
            return ExecutionResult(
                success=False,
                message="Source or destination path missing",
                error="Missing src or dest parameter"
            )

        # 安全检查 (Safety check)
        is_safe_src, error_msg_src = self._is_safe_path(src)
        is_safe_dest, error_msg_dest = self._is_safe_path(dest)

        if not is_safe_src:
            return ExecutionResult(
                success=False,
                message="Source access denied",
                error=error_msg_src
            )

        if not is_safe_dest:
            return ExecutionResult(
                success=False,
                message="Destination access denied",
                error=error_msg_dest
            )

        # 展开路径 (Expand paths)
        expanded_src = os.path.expanduser(src)
        expanded_dest = os.path.expanduser(dest)

        if self.dry_run:
            msg = f"[DRY RUN] Copy: {expanded_src} -> {expanded_dest}"
            logger.info(msg)
            return ExecutionResult(success=True, message=msg, output=msg)

        try:
            # 检查源文件是否存在 (Check if source exists)
            if not os.path.exists(expanded_src):
                return ExecutionResult(
                    success=False,
                    message=f"Source not found: {src}",
                    error="Source does not exist"
                )

            # 如果目标是目录，保留原文件名 (If dest is directory, keep filename)
            if os.path.isdir(expanded_dest):
                expanded_dest = os.path.join(
                    expanded_dest,
                    os.path.basename(expanded_src)
                )

            # 复制文件或目录 (Copy file or directory)
            if os.path.isdir(expanded_src):
                shutil.copytree(expanded_src, expanded_dest)
            else:
                shutil.copy2(expanded_src, expanded_dest)

            return ExecutionResult(
                success=True,
                message=f"Copied: {src} -> {dest}",
                output=f"File copied from {src} to {expanded_dest}",
                file_path=expanded_dest
            )

        except Exception as e:
            logger.error(f"File copy failed: {e}")
            return ExecutionResult(
                success=False,
                message=f"Failed to copy file",
                error=str(e)
            )

    def _execute_file_delete(self, intent: Intent) -> ExecutionResult:
        """
        执行文件删除（高风险操作）。
        (Execute file delete operation - high risk)
        """
        slots = intent.slots
        path = slots.get("path", "")

        if not path:
            return ExecutionResult(
                success=False,
                message="No file path provided",
                error="Missing path parameter"
            )

        # 安全检查 (Safety check)
        is_safe, error_msg = self._is_safe_path(path)
        if not is_safe:
            return ExecutionResult(
                success=False,
                message="File access denied",
                error=error_msg
            )

        # 展开路径 (Expand path)
        expanded_path = os.path.expanduser(path)

        if self.dry_run:
            msg = f"[DRY RUN] Delete: {expanded_path}"
            logger.info(msg)
            return ExecutionResult(success=True, message=msg, output=msg)

        try:
            # 检查文件是否存在 (Check if file exists)
            if not os.path.exists(expanded_path):
                return ExecutionResult(
                    success=False,
                    message=f"File not found: {path}",
                    error="File does not exist"
                )

            # 删除文件或目录 (Delete file or directory)
            if os.path.isdir(expanded_path):
                shutil.rmtree(expanded_path)
                msg = f"Directory deleted: {path}"
            else:
                os.remove(expanded_path)
                msg = f"File deleted: {path}"

            return ExecutionResult(
                success=True,
                message=msg,
                output=msg
            )

        except Exception as e:
            logger.error(f"File delete failed: {e}")
            return ExecutionResult(
                success=False,
                message=f"Failed to delete: {path}",
                error=str(e)
            )

    def _execute_file_list(self, intent: Intent) -> ExecutionResult:
        """
        执行文件列表查询。
        (Execute file list operation)
        """
        slots = intent.slots
        path = slots.get("path", "~/")

        # 安全检查 (Safety check)
        is_safe, error_msg = self._is_safe_path(path)
        if not is_safe:
            return ExecutionResult(
                success=False,
                message="Directory access denied",
                error=error_msg
            )

        # 展开路径 (Expand path)
        expanded_path = os.path.expanduser(path)

        if self.dry_run:
            msg = f"[DRY RUN] List directory: {expanded_path}"
            logger.info(msg)
            return ExecutionResult(success=True, message=msg, output=msg)

        try:
            # 检查目录是否存在 (Check if directory exists)
            if not os.path.isdir(expanded_path):
                return ExecutionResult(
                    success=False,
                    message=f"Directory not found: {path}",
                    error="Not a directory"
                )

            # 列出文件 (List files)
            items = os.listdir(expanded_path)
            items.sort()

            # 分类文件和目录 (Categorize files and directories)
            files = []
            dirs = []
            for item in items:
                item_path = os.path.join(expanded_path, item)
                if os.path.isdir(item_path):
                    dirs.append(f"📁 {item}")
                else:
                    files.append(f"📄 {item}")

            # 组合输出 (Combine output)
            all_items = dirs + files
            total = len(all_items)

            # 限制输出数量 (Limit output)
            preview_items = all_items[:20]
            output = "\n".join(preview_items)
            if total > 20:
                output += f"\n... and {total - 20} more items"

            return ExecutionResult(
                success=True,
                message=f"Listed {total} items in {path}",
                output=output
            )

        except Exception as e:
            logger.error(f"File list failed: {e}")
            return ExecutionResult(
                success=False,
                message=f"Failed to list directory: {path}",
                error=str(e)
            )


def create_executor(dry_run: bool = False) -> MacOSExecutor:
    """Factory function to create executor."""
    return MacOSExecutor(dry_run=dry_run)
