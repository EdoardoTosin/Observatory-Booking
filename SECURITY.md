# Security Policy

## Reporting a Vulnerability

If you discover a potential security issue or vulnerability, please report it directly via:

- Email: [Edoardo Tosin](https://github.com/edoardotosin)
- GitHub: [Security Advisories](https://github.com/EdoardoTosin/Observatory-Booking/security/advisories)

Please do **not** create a public issue. I will review and respond as soon as possible, typically within **48–72 hours**.

## Project Scope

This is a solo-maintained project without formal versioning at the moment. Fixes will be applied to the `main` branch as needed.

Security is a priority:
- AES-256 encryption is used for sensitive user data
- Role-based access control is enforced at the route level
- Input handling and sessions follow Flask security practices

## Recommendations for Deployers

If you're deploying this project yourself:

- Use HTTPS in production
- Store `.env` secrets securely
- Keep dependencies up to date (`pip install --upgrade -r requirements.txt`)
- Review and configure access controls before going live

## Contributions

Security enhancements (e.g. CSP, rate limiting, hardening) are welcome. Please reach out before submitting large changes related to authentication, encryption, or user access logic.

Thanks for helping make this project safer for everyone!
