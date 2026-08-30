# Security policy

## Alpha support boundary

The planned `v0.1.0-alpha.1` release is research software. Only the latest alpha commit/release is supported for security fixes. The benchmark is not a sandbox, security certification, credential manager, or guarantee that a coding-agent host is safe.

## Report privately

Use GitHub private vulnerability reporting for this repository when available. If that control is unavailable, contact the repository owner through the private contact method on the owner's GitHub profile. Do not open a public issue containing an exploit, credential, private run artifact, or identifying environment detail.

Include:

- affected revision and component;
- minimal reproduction using synthetic data;
- expected impact and evidence;
- whether credentials or private artifacts may have been exposed; and
- a safe way to coordinate disclosure.

Do not send OAuth tokens, API keys, cookies, credential files, raw private transcripts, or private chain-of-thought. Maintainers will acknowledge a report when capacity permits, assess scope, preserve evidence, and coordinate a fix/disclosure. No response-time SLA is promised for the alpha.

## Safe research

Use isolated synthetic fixtures, the least privileges needed, and accounts/systems you are authorized to test. Do not test against third-party repositories or services without permission. Live-host experiments must follow the repository's bound-plan and scheduler rules.