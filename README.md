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

```bash id="fqekpk"
pip install -r requirements.txt
```

## Run Application

```bash id="efbf6w"
python testing_sim.py
```

## Notes

* Configure COM ports before starting tests
* Ensure COM ports are not occupied by other applications
* Extract release ZIP fully before running executable
