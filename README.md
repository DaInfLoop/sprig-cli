# sprig CLI
An unofficial tool to help you manage your [Sprig](https://sprig.hackclub.com)!

> [!WARNING]  
> This is an unofficial tool and barely tested. I do not assume any responsibility for any damages caused to your Sprig while using this tool.
>
> That being said, if any bugs do arise, please contact me in [my channel on the Hack Club Slack](https://hackclub.slack.com/archives/C06SY7X0ESK)!

## Installation
Head over to [nightly.link](https://nightly.link/DaInfLoop/sprig-cli/workflows/build/main) and grab the binary for your OS.

## Usage
Once installed, run `./sprig <command> [options]` or `./sprig.exe <command> [options]`.
```
Usage: sprig <command> [options]

  sprig CLI - a tool to help you interact with your Sprig

Options:
  --help  Show this message and exit.

Commands:
  flash    Flash your Sprig with the latest firmware
  upload   Upload a game to your Sprig
  version  Get the version of your Sprig connected to this device
```

### sprig flash
Flashes the latest SPADE software on to your Sprig. Requires your Sprig to be in [BOOTSEL mode](https://github.com/hackclub/sprig/blob/main/docs/UPLOAD.md#bootsel).

```
$ sprig flash
Flashing firmware to your Sprig (/media/haroon/RPI-RP2)...
Firmware flashed successfully!
```

### sprig upload \<file.js> [--name "..."]
Upload a game to your Sprig, and optionally give it a name to be displayed.

```
$ sprig upload game.js --name "My Game"
Uploading game.js to your Sprig...
Upload completed successfully!
```

## sprig version
View what version of SPADE is on your Sprig

```
$ sprig version
Your Sprig is on SPADE version: 2.0.1
```

## License
This software is licensed under the MIT License. A version of this is avaliable for reading at [LICENSE](/LICENSE).