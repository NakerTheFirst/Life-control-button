# Life Control Button
A simple app that helps you schedule your PC shutdown time. Run while starting a coding or gaming session and make sure you don't end up going to sleep at 3 AM. You can also run it at system startup via Windows Task Scheduler to make sure you don't end up binging.

<br>
<p align="center"><img width="500" src="https://github.com/user-attachments/assets/cf5798be-2c8e-4e04-8a12-71434a1147fc" alt="Image of Life Control Button GUI"></p>
<p align="center">Life Control Button GUI</p>

## Features
* Schedule PC shutdown at a set time
* Schedule PC shutdown after set time
* Dark theme inspired by Atom One Dark
* Clean, minimalist interface
* Hit the Life Control Button via enter (wow!)

## Requirements
* Python 3.10
* PyQt6

## Installation & Usage
1. Clone this repository:
  ```bash
  git clone git@github.com:NakerTheFirst/Life-control-button.git
  ```
2. Install the dependencies:
  ```bash
  pip install -r requirements.txt
   ```
3. Run the application:
  ```bash
  python main.py
  ```

Select your preferred shutdown mode:
* Choose "Turn PC off at a specific time" to set a target time
* Choose "Turn PC off after a specific duration" to set a countdown

Click "Get Life Control" or press Enter to schedule the shutdown.

## Note
This application uses the Windows `shutdown` command through PowerShell, so Linux and Mac are unsupported. Feel free to contribute. 
