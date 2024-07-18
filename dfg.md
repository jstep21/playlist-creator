# UPSmon

A simple UPS monitor for [UPS HAT (B) for Raspberry Pi](https://www.waveshare.com/product/ups-hat-b.htm).

## Installation

You can download the latest release from the [releases page](https://github.com/maximousblk/upsmon/releases) or build it yourself™️.

### Requirements

- [Zig](https://ziglang.org/)
- Make sure you have I2C enabled on your Raspberry Pi

### Clone this repository

```bash
git clone https://github.com/maximousblk/upsmon.git
```

### Install

```bash
cd upsmon
zig build install -Doptimize=ReleaseSafe -p ~/.local # will install to ~/.local/bin/upsmon
```

## License

This project is licensed under the [MIT License](LICENSE).