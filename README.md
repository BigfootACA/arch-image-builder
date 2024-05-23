# arch-image-builder

A tool to build flashable and bootable image for Arch Linux

## Install requirements

Currently only support Arch based distros

### Arch Linux

Install required packages

```commandline
pacman -S p7zip rsync pyalpm python-yaml python-libarchive-c
```

For cross build (UNTESTED)

```commandline
pacman -S qemu-user-static-binfmt
```

## Example

```commandline
python build.py -c target/ayn-odin2-sdcard,locale/zh-cn,desktop/gnome -m bfsu,tuna
```

## Options

| Option                              | Description                        |
|-------------------------------------|------------------------------------|
| -C, --clean                         | Clean workspace before build       |
| -m MIRROR, --mirror MIRROR          | Select mirror to download package  |
| -p PRESET, --preset PRESET          | Select preset to create package    |
| -c CONFIG, --config CONFIG          | Select configs to build            |
| -o WORKSPACE, --workspace WORKSPACE | Set workspace for builder          |
| -d, --debug                         | Enable debug logging               |
| -G, --no-gpgcheck                   | Disable GPG check                  |
| -r, --repack                        | Repack rootfs only                 |

## License

SPDX: GPL-3.0-or-later
