const API_BASE = import.meta.env.VITE_API_BASE || "/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.message || "请求失败");
  }
  return data;
}

export function getPackages() {
  return request("/packages");
}

export function getPhotographers() {
  return request("/photographers");
}

export function getAvailability(photographerId, date) {
  return request(`/photographers/${photographerId}/availability?date=${date}`);
}

export function getBookings() {
  return request("/bookings");
}

export function createBooking(payload) {
  return request("/bookings", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function submitReschedule(bookingId, payload) {
  return request(`/bookings/${bookingId}/reschedule`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getReschedules() {
  return request("/bookings/reschedules");
}

export function confirmReschedule(requestId) {
  return request(`/bookings/reschedules/${requestId}/confirm`, {
    method: "PUT",
  });
}

export function rejectReschedule(requestId, reason = "") {
  return request(`/bookings/reschedules/${requestId}/reject`, {
    method: "PUT",
    body: JSON.stringify({ reason }),
  });
}

export function getDeliveries() {
  return request("/deliveries");
}

export function getDelivery(code) {
  return request(`/deliveries/${code}`);
}

export function saveSelection(payload) {
  return request("/selections", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
