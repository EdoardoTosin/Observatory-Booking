const config = window.CALENDAR_CONFIG || {
  defaultOpeningTime: "17:00",
  defaultClosingTime: "22:00",
  maxBookingsPerEvent: 10,
  timezone: "UTC",
  year: new Date().getFullYear(),
  month: new Date().getMonth() + 1,
};

// Tracked as plain (year, month) integers, not a JS Date object: a Date
// mixes the browser's local timezone with the observatory's configured
// timezone in ways that can shift the grid by a day around DST/month edges.
// The server resolves the initial (year, month) - see admin_dashboard.py's
// _resolve_calendar_month - so this never needs its own "today" fallback.
let currentYear = config.year;
let currentMonth = config.month;

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function renderCalendar() {
  const calendarGrid = document.getElementById("calendarGrid");
  if (!calendarGrid) return;
  calendarGrid.innerHTML = "";

  const firstDay = new Date(currentYear, currentMonth - 1, 1);
  const daysInMonth = new Date(currentYear, currentMonth, 0).getDate();
  const startDay = firstDay.getDay();

  const currentMonthEl = document.getElementById("currentMonth");
  if (currentMonthEl) {
    currentMonthEl.textContent = `${MONTH_NAMES[currentMonth - 1]} ${currentYear}`;
  }

  const todayStr = new Date().toLocaleDateString("en-CA", {
    timeZone: config.timezone,
  });

  for (let i = 0; i < startDay; i++) {
    calendarGrid.appendChild(createEmptyDay());
  }

  for (let day = 1; day <= daysInMonth; day++) {
    const dayStr = `${currentYear}-${String(currentMonth).padStart(2, "0")}-${String(
      day
    ).padStart(2, "0")}`;

    const eventForDay =
      window.events && window.events.find((e) => e.effective_date === dayStr);

    const dayElement = document.createElement("div");
    dayElement.className = "text-center p-2 rounded-lg";
    dayElement.textContent = day;

    if (dayStr < todayStr) {
      dayElement.classList.add(
        "text-gray-400",
        "cursor-not-allowed",
        "opacity-50"
      );
    } else if (eventForDay) {
      dayElement.classList.add(
        "border",
        "bg-green-200",
        "dark:bg-green-700",
        "hover:bg-green-300",
        "dark:hover:bg-green-600",
        "cursor-pointer"
      );
      dayElement.addEventListener("click", () =>
        openEventModal(dayStr, eventForDay)
      );
    } else {
      dayElement.classList.add(
        "border",
        "bg-white",
        "dark:bg-gray-800",
        "hover:bg-gray-100",
        "dark:hover:bg-gray-700",
        "cursor-pointer"
      );
      dayElement.addEventListener("click", () => openEventModal(dayStr));
    }

    calendarGrid.appendChild(dayElement);
  }
}

function createEmptyDay() {
  const emptyDay = document.createElement("div");
  emptyDay.className = "text-center p-2";
  return emptyDay;
}

function openEventModal(dateStr, event = null) {
  const eventDateInput = document.getElementById("eventDate");
  if (eventDateInput) eventDateInput.value = dateStr;

  if (event) {
    document.getElementById("eventId").value = event.id;

    document.getElementById("openingTime").value = event.opening_time;
    document.getElementById("closingTime").value = event.closing_time;

    document.getElementById("maxBookings").value = event.max_bookings;
    document.getElementById("maxBookings").min = event.num_bookings;
    document.getElementById("eventTitle").value = event.title || "";
    document.getElementById("eventDescription").value = event.description || "";

    document.getElementById("weatherRatingDiv").classList.remove("hidden");
    document.getElementById("weatherRating").value = isNaN(event.weather_rating)
      ? "Unknown"
      : Math.round(event.weather_rating);

    renderCapacityStatus(event.num_bookings, event.max_bookings);
    renderBookedUsersList(event.id, event.bookings || []);
    document.getElementById("manageBookingsDiv").classList.remove("hidden");

    document.getElementById("modalTitle").textContent = "Modify Event";
    document.getElementById("deleteButton").classList.remove("hidden");
    document.getElementById("confirmButton").textContent = "Edit";
  } else {
    document.getElementById("eventId").value = "";
    document.getElementById("eventTitle").value = "";
    document.getElementById("eventDescription").value = "";

    document.getElementById("openingTime").value = config.defaultOpeningTime;
    document.getElementById("closingTime").value = config.defaultClosingTime;

    document.getElementById("maxBookings").value = config.maxBookingsPerEvent;
    document.getElementById("maxBookings").min = 1;

    document.getElementById("weatherRatingDiv").classList.add("hidden");
    document.getElementById("manageBookingsDiv").classList.add("hidden");
    document.getElementById("capacityStatus").classList.add("hidden");

    document.getElementById("modalTitle").textContent = "Create Event";
    document.getElementById("deleteButton").classList.add("hidden");
    document.getElementById("confirmButton").textContent = "Create";
  }

  document.getElementById("eventModal").classList.remove("hidden");
}

