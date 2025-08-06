# Better Ryzen Controller  
A more powerful and flexible Ryzen CPU control tool for advanced users  

- [What is this?](#whats-this)  
- [Installation](#installation)  
  - [Windows](#windows)  
- [Troubleshoot, Q&A](#troubleshoot-qa)  
- [Build](#build)  
  - [Pre-requisites](#pre-requisites)  
  - [Building binaries](#building-binaries)  

---

## What's this?

- Take full control of your laptop's Ryzen CPU with complete freedom to tweak and optimize.
- Compatible with Ryzen 2000, 3000, 4000, and 5000 series (for now).
- Built for enthusiasts who want more than what OEM tools provide.

Features include:

- Set PPT, TDC, EDC power limits  
- Temperature limit customization  
- Auto-load configuration on startup  
- Clean, modern Fluent-style UI  
- Multi-language support (English/中文)

---

## Installation

### Windows

1. Go to the [Releases Page](https://gitlab.com/ryzen-controller-team/ryzen-controller/-/releases)  
2. Download the latest `BetterRyzenController-X.X.X.exe`  
3. Run the installer and follow the instructions  
4. Start customizing your Ryzen CPU!

> **Note:** Administrator privileges are required for some actions.

---

## Troubleshoot, Q&A

> **Does this program run on Windows 7 or older?**  
No, it doesn't. This application uses Python 3.10+, which is not supported on Windows 7 and below.  
Please use Windows 10 or 11.

> **My settings aren’t applying correctly. Why?**  
- Make sure you’re running the program with **Administrator privileges**.  
- Some OEM BIOS settings may block external control.  

> **Will this damage my hardware?**  
- All changes are temporary and revert on reboot.  
- But misconfiguration **can cause instability**. Use responsibly.

---

## Build

### Pre-requisites

- Python 3.10 or higher  
- `pip`, `PyInstaller`, and other dependencies listed in `requirements.txt`  
- Windows OS (tested on Windows 10/11)

Install dependencies:

```bash
pip install -r requirements.txt
```

### Building binaries

Use PyInstaller to build a standalone executable:

```bash
pyinstaller main.spec
```

The output `.exe` will be found in the `/dist` folder.

---

## License

This project is open-sourced under the MIT License.  
See the [LICENSE](./LICENSE) file for more information.

---

## Credits

- Inspired by Ryzen Controller, RyzenAdj, and the open-source AMD tweaking community.  
- UI powered by Fluent Design.  
- Huge thanks to everyone who tested and contributed!
