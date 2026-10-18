# Security Policy

Maintainer: **AliFanni-79**

## Reporting a vulnerability

Please do **not** publish working credentials, customer subscription URLs, Telegram bot tokens, 3x-ui API tokens, database dumps, or other private deployment data in a public GitHub Issue.

For sensitive security reports, contact:

- Telegram: @AliFanni_79
- Repository: https://github.com/AliFanni-79/SpeedyBot

Include the affected VizzPN Shop Bot version, relevant component, reproduction steps, expected/actual behavior and a redacted log if useful.

## Deployment reminders

- Keep `.env` outside version control and restrict its permissions.
- Treat the 3x-ui Bearer token as an administrative credential.
- Treat subscription URLs, direct proxy URIs and QR codes as credentials.
- Keep Ubuntu, Python packages and 3x-ui updated.
- Restrict SSH and panel exposure appropriately.
- Rotate any token immediately if it is accidentally published.
