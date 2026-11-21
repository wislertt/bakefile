Output bat-png.gif
Set Shell "zsh"
Set FontSize 18
Set Width 640
Set Height 800
Set Theme {"background":"#0E1C2C","foreground":"#DDB283","cursor":"#DDB283","cursor_text":"#0E1C2C","selection_background":"#3B6FA5","selection_foreground":"#F0DEC2","palette":["#1E3A55","#C25B4E","#5CB87A","#D2A06B","#4F8CC8","#B08CC0","#64A8D8","#DDB283","#48678A","#D97E6A","#7BD49A","#E8C08A","#7AB0DE","#C9A6D9","#8CC8E8","#F0DEC2"]}
Set Padding 24
Set CursorBlink false
Hide
Type "bat --theme=ansi --style=numbers -P bakefile.py > /dev/null 2>&1"
Enter
Sleep 2s
Type "clear"
Enter
Sleep 1s
Show
Type "bat --theme=ansi --style=numbers -P bakefile.py"
Enter
Sleep 3s
