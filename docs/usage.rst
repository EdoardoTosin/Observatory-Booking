Usage Guide
===========

This guide explains how users, admins, and superadmins interact with the Observatory Booking Web App.

User Workflow
-------------

1. **Register**

   - Go to `/register`.
   - Provide name, email, and password.
   - Passwords must be 8-30 characters, with at least one uppercase, one lowercase, and one digit.
   - Name and email are AES-encrypted; passwords are hashed with bcrypt.

2. **Login**

   - Visit `/login`.
   - On success, you're redirected to `/events`.

3. **View Events**

   - Events are shown on the `/events` page.
   - Each event includes title, date, time, and weather rating.
   - Status shows if it's available, booked, full, or past.
   - Weather warnings and color-coded ratings are included.
   - Search by title, sort by date or weather rating, hide full/warned
     events, and browse a date-picker calendar to jump to a specific day -
     the calendar stays open across month navigation so you don't have to
     reopen it after each click.

   Filtering/sorting/date navigation re-fetch just the event list and
   calendar via the JSON API (``/api/v1/events``) without a full page
   reload; the same page also works with JavaScript disabled, falling
   back to plain links.

4. **Book an Event**

   - Click "Book Now" on an available event.
   - System enforces:
     - Max bookings per event (admin-configured)
     - User must not have booked already
     - No booking if the event already started

5. **Cancel a Booking**

   - If booked, click "Cancel Booking" on that event.
   - Cancellation is only allowed before the event starts.

6. **Change Password**

   - Navigate to `/change_password` from your account menu.
   - Enter current password, and a strong new password to update it.

7. **Rate Limiting**

   - Users are limited to **10 requests per 20 seconds**.
   - This applies to login, booking, cancellation, and sensitive actions.

Admin Workflow
--------------

1. **Access the Admin Dashboard**

   - URL: `/admin` (available to Admins and Superadmins)
   - Tabs: Events Calendar, User Accounts, System Settings

2. **Manage Events**

   - Add/update events using the calendar tab (scoped to the viewed month;
     prev/next navigation re-fetches via the JSON API without a reload)
   - Provide title, description, date, open/close times, max bookings
   - Weather is auto-evaluated on save
   - Use “Update Weather” to refresh forecasts for all events
   - The edit modal shows "booked / max" capacity; lowering the max
     bookings below the number of confirmed bookings is rejected with an
     explicit error
   - Revoke an individual user's booking directly from the edit modal's
     "Manage bookings" list to free up capacity (allowed even after the
     event has started, unlike a user's own self-cancel) before reducing
     the limit or deleting the event

3. **Manage Users**

   - View all non-superadmin accounts, paginated (10/25/50/100 per page)
   - Filter by name, email, role, or status; sort by ID, name, role, or status
   - Promote/demote between User and Admin
   - Block/unblock accounts
   - Superadmins can also delete users permanently
   - Select rows individually, or select every row on the page and expand
     to "select all N users matching the current filters" for a bulk
     block/unblock/role change in one action - the acting admin and any
     superadmin account are always excluded server-side regardless of
     what's selected

4. **Configure System Settings**

   - Update observatory coordinates (latitude/longitude) by dragging a
     marker on the built-in map (Leaflet + OpenStreetMap tiles) or typing
     values directly
   - Set default event times
   - Set weather suitability threshold (%)
   - Define max bookings per event
   - Choose the timezone from a curated, continent-grouped list (derived
     from the IANA database)

Superadmin Rules
----------------

- Superadmins is created from `.env` on first run.
- They cannot be demoted, blocked, or deleted.
- Only superadmins can:
  - Delete users
  - Manage other admins' privileges

Weather System
--------------

- Updates every 3 hours using Open-Meteo API
- Metrics used:
  - Cloud cover
  - Precipitation
  - Visibility
  - Dew point
- Ratings range from 0 (worst) to 100 (ideal)
- Warning icon shown if rating is below threshold
- Cached to reduce API load

Security Features
-----------------

- All data in-transit is protected (CSRF tokens, HTTPS recommended)
- Sensitive fields are encrypted (AES)
- Rate limits prevent abuse
- Passwords are hashed using bcrypt
- User sessions are secured with cookie flags
- Deleted or blocked users are auto-logged out
