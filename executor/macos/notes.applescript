-- Create a new note in Notes app
-- Usage: osascript notes.applescript <title> <body>

on run argv
	set noteTitle to item 1 of argv as text
	set noteBody to item 2 of argv as text

	tell application "Notes"
		-- Create new note in default account
		tell account 1
			set newNote to make new note at folder "Notes" with properties {name:noteTitle, body:noteBody}
		end tell

		activate
	end tell

	return "Note created: " & noteTitle
end run
