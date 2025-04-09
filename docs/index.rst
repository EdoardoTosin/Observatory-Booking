Observatory Booking Documentation
=================================

Welcome to the documentation for the **Observatory Booking Web App** - a self-hostable, modular application built with **Flask** and styled using **Tailwind CSS**, designed for managing observatory event reservations with real-time weather integration and secure user access.

.. raw:: html

    <img src="_static/screenshots/landing-page-light-mode.jpg" class="only-light" alt="Homepage Preview"
        style="max-width: 100%; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); filter: none !important;" />

.. raw:: html

    <img src="_static/screenshots/landing-page-dark-mode.jpg" class="only-dark" alt="Homepage Preview"
        style="max-width: 100%; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); filter: none !important;" />

.. admonition:: Artwork Credit
   :class: tip

   **Artwork by** `Alexandra Kostecka <https://alexrockheart.artstation.com/>`_.

Project Overview
----------------

- **Framework**: Flask (Python)
- **Styling**: Tailwind CSS
- **Database**: SQLite (default), PostgreSQL (optional)

**Key Features:**

- 🔒 **Role-based access control**: User, Admin, Superadmin with enforced permissions
- 📅 **Event booking system**: Event-based reservations with limits
- 🌤️ **Weather-aware scheduling**: Real-time data from the Open-Meteo API
- ⚙️ **Admin dashboard**: Manage users, events, system config
- 🔐 **Secure user data**: AES-encrypted name/email, bcrypt passwords, session hardening
- 🚀 **Responsive UI**: Mobile-first, Tailwind-based with support for dark mode
- ⏱️ **Rate limiting**: Prevent brute-force and abuse
- 🕒 **Timezone-aware**: All logic respects configured IANA timezone

Contents
--------

.. toctree::
   :maxdepth: 1
   :caption: 🚀 Introduction

   introduction
   installation
   usage
   architecture

.. toctree::
   :maxdepth: 1
   :caption: 🔐 API Endpoints

   endpoints

.. toctree::
   :maxdepth: 1
   :caption: 🧱 Application Structure

   components/index

Indices and Tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

License
-------

This project is licensed under the **MIT License**. See the `LICENSE` file for details.
