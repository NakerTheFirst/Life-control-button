# Life Control Button
A simple app that helps you schedule your PC shutdown time. Run while starting a coding or gaming session and make sure you don't end up going to sleep at 3 AM. You can also make it run at system startup (see below) to make sure you don't end up binging.

<br>
<p align="center"><img width="380" src="assets/gui_mode_1.png" alt="Life Control Button GUI in at-a-specific-time mode">&nbsp;<img width="380" src="assets/gui_mode_2.png" alt="Life Control Button GUI in after-a-duration mode"></p>
<p align="center">Life Control Button GUI</p>

## Features
* Schedule PC shutdown at a set time
* Schedule PC shutdown after set duration
* Glowing ember theme with a drifting CRT scanline texture
* Clean, minimalist interface
* Live countdown if you reopen the app while a shutdown is already pending
* Register the app to run at every system startup with a single flag
* Hit the Life Control Button via enter (wow!)
* Full keyboard navigation: up/down arrows adjust the value, right/left jump between sections, Tab moves through the controls

## Installation & Usage
1. Download `LifeControlButton.zip` from the [release page](https://github.com/NakerTheFirst/Life-control-button/releases/latest).
2. Unblock the zip: right-click it, Properties, tick "Unblock" (or run `Unblock-File LifeControlButton.zip` in PowerShell). Windows marks downloaded files as coming from the internet, and SmartScreen silently blocks marked exes at logon.
3. Extract it anywhere and run `LifeControlButton.exe` - it sits at the top of the folder.

Select your preferred shutdown mode:
* Choose "at a specific time" to set a target time
* Choose "after a duration" to set a countdown

Click "Get Life Control" or press Enter to schedule the shutdown.

## Run at startup
The app can register itself to launch at every logon - no Task Scheduler needed. In PowerShell, from the extracted folder:
```powershell
.\LifeControlButton.exe --install-startup
```
Undo it with `--uninstall-startup`. Both write only to the per-user registry, so no admin rights are required. If the app does not start with the system, you most likely skipped step 2 above.

## Running from source
Requires Python 3.10+ and PyQt6:
```bash
git clone git@github.com:NakerTheFirst/Life-control-button.git
cd Life-control-button
pip install -r requirements.txt
pythonw main.py
```
`pythonw` avoids opening a console window.

## Note
This application uses the native Windows `shutdown` command (Windows 10 and 11), so Linux and Mac are unsupported. There is deliberately no cancel button. Feel free to contribute.
