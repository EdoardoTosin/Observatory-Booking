const config = window.CALENDAR_CONFIG || {
  defaultOpeningTime: "17:00",
  defaultClosingTime: "22:00",
  maxBookingsPerEvent: 10,
  timezone: "UTC",
};

let currentDate = new Date();

function renderCalendar(date) {
  const calendarGrid = document.getElementById("calendarGrid");
  if (!calendarGrid) return;
  calendarGrid.innerHTML = "";

  const year = date.getFullYear();
  const month = date.getMonth();
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const daysInMonth = lastDay.getDate();
  const startDay = firstDay.getDay();

  const currentMonthEl = document.getElementById("currentMonth");
  if (currentMonthEl) {
    currentMonthEl.textContent = date.toLocaleString("default", {
      month: "long",
      year: "numeric",
    });
  }

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  for (let i = 0; i < startDay; i++) {
    calendarGrid.appendChild(createEmptyDay());
  }

  for (let day = 1; day <= daysInMonth; day++) {
    const cellDate = new Date(year, month, day);
    const dayStr = cellDate.toLocaleDateString("en-CA", {
      timeZone: config.timezone,
    });

    const eventForDay =
      window.events &&
      window.events.find((e) => {
        const eventDate = new Date(e.effective_date + "T00:00:00Z");
        const eventLocalDate = eventDate.toLocaleDateString("en-CA", {
          timeZone: config.timezone,
        });
        return eventLocalDate === dayStr;
      });

    const dayElement = document.createElement("div");
    dayElement.className = "text-center p-2 rounded-lg";
    dayElement.textContent = day;

    if (cellDate < today) {
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
        openEventModal(cellDate, eventForDay)
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
      dayElement.addEventListener("click", () => openEventModal(cellDate));
    }

    calendarGrid.appendChild(dayElement);
  }
}

function createEmptyDay() {
  const emptyDay = document.createElement("div");
  emptyDay.className = "text-center p-2";
  return emptyDay;
}

function openEventModal(date, event = null) {
  const formattedDate = date.toLocaleDateString("en-CA", {
    timeZone: config.timezone,
  });
  const eventDateInput = document.getElementById("eventDate");
  if (eventDateInput) eventDateInput.value = formattedDate;

  if (event) {
    document.getElementById("eventId").value = event.id;

    const openingDateUTC = new Date(`2000-01-01T${event.opening_time}Z`);
    const closingDateUTC = new Date(`2000-01-01T${event.closing_time}Z`);
    document.getElementById("openingTime").value =
      openingDateUTC.toLocaleTimeString("en-GB", {
        hour12: false,
        timeZone: config.timezone,
        hour: "2-digit",
        minute: "2-digit",
      });
    document.getElementById("closingTime").value =
      closingDateUTC.toLocaleTimeString("en-GB", {
        hour12: false,
        timeZone: config.timezone,
        hour: "2-digit",
        minute: "2-digit",
      });

    document.getElementById("maxBookings").value = event.max_bookings;
    document.getElementById("eventTitle").value = event.title || "";
    document.getElementById("eventDescription").value = event.description || "";

    document.getElementById("weatherRatingDiv").classList.remove("hidden");
    document.getElementById("weatherRating").value = isNaN(event.weather_rating)
      ? "Unknown"
      : Math.round(event.weather_rating);

    document.getElementById("bookedUsersDiv").classList.remove("hidden");
    document.getElementById("bookedUsers").value = event.num_bookings;

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

    document.getElementById("weatherRatingDiv").classList.add("hidden");
    document.getElementById("bookedUsersDiv").classList.add("hidden");

    document.getElementById("modalTitle").textContent = "Create Event";
    document.getElementById("deleteButton").classList.add("hidden");
    document.getElementById("confirmButton").textContent = "Create";
  }

  document.getElementById("eventModal").classList.remove("hidden");
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
    const eventId = document.getElementById("eventId").value;
    const deleteForm = document.getElementById("deleteForm");
    deleteForm.action = "/admin/delete_event/" + eventId;
    deleteForm.submit();
  }
}

function previousMonth() {
  currentDate.setMonth(currentDate.getMonth() - 1);
  renderCalendar(currentDate);
}

function nextMonth() {
  currentDate.setMonth(currentDate.getMonth() + 1);
  renderCalendar(currentDate);
}

renderCalendar(currentDate);

window.previousMonth = previousMonth;
window.nextMonth = nextMonth;
window.openEventModal = openEventModal;
window.closeEventModal = closeEventModal;
window.deleteEvent = deleteEvent;
