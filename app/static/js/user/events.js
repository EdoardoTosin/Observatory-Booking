document.addEventListener("DOMContentLoaded", () => {
  initializeLegend();
  initializeEventSlots();
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

function initializeEventSlots() {
  const { nowUtc, slots } = window.eventData;
  const nowUtcDate = new Date(nowUtc);

  slots.forEach((slot) => {
    const startTime = new Date(slot.startTime);
    const endTime = new Date(slot.endTime);
    const eventDate = startTime.toISOString().split("T")[0];

    updateDateTimeElements(slot.id, eventDate, startTime, endTime);

    updateBookingButton(slot.id, startTime, nowUtcDate);
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

function updateDateTimeElements(slotId, eventDate, startTime, endTime) {
  const dateElement = document.getElementById(`event-date-${slotId}`);
  const timeElement = document.getElementById(`event-time-${slotId}`);

  if (dateElement) {
    dateElement.textContent = eventDate;
  }

  if (timeElement) {
    timeElement.textContent = `${formatTime(startTime)} - ${formatTime(
      endTime
    )}`;
  }
}

function updateBookingButton(slotId, startTime, nowUtcDate) {
  const bookingButton = document.querySelector(`#slot-${slotId} .btn-book-now`);

  if (bookingButton && startTime <= nowUtcDate) {
    bookingButton.disabled = true;
    bookingButton.classList.add("bg-gray-400", "cursor-not-allowed");
  }
}

function formatTime(date) {
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}
