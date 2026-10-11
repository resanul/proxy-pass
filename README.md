# ProxyPilot

Windows proxy manager for proxy-aware applications in Squid → Cisco WSA networks.

**Current version:** 1.0.0  
**Windows outputs:** `ProxyPilot.exe` and `ProxyPilot-Setup-1.0.0.exe`

## Features

- GUI to configure a Squid HTTP proxy without authentication.
- Windows Internet Settings (WinINET) proxy settings for HTTP/HTTPS.
- Optional WinHTTP configuration (`netsh`; may require elevated rights).
- Optional user-level `HTTP_PROXY`, `HTTPS_PROXY`, and `ALL_PROXY` environment variables.
- TCP listener test plus HTTPS endpoint test through Squid.
- Initial settings backup, restore, and reset-to-direct actions.
- Windows CI workflow for repeatable EXE and installer builds.

## Critical scope limitation

ProxyPilot v1.0 configures proxy-aware software; it is **not** a transparent system-wide traffic tunnel. Apps using custom network stacks, hard-coded direct connections, their own proxy settings, UDP/QUIC, or services running under other user accounts may ignore Windows proxy settings and environment variables.

If an application ignores these settings, configure its own supported proxy option or use an organization-approved VPN/TUN or endpoint traffic-redirection product. A standard HTTP CONNECT proxy cannot universally forward arbitrary system TCP/UDP traffic. This project intentionally does not install network drivers or silently change firewall/routing rules.

## Build on Windows locally

1. Install Python 3.11+ from https://www.python.org/downloads/windows/ and enable the Python launcher.
2. Download or clone this repo on Windows.
3. Run `build.bat`.
4. The EXE will be at `dist\ProxyPilot.exe`.

To create an installer, install Inno Setup 6 and compile `installer\ProxyPilot.iss` after building the EXE. The output is `dist-installer\ProxyPilot-Setup-1.0.0.exe`.

## Build through GitHub Actions

The workflow `.github/workflows/windows-release.yml` builds on a Windows runner and uploads both outputs as a workflow artifact. It runs on pushes to `main` or `release/**` and can be started manually from **Actions → Windows build and release → Run workflow**.

To publish a GitHub Release:
1. Merge/review the v1.0 source into the default branch as appropriate.
2. Create and push a tag such as `v1.0.0` after confirming the workflow is on the tagged commit.
3. The tag workflow uploads the EXE and installer to the GitHub Release.

The binary is not committed to source control. Use GitHub Actions artifacts/releases for build outputs.

## Use

1. Launch ProxyPilot.
2. Enter the reachable Squid listener IP/FQDN and port. The default port shown is `3128` as a common example; use your real listener.
3. Click **Test Proxy**.
4. Click **Apply**.
5. Restart target apps so they inherit environment variables.
6. Use **Restore Backup** to restore the snapshot taken before the first Apply, or **Reset to Direct** to disable WinINET proxy and remove ProxyPilot's proxy environment variables.

The backup is kept as `%APPDATA%\ProxyPilot\backup.json`. It is intentionally not overwritten on later applies, preserving the original snapshot.

## Troubleshooting

- TCP connection failure: verify route/firewall and `Test-NetConnection <SQUID_IP> -Port <SQUID_PORT>`.
- HTTP 407: this build assumes IP-based access and does not implement proxy authentication.
- Timeout: inspect Squid access/cache logs and Cisco WSA logs to identify the failing hop.
- TLS error: inspect the approved corporate CA/trust and TLS inspection configuration; do not disable certificate verification globally.
- Antigravity not using proxy: verify the request appears in Squid logs; if absent, its backend may ignore the configured proxy. This utility cannot force that app to comply.

## Security and recovery notes

- Run as administrator only if needed for WinHTTP.
- Group Policy may override Windows proxy values.
- Review the bypass list for your network before applying it.
- Test on a non-critical endpoint first.
- This app does not collect or store credentials.