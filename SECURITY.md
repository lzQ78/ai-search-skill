# Security

Do not commit `.env` or real provider credentials.

This project reads API keys from local environment variables only. The checked-in
`.env.example` file must contain empty values or commented examples.

If you find a security issue, open a GitHub security advisory or a minimal issue
that does not include secrets.
