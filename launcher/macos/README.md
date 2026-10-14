# Optional macOS launcher

The launcher starts or stops the relay and Terminal host together, checks their
exact process arguments and refuses duplicate starts. It does not start at login,
force-kill a process, or alter the OpenClaw Gateway. Install and pair the services
first using the repository's relay and Terminal instructions.

`control.py` uses the existing compatibility installation paths and expects Node
at `/usr/local/bin/node` and Python at `/usr/bin/python3`. Check those executable
paths in `SPECS` for your host before installing. The commands run as the current
user and read private runtime configuration at execution time.

For a new launcher installation, copy `control.py`, `setup_help.py` and
`Setup Help.html` into `~/Library/Application Support/HardwareOne Launcher/`.
Keep that directory private. If it already exists, compare the existing source
before replacing files; preserve its configuration and unique changes.

Compile the UI into a new app path with the macOS AppleScript compiler:

```sh
mkdir -p "$HOME/Applications"
osacompile -o "$HOME/Applications/HardwareOne G2 Terminal Bridge.app" launcher/macos/Launcher.applescript
```

Use an unused app path. This compiles the UI only; it does not start services.
The setup dialog computes the device endpoint from local private configuration.
The device key is read and copied only after the explicit Copy device key action;
it is not embedded in the app, printed or logged. The HTML guide contains only
generic instructions and no deployment data.

For headless operation after installing the support files:

```sh
python3 "$HOME/Library/Application Support/HardwareOne Launcher/control.py" status
```

Replace `status` with `start` or `stop` to operate both services. Stopping services
can interrupt active conversations. The source tests mock service processes and
clipboard commands; they do not operate the installed services.
