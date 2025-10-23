-- Set system volume
-- Usage: osascript system.applescript <percentage>

on run argv
	set volumePercent to item 1 of argv as integer

	-- Ensure value is between 0 and 100
	if volumePercent < 0 then
		set volumePercent to 0
	else if volumePercent > 100 then
		set volumePercent to 100
	end if

	-- Set output volume (0-100)
	set volume output volume volumePercent

	return "Volume set to " & volumePercent & "%"
end run
