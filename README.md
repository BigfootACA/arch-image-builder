# arch-image-builder

A tool to build flashable and bootable image for Arch Linux

## Install requirements

### Arch Linux

Install required packages

```commandline
pacman -S p7zip rsync pyalpm python-yaml python-libarchive-c
```

For cross build (UNTESTED)

```commandline
pacman -S qemu-user-static-binfmt
```

### Debian / Ubuntu (Debian-based)

Install required packages

```commandline
apt update
apt install -y pacman-package-manager gpg gpg-agent libalpm-dev libssl-dev libarchive-dev libgpgme-dev libcurl4-openssl-dev libmount-dev p7zip rsync python3-pip python3-venv
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

For cross build (UNTESTED)

```commandline
apt install -y qemu-user-static
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
