Usage Guide
===========

This guide explains how users, admins, and superadmins interact with the Observatory Booking Web App.

User Workflow
-------------

1. **Register**

   - Go to `/register`.
   - Provide name, email, and password.
   - Passwords must be 8–30 characters, with at least one uppercase, one lowercase, and one digit.
   - Name and email are AES-encrypted; passwords are hashed with bcrypt.

2. **Login**

   - Visit `/login`.
   - On success, you're redirected to `/events`.

3. **View Events**

   - Events are shown on the `/events` page.
   - Each event includes title, date, time, and weather rating.
   - Status shows if it's available, booked, full, or past.
   - Weather warnings and color-coded ratings are included.

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

   - Add/update events using the calendar tab
   - Provide title, description, date, open/close times, max bookings
   - Weather is auto-evaluated on save
   - Use “Update Weather” to refresh forecasts for all events

3. **Manage Users**

   - View all non-superadmin accounts
   - Filter by name, email, role, or status
   - Promote/demote between User and Admin
   - Block/unblock accounts
   - Superadmins can also delete users permanently

4. **Configure System Settings**

   - Update observatory coordinates (latitude/longitude)
   - Set default event times
   - Set weather suitability threshold (%)
   - Define max bookings per event
   - Define timezone (IANA format)

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
