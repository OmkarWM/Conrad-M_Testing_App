# WM Testing Console

Industrial desktop testing console built using PyQt6 for managing Front-End, Back-End, and End-to-End testing workflows.

## Features

* Unified launcher interface
* Front-End testing module
* Back-End testing module
* End-to-End testing module
* COM port configuration system
* Database path selection support
* Automated bridge process handling
* Multi-process testing workflow
* PyQt6-based desktop application

## Requirements

* Windows 10 / Windows 11
* Python 3.10+
* com0com virtual serial port driver

## COM Port Setup

Install com0com:
https://com0com.com/download/

Create virtual COM port pairs before running the application.

Example:

* COM10 ↔ COM11
* COM12 ↔ COM13
* COM14 ↔ COM15

Assign the created ports inside the WM Testing Console configuration panel before starting tests.

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Run Application

### Run from Source

```bash
python testing_sim.py
```

### Run Packaged Executable

Launch:

```text
WM_TestingConsole.exe
```

Ensure the complete release ZIP is extracted before launching the executable.

# User Guide: 

Follow these instructions to configure your virtual environment, map your ports, and execute tests using the console.

## Step 1: Initialize Virtual COM Port Pairs

Because this software simulates real hardware communication over serial ports, you must create virtual linked pairs on your computer before running the application.

1. Open your virtual serial port utility (such as com0com)
2. Create three distinct virtual COM pairs
3. Note the generated port names

Example:

* COM6 ↔ COM7
* COM8 ↔ COM9
* COM10 ↔ COM11

## Step 2: Open the Console Interface

### Source Mode

```bash
python testing_sim.py
```

### Executable Mode

Launch:

```text
WM_TestingConsole.exe
```

## Step 3: Configure Hardware Ports

When the GUI opens, locate the Hardware Configuration Panel at the bottom of the interface.

Configure:

* MEGA Serial Port
* MEGA Bridge Port
* X-RAY Serial Port
* X-RAY Bridge Port
* UNO Serial Port
* UNO Bridge Port

The port selectors are editable.
Custom COM names can be typed manually if required.

Port selections are automatically saved to:

```text
port_config.txt
```

## Step 4: Select Database Path

1. Click the `BROWSE` button
2. Select the required database file
3. The selected path is automatically stored

## Step 5: Execute Simulation Tests

Select a testing tab:

* Front-End
* Back-End
* End-to-End

Click the RUN button to start the selected testing workflow.

While running:

* Status indicator turns Green
* Other testing modules are temporarily disabled
* Active serial communication processes begin execution

## Step 6: Stop Active Processes

Click the STOP button or close the testing module window to terminate the active testing workflow.

After stopping:

* COM port settings can be modified
* Database path can be changed
* Another testing module can be launched

## Notes

* Configure COM ports before starting tests
* Ensure COM ports are not occupied by other applications
* Extract release ZIP fully before running executable

## Important

Before running the following modules:

* Front-End testing
* End-to-End testing

Ensure the Machine GUI is already launched and running.


