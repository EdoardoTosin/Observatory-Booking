Introduction
============

Overview
--------

The **Observatory Booking Web App** is a Flask-based, self-hostable application designed to manage **events reservations for observatories**, with integrated **weather forecasting** and **role-based user access**. Built using the **Flask** framework and styled with **Tailwind CSS**, it offers a secure, modern, and responsive interface for users and administrators.

Purpose
-------

The web app enables users to book events by evaluating the weather rating, using real-time **Open-Meteo weather data**, with a user-friendly interface. For admins, it supports seamless management of events, users, and weather evaluations.

Key Features
------------

- **User Registration and Authentication**
  - Encrypted names/emails (AES) and bcrypt-hashed passwords.
  - Role-based access control: **User**, **Admin**, and **Superadmin**.
  - Superadmins are bootstrapped from environment variables.

- **Events Management**
  - Users can search, filter, sort, and browse a date-picker calendar to find events, then view, book, and cancel them.
  - Admins can create, update, and confirm events, manage per-event capacity, and revoke individual bookings.
  - Bookings are blocked if full, expired, or weather-restricted.

- **Progressive JSON API**
  - Every page renders a full first paint as plain server-rendered HTML (works with JavaScript disabled).
  - A consistent ``/api/v1/...`` JSON API backs filtering, pagination, and bulk/corrective admin actions via ``fetch()`` on top of that first paint, without full page reloads.

- **Weather-Aware Booking**
  - Uses hourly forecasts (cloud cover, dew point, visibility, precipitation).
  - Events are scored from 0-100 and flagged if below configured threshold.
  - Background updates run every 3 hours via APScheduler.

- **Time Zone & Location Awareness**
  - Fully IANA-compliant timezone support.
  - Twilight times and weather aligned with configured latitude/longitude.

- **Security**
  - AES encryption for PII, rate-limiting, secure cookie/session handling.
  - Automatic logout for blocked or deleted users.
  - Strict role enforcement: Admins cannot modify Superadmins.

- **Responsive User Interface**
  - Built with Tailwind CSS.
  - Supports dark mode, mobile views, and component-based templating.

Target Audience
---------------

This system is ideal for:
- **Astronomy clubs** managing shared telescope time.
- **Educational institutions** teaching observational astronomy.
- **Privacy-focused self-hosters** looking for modern, secure infrastructure.


Deployment Scenarios
--------------------

The application is designed to be **flexible and easy to deploy**:
- Use **SQLite** for quick local deployment or **PostgreSQL** for production-scale installations.
- Deploy with Flask's built-in server for development or a **WSGI server** (e.g., Waitress, Gunicorn) for production.
- Optional integration with **reverse proxies** like Nginx or Apache for SSL termination and enhanced performance.

License
-------

This project is licensed under the **MIT License**. See the `LICENSE` file for details.

Getting Started
---------------

Continue to the :doc:`installation` guide to set up and run the application in your environment.
