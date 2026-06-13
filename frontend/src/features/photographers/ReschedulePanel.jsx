import { CalendarDays, Clock, RefreshCw, CheckCircle, XCircle, Send } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  confirmReschedule,
  getAvailability,
  getBookings,
  getReschedules,
  rejectReschedule,
  submitReschedule,
} from "../../api/client";
import { SectionHeader } from "../../components/SectionHeader";

function statusBadge(status) {
  const map = {
    待确认: "badge-pending",
    改期中: "badge-rescheduling",
    已确认: "badge-confirmed",
    已拒绝: "badge-rejected",
  };
  return <span className={`status-badge ${map[status] || ""}`}>{status}</span>;
}

export function ReschedulePanel({ packages, photographers, onBookingsChange }) {
  const [bookings, setBookings] = useState([]);
  const [reschedules, setReschedules] = useState([]);
  const [selectedBookingId, setSelectedBookingId] = useState("");
  const [newDate, setNewDate] = useState("");
  const [newTime, setNewTime] = useState("");
  const [reason, setReason] = useState("");
  const [slots, setSlots] = useState([]);
  const [status, setStatus] = useState("");
  const [statusType, setStatusType] = useState("info");
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchData = () => {
    Promise.all([getBookings(), getReschedules()])
      .then(([bookingData, rescheduleData]) => {
        setBookings(bookingData);
        setReschedules(rescheduleData);
        if (onBookingsChange) onBookingsChange(bookingData);
      })
      .catch(() => setStatus("加载预约数据失败"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchData();
  }, []);

  const selectedBooking = useMemo(
    () => bookings.find((b) => b.id === selectedBookingId),
    [bookings, selectedBookingId],
  );

  const selectedPhotographer = useMemo(
    () => photographers.find((p) => p.id === selectedBooking?.photographerId),
    [selectedBooking, photographers],
  );

  const pendingReschedule = useMemo(
    () =>
      reschedules.find(
        (r) => r.bookingId === selectedBookingId && r.status === "待确认",
      ),
    [reschedules, selectedBookingId],
  );

  useEffect(() => {
    if (!selectedPhotographer || !newDate) {
      setSlots([]);
      return;
    }
    getAvailability(selectedPhotographer.id, newDate)
      .then((data) => setSlots(data.slots))
      .catch(() => setSlots([]));
  }, [selectedPhotographer, newDate]);

  const findPackage = (packageId) => packages.find((p) => p.id === packageId);
  const findPhotographer = (photographerId) =>
    photographers.find((p) => p.id === photographerId);

  function resetForm() {
    setNewDate("");
    setNewTime("");
    setReason("");
    setSlots([]);
  }

  function selectBooking(bookingId) {
    setSelectedBookingId(bookingId);
    resetForm();
    setStatus("");
  }

  function updateStatus(message, type = "info") {
    setStatus(message);
    setStatusType(type);
  }

  async function handleSubmitReschedule(event) {
    event.preventDefault();
    if (!selectedBooking || !newDate || !newTime) return;

    setSubmitting(true);
    updateStatus("", "info");

    try {
      const result = await submitReschedule(selectedBooking.id, {
        newDate,
        newTime,
        reason,
      });
      updateStatus(
        `改期申请已提交：${result.request.oldDate} ${result.request.oldTime} → ${result.request.newDate} ${result.request.newTime}，当前状态：${result.booking.status}。`,
        "success",
      );
      resetForm();
      fetchData();
    } catch (error) {
      updateStatus(error.message, "error");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleConfirm(requestId) {
    try {
      await confirmReschedule(requestId);
      updateStatus("改期已确认，预约档期已更新。", "success");
      fetchData();
    } catch (error) {
      updateStatus(error.message, "error");
    }
  }

  async function handleReject(requestId) {
    try {
      await rejectReschedule(requestId, "档期冲突");
      updateStatus("改期已拒绝。", "success");
      fetchData();
    } catch (error) {
      updateStatus(error.message, "error");
    }
  }

  return (
    <section className="section reschedule-section" id="reschedule">
      <SectionHeader
        eyebrow="改期申请管理"
        title="申请改期与确认档期"
        description="客户可选择已有预约并提交新档期，改期申请将进入待确认状态，确认后正式更新预约信息。"
      />

      <div className="reschedule-layout">
        <div className="booking-list">
          <h3 className="panel-title">我的预约</h3>
          {loading ? (
            <div className="empty-state">加载中...</div>
          ) : bookings.length === 0 ? (
            <div className="empty-state">暂无预约记录</div>
          ) : (
            <div className="summary-list">
              {bookings.map((booking) => {
                const pkg = findPackage(booking.packageId);
                const photographer = findPhotographer(booking.photographerId);
                return (
                  <button
                    key={booking.id}
                    className={`summary-item booking-summary-item ${selectedBookingId === booking.id ? "active" : ""}`}
                    onClick={() => selectBooking(booking.id)}
                    type="button"
                  >
                    <div>
                      <strong>
                        {pkg?.name || booking.packageId} · {photographer?.name || booking.photographerId}
                      </strong>
                      <span>
                        <CalendarDays size={14} /> {booking.date}
                        <Clock size={14} /> {booking.time}
                      </span>
                      <small>
                        客户：{booking.clientName} · {booking.phone}
                      </small>
                    </div>
                    <div>{statusBadge(booking.status)}</div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="reschedule-main">
          {!selectedBooking ? (
            <div className="booking-form">
              <div className="empty-state">请从左侧选择一个预约以申请改期</div>
            </div>
          ) : (
            <>
              <div className="booking-form reschedule-form">
                <h3 className="panel-title">
                  <RefreshCw size={20} />
                  申请改期
                </h3>

                <div className="current-slot">
                  <span className="slot-label">当前档期</span>
                  <strong>
                    <CalendarDays size={16} /> {selectedBooking.date}
                    <Clock size={16} /> {selectedBooking.time}
                  </strong>
                </div>

                {pendingReschedule ? (
                  <div className="pending-notice">
                    <CheckCircle size={18} />
                    <div>
                      <strong>已有待确认的改期申请</strong>
                      <small>
                        申请档期：{pendingReschedule.newDate} {pendingReschedule.newTime}
                        {pendingReschedule.reason && ` · 原因：${pendingReschedule.reason}`}
                      </small>
                    </div>
                  </div>
                ) : selectedBooking.status === "已取消" ? (
                  <div className="empty-state">已取消的预约无法改期</div>
                ) : (
                  <form onSubmit={handleSubmitReschedule}>
                    <div className="form-grid">
                      <label>
                        新拍摄日期
                        <select
                          value={newDate}
                          onChange={(e) => {
                            setNewDate(e.target.value);
                            setNewTime("");
                          }}
                          required
                        >
                          <option value="">请选择日期</option>
                          {selectedPhotographer?.availableDates.map((date) => (
                            <option value={date} key={date}>
                              {date}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        改期原因
                        <input
                          value={reason}
                          onChange={(e) => setReason(e.target.value)}
                          placeholder="选填，例如：临时有事"
                        />
                      </label>
                    </div>

                    <div className="slot-panel">
                      <span>
                        <CalendarDays size={18} />
                        可选新时间
                      </span>
                      <div className="slot-list">
                        {slots.length ? (
                          slots.map((slot) => (
                            <button
                              className={newTime === slot ? "slot active" : "slot"}
                              key={slot}
                              onClick={() => setNewTime(slot)}
                              type="button"
                            >
                              {slot}
                            </button>
                          ))
                        ) : (
                          <small>选择日期后显示可用时间</small>
                        )}
                      </div>
                    </div>

                    <button
                      className="button button-primary"
                      disabled={submitting || !newDate || !newTime}
                      type="submit"
                    >
                      <Send size={18} />
                      {submitting ? "提交中" : "提交改期申请"}
                    </button>
                  </form>
                )}

                {status && (
                  <div className={`notice notice-${statusType}`}>{status}</div>
                )}
              </div>

              {reschedules.filter((r) => r.bookingId === selectedBookingId).length > 0 && (
                <div className="booking-form reschedule-history">
                  <h3 className="panel-title">改期记录</h3>
                  <div className="reschedule-list">
                    {reschedules
                      .filter((r) => r.bookingId === selectedBookingId)
                      .map((req) => (
                        <div key={req.id} className="reschedule-item">
                          <div className="reschedule-info">
                            <div className="reschedule-slot">
                              <span>
                                <CalendarDays size={14} /> {req.oldDate}
                                <Clock size={14} /> {req.oldTime}
                              </span>
                              <em>→</em>
                              <span>
                                <CalendarDays size={14} /> {req.newDate}
                                <Clock size={14} /> {req.newTime}
                              </span>
                            </div>
                            <small>申请于 {req.createdAt}</small>
                            {req.reason && <small>原因：{req.reason}</small>}
                            {req.rejectReason && (
                              <small className="reject-reason">拒绝原因：{req.rejectReason}</small>
                            )}
                          </div>
                          <div className="reschedule-actions">
                            {statusBadge(req.status)}
                            {req.status === "待确认" && (
                              <div className="action-buttons">
                                <button
                                  className="button button-primary button-sm"
                                  onClick={() => handleConfirm(req.id)}
                                  type="button"
                                >
                                  <CheckCircle size={14} />
                                  确认
                                </button>
                                <button
                                  className="button button-danger button-sm"
                                  onClick={() => handleReject(req.id)}
                                  type="button"
                                >
                                  <XCircle size={14} />
                                  拒绝
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
