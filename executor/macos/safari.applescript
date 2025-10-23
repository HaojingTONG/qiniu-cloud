-- Open URL in Safari
-- Usage: osascript safari.applescript <url>

on run argv
	set targetURL to item 1 of argv as text

	tell application "Safari"
		activate

		-- Try to use existing window, or create new one
		if (count of windows) is 0 then
			make new document with properties {URL:targetURL}
		else
			set URL of front document to targetURL
		end if
	end tell

	return "Opened URL in Safari: " & targetURL
end run
