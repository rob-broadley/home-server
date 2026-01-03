# home-server

System to build an Ignition configuration and a Combustion script to provision
a Leap Micro (6.2) based home server.

The operating system images are available here: https://get.opensuse.org/leapmicro/6.2/

This provisions:

- network (adapter `eth0`)
- root user
  - password
- admin user
  - password
  - authorised SSH keys
  - second factor one-time passcodes
- localisation (en GB)
- disk encryption (TPM backed with fallback password)
- weekly updates (operating system & services)
- Cockpit
  - access for admin (2FA - password + one-time passcode)
- Adguard Home service
  - DNS (inc. filtering)
  - DHCP

## Requirements

- `uv`

## Building the Provisioning Configuration

The provisioning requires secrets such as passwords,
these are loaded from environment variables and used to populate
jinja templates, which are stored in version control (this repo).

### Setting Environment Variables

The preferred method to provide these variables is with an environment
file (`.env`).
Below is a template:

```
ROOT_PASSWD="<root password hash>"
ADMIN_PASSWD="<admin password hash>"
ADMIN_SSH_KEYS="<';' separated list of SSH public keys>"
ADMIN_OTP_SECRET="<secret key>"
DISK_PASSWD="<password for disk encryption>"
ADGUARD_MAC="<locally administered MAC address>"
```

Hashed passwords can be generated with:

```sh
openssl passwd -6
```

The secret key can be generated with:

```sh
head -c 1024 /dev/urandom | openssl sha1 | awk '{ print $2 }'
```

To convert the hex output into a base32 code for OTP apps use `xxd` and `base32`,
for example:

```sh
source .env; echo "$ADMIN_OTP_SECRET" | xxd -r -p | base32
```

### Creating Ignition Drive

Running `uv run build` will create the files needed for provisioning
and place them in the `_build` directory.

These files need to be copied to the root level of the filesystem
on an `ignition` partition of a USB drive.

The filesystem for the `ignition` partition should be as follows:

```
<root directory>
├── combustion
│   └──  script
└── ignition
    └──  config.ign
```

Ensure the drive is attached when installing the OS, and the provisioning will
happen automatically once the install completes (first boot).

An ISO filesystem can be created using `mkisofs` as follows:

```sh
mkisofs -full-iso9660-filenames -o ignition.iso -V ignition _build
```

## Development Setup

Set up git hooks: `uv run pre-commit install`.
Then to commit `uv run git commit`.

Alternatively run `uv sync` to create the Python virtual environment (`.venv`),
then activate it before running `pre-commit` or `git` commands.
