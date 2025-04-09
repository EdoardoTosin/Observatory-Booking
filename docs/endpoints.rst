API Endpoints
=============

.. contents:: Table of Contents
   :local:
   :depth: 2

Public Endpoints
----------------

These endpoints are accessible to all users, including unauthenticated visitors. They support general site functionality such as authentication, viewing legal documents, and accessing publicly available content.

.. openapi:: specs/openapi.yaml
   :paths:
     /
     /favicon.ico
     /contact
     /faq
     /terms_of_service
     /privacy_policy
     /cookie_policy
     /login
     /register

User Endpoints
--------------

These endpoints require the user to be authenticated. They allow registered users to perform actions related to their account and event participation, such as viewing available slots, booking events, canceling bookings, and managing passwords.

.. openapi:: specs/openapi.yaml
   :paths:
     /logout
     /events
     /booking
     /cancel_booking/{slot_id}
     /change_password

Admin Endpoints
---------------

Accessible only by authenticated admin users, these endpoints provide administrative control over application configuration, event validation, weather updates, and user management tasks such as role assignment and user blocking.

.. openapi:: specs/openapi.yaml
   :paths:
     /admin/config
     /admin/user/block
     /admin/user/role
     /admin/confirm_event
     /admin/update_events_weather
     /admin/delete_event/{event_id}

Superadmin Endpoints
--------------------

Reserved for superadministrators, these endpoints enable the execution of critical account management actions such as permanent user deletion. They should be protected with strict access controls and auditing.

.. openapi:: specs/openapi.yaml
   :paths:
     /admin/user/delete

Utility Endpoints
-----------------

These endpoints serve JavaScript assets that enhance frontend interactivity for authenticated users. Though technically public, they are primarily intended to support functionality on protected pages.

.. openapi:: specs/openapi.yaml
   :paths:
     /js/events.js
	 /js/change_password.js
	 /js/admin.js
	 /js/user_accounts.js
	 /js/events_calendar.js

Common Error Responses
-----------------------

These reusable response descriptions are used across multiple endpoints.

.. list-table::
   :header-rows: 1

   * - Component Name
     - Description
   * - NotFound
     - Resource not found (custom 404 page).
   * - Forbidden
     - Access denied (custom 403 page).
   * - InternalServerError
     - Unexpected server error (custom 500 page).
