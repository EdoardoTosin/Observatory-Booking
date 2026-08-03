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

These endpoints require the user to be authenticated. They allow registered users to perform actions related to their account and event participation, such as viewing available events, booking events, canceling bookings, and managing passwords.

.. openapi:: specs/openapi.yaml
   :paths:
     /logout
     /events
     /booking
     /cancel_booking/{event_id}
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

JSON API (v1)
-------------

A separate ``/api/v1/...`` namespace used by the Events page, the admin User Accounts tab, and the admin Events Calendar tab to filter, paginate, and run bulk/corrective actions via ``fetch()`` without a full page reload. Every page still renders its first paint as plain server-rendered HTML (so it works with JavaScript disabled); these endpoints only back the *subsequent* interactions on top of that first paint.

Authenticated the same way as the rest of the app (session cookie via ``login_required``/``admin_required`` - not a separately token-authenticated public API). State-changing requests (``POST``) must send the CSRF token via the ``X-CSRF-Token`` header instead of a form field, since the body is JSON.

Every response uses the same envelope, regardless of success or failure:

.. code-block:: javascript

    // list endpoints
    {"data": [...], "meta": {"page": 1, "per_page": 25, "total": 5000, "total_pages": 200}, "errors": null}
    // single-object / action endpoints
    {"data": {...}, "errors": null}
    // failure
    {"data": null, "errors": [{"message": "Cannot reduce capacity below 5 confirmed bookings."}]}

.. openapi:: specs/openapi.yaml
   :paths:
     /api/v1/events
     /api/v1/admin/users
     /api/v1/admin/users/bulk
     /api/v1/admin/events
     /api/v1/admin/events/{event_id}/bookings/{booking_id}/revoke

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
