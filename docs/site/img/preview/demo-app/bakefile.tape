Output bakefile-preview.gif
Set Shell "zsh"
Set FontSize 18
Set Width 960
Set Height 640
Set Theme {"background":"#0E1C2C","foreground":"#DDB283","cursor":"#DDB283","cursor_text":"#0E1C2C","selection_background":"#3B6FA5","selection_foreground":"#F0DEC2","palette":["#1E3A55","#C25B4E","#5CB87A","#D2A06B","#4F8CC8","#B08CC0","#64A8D8","#DDB283","#48678A","#D97E6A","#7BD49A","#E8C08A","#7AB0DE","#C9A6D9","#8CC8E8","#F0DEC2"]}
Set Padding 42
Set CursorBlink false

Type "bat --theme=ansi --style=numbers -P bakefile.py"
Enter
Sleep 4s
Ctrl+L
Sleep 300ms

Type "bake --help"
Enter
Sleep 4s
Ctrl+L
Sleep 300ms

Type "bake build"
Enter
Sleep 4s

Sleep 3s
