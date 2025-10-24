-- Open URL in Safari
-- Usage: osascript safari.applescript <url>

on run argv
	set targetURL to item 1 of argv as text

	-- Use 'open' command to ensure Safari launches and opens URL
	do shell script "open -a Safari " & quoted form of targetURL

	delay 1

	return "Opened URL in Safari: " & targetURL
end run
