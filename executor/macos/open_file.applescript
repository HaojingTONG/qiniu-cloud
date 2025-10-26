-- Open file in default application
-- Usage: osascript open_file.applescript <file_path>

on run argv
	set file_path to item 1 of argv as text

	-- Use Finder to open the file with its default application
	tell application "Finder"
		try
			open POSIX file file_path
			activate
			return "Opened file: " & file_path
		on error errMsg
			return "Error opening file: " & errMsg
		end try
	end tell
end run
