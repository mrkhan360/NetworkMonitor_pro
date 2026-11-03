NETWORK MONITOR PRO — Fresh rebuild

Features:
- Live download/upload speed in MB/s
- Ping and Online/Offline status
- Drag the floating panel anywhere
- Settings: width, font size, transparency, background/text colors
- Show/hide Download, Upload, Ping, Status
- Always-on-top toggle
- Settings are saved in %APPDATA%\\NetworkMonitorPro\\settings.json

BUILD EXE WITHOUT INSTALLING PYTHON ON YOUR PC:
1. Create a GitHub repository and upload all files/folders from this ZIP.
2. Keep the workflow file at .github/workflows/build-windows.yml
3. Open the repository Actions tab.
4. Select "Build Network Monitor EXE" and click Run workflow.
5. Wait until the run succeeds. Open the run and download artifact
   "NetworkMonitorPro-Windows".
6. Extract the downloaded ZIP and run NetworkMonitorPro.exe.

The app is a floating desktop panel, NOT text embedded inside the Windows 11 taskbar.
To run locally from Python: pip install -r requirements.txt, then python network_monitor.py
