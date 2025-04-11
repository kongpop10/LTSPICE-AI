$WshShell = New-Object -ComObject WScript.Shell
$path = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\LTSpice AI.lnk"
$Shortcut = $WshShell.CreateShortcut($path)
$Shortcut.TargetPath = "C:\WINDOWS\system32\cmd.exe"
$Shortcut.Arguments = "/c streamlit run c:\Users\USER\Dev\AI\SPICEAI\ltspice-ai-assistant\app.py"
$Shortcut.IconLocation = "c:\Users\USER\Dev\AI\SPICEAI\ltspice-ai-assistant\lt_icon.ico"
$Shortcut.WorkingDirectory = "c:\Users\USER\Dev\AI\SPICEAI"
$Shortcut.Save()