function renderCapacityStatus(numBookings, maxBookings) {
  const status = document.getElementById("capacityStatus");
  if (!status) return;
  status.textContent = `${numBookings} / ${maxBookings} booked`;
  status.classList.remove("hidden");
}

function renderBookedUsersList(eventId, bookings) {
  const list = document.getElementById("bookedUsersList");
  if (!list) return;
  list.innerHTML = "";

  if (bookings.length === 0) {
    const empty = document.createElement("li");
    empty.className = "p-2 text-gray-500 dark:text-gray-400 text-xs";
    empty.textContent = "No bookings yet.";
    list.appendChild(empty);
    return;
  }

  bookings.forEach((booking) => {
    const item = document.createElement("li");
    item.className = "flex items-center justify-between p-2";
    item.dataset.bookingId = booking.booking_id;

    const info = document.createElement("span");
    info.className = "truncate mr-2";
    info.textContent = `${booking.name} (${booking.email})`;
    item.appendChild(info);

    const revokeButton = document.createElement("button");
    revokeButton.type = "button";
    revokeButton.className =
      "shrink-0 text-red-600 dark:text-red-400 hover:underline text-xs";
    revokeButton.textContent = "Revoke";
    revokeButton.addEventListener("click", () =>
      revokeBooking(eventId, booking.booking_id)
    );
    item.appendChild(revokeButton);

    list.appendChild(item);
  });
}

async function revokeBooking(eventId, bookingId) {
  if (!confirm("Revoke this user's booking? This cannot be undone.")) return;
  try {
    const result = await apiFetch(
      `/api/v1/admin/events/${eventId}/bookings/${bookingId}/revoke`,
      { method: "POST" }
    );
    const { num_bookings: numBookings, bookings } = result.data;

    renderBookedUsersList(eventId, bookings);
    const maxBookings = document.getElementById("maxBookings").value;
    renderCapacityStatus(numBookings, maxBookings);
    document.getElementById("maxBookings").min = numBookings;

    const eventInList = window.events && window.events.find((e) => e.id === eventId);
    if (eventInList) {
      eventInList.num_bookings = numBookings;
      eventInList.bookings = bookings;
    }
    showToast("Booking revoked.", "success");
  } catch (error) {
    showToast(error.message || "Failed to revoke booking.", "error");
  }
}

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeEventModal();
  }
});

function closeEventModal() {
  const modal = document.getElementById("eventModal");
  if (!modal.classList.contains("hidden")) {
    modal.classList.add("hidden");
  }
}

function deleteEvent() {
  if (confirm("Are you sure you want to delete this event?")) {
    const rawId = document.getElementById("eventId").value;
    const eventId = parseInt(rawId, 10);
    if (!Number.isInteger(eventId) || eventId <= 0) {
      return;
    }
    const deleteForm = document.getElementById("deleteForm");
    deleteForm.action = "/admin/delete_event/" + eventId;
    deleteForm.submit();
  }
}

async function goToMonth(year, month) {
  try {
    const result = await apiFetch(
      `/api/v1/admin/events?year=${year}&month=${month}`
    );
    currentYear = result.meta.year;
    currentMonth = result.meta.month;
    window.events = result.data;

    document.getElementById("formMonth").value = currentMonth;
    document.getElementById("formYear").value = currentYear;
    const deleteFormMonth = document.querySelector('#deleteForm input[name="month"]');
    const deleteFormYear = document.querySelector('#deleteForm input[name="year"]');
    if (deleteFormMonth) deleteFormMonth.value = currentMonth;
    if (deleteFormYear) deleteFormYear.value = currentYear;

    renderCalendar();
  } catch (error) {
    showToast(error.message || "Failed to load events for that month.", "error");
  }
}

function previousMonth() {
  const month = currentMonth === 1 ? 12 : currentMonth - 1;
  const year = currentMonth === 1 ? currentYear - 1 : currentYear;
  goToMonth(year, month);
}

function nextMonth() {
  const month = currentMonth === 12 ? 1 : currentMonth + 1;
  const year = currentMonth === 12 ? currentYear + 1 : currentYear;
  goToMonth(year, month);
}

renderCalendar();

window.previousMonth = previousMonth;
window.nextMonth = nextMonth;
window.openEventModal = openEventModal;
window.closeEventModal = closeEventModal;
window.deleteEvent = deleteEvent;
