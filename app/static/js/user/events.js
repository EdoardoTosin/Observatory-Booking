document.addEventListener("DOMContentLoaded", () => {
  initializeLegend();
  initializeEvents();
  initializeDescriptionToggles();
});

function initializeLegend() {
  const legendContent = document.getElementById("legend-content");
  const legendArrow = document.getElementById("legend-arrow");

  legendContent.classList.add("hidden", "opacity-0");
  legendArrow.style.transform = "rotate(0deg)";
}

function toggleLegend() {
  const legendContent = document.getElementById("legend-content");
  const legendArrow = document.getElementById("legend-arrow");
  const isExpanded = legendContent.classList.contains("hidden");

  if (isExpanded) {
    legendContent.classList.remove("hidden", "opacity-0");
    setTimeout(() => legendContent.classList.add("opacity-100"), 10);
    legendArrow.style.transform = "rotate(180deg)";
  } else {
    legendContent.classList.add("opacity-0");
    setTimeout(() => legendContent.classList.add("hidden"), 300);
    legendArrow.style.transform = "rotate(0deg)";
  }
}

function initializeEvents() {
  const { configTimezone, nowUtc, events } = window.eventData;
  const nowUtcDate = new Date(nowUtc);

  events.forEach((event) => {
    const startTime = new Date(event.startTime);
    const endTime = new Date(event.endTime);
    const eventDate = startTime.toLocaleDateString("en-CA", { timeZone: configTimezone });

    updateDateTimeElements(event.id, eventDate, startTime, endTime, configTimezone);

    updateBookingButton(event.id, startTime, nowUtcDate);
  });
}

function initializeDescriptionToggles() {
  document.querySelectorAll(".desc-toggle").forEach((toggle) => {
    toggle.addEventListener("change", function () {
      const arrow = this.nextElementSibling.querySelector(".desc-arrow");
      if (this.checked) {
        arrow.style.transform = "rotate(180deg)";
      } else {
        arrow.style.transform = "rotate(0deg)";
      }
    });
  });
}

function updateDateTimeElements(eventId, eventDate, startTime, endTime, timezone) {
  const dateElement = document.getElementById(`event-date-${eventId}`);
  const timeElement = document.getElementById(`event-time-${eventId}`);

  if (dateElement) {
    dateElement.textContent = eventDate;
  }

  if (timeElement) {
    timeElement.textContent = `${formatTime(startTime, timezone)} - ${formatTime(
      endTime,
      timezone
    )}`;
  }
}

function updateBookingButton(eventId, startTime, nowUtcDate) {
  const bookingButton = document.querySelector(`#event-${eventId} .btn-book-now`);

  if (bookingButton && startTime <= nowUtcDate) {
    bookingButton.disabled = true;
    bookingButton.classList.add("bg-gray-400", "cursor-not-allowed");
  }
}

function formatTime(date, timezone) {
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone,
  });
}
