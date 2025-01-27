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

### Build using preset

```commandline
python build.py -p ayn-odin2-ufs-gnome-global -m bfsu,tuna
```

### Manual build

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
| -a ARTIFACTS, --artifacts ARTIFACTS | Set artifacts folder for builder   |
| -d, --debug                         | Enable debug logging               |
| -G, --no-gpgcheck                   | Disable GPG check                  |
| -r, --repack                        | Repack rootfs only                 |

## License

SPDX: GPL-3.0-or-later
