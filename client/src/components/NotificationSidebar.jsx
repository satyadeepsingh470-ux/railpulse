import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Send,
  Trash2,
  CheckCheck,
  Check,
  Clock,
  Sparkles,
  Smartphone,
  AlertCircle
} from 'lucide-react';

export default function NotificationSidebar({
  isOpen,
  onClose,
  notifications = [],
  onClearNotifications,
  onSendTestPing
}) {
  const [testPhone, setTestPhone] = useState('9876543210');
  const [sending, setSending] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const handleTestPing = async (e) => {
    e.preventDefault();
    if (!testPhone.trim()) return;
    setSending(true);
    setFeedback(null);
    try {
      await onSendTestPing(testPhone);
      setFeedback({ type: 'success', text: `Test WhatsApp ping dispatched!` });
      setTimeout(() => setFeedback(null), 4000);
    } catch (err) {
      setFeedback({ type: 'error', text: err.message || 'Failed to send ping' });
    } finally {
      setSending(false);
    }
  };

  // Helper to format WhatsApp markdown (e.g. *bold*, _italic_) into HTML/React elements
  const formatWhatsAppText = (text) => {
    if (!text) return '';
    const lines = text.split('\n');

    return lines.map((line, idx) => {
      // Replace *text* with <strong>text</strong>
      const boldFormatted = line.replace(/\*([^*]+)\*/g, '<strong>$1</strong>');
      // Replace _text_ with <em>text</em>
      const italicFormatted = boldFormatted.replace(/_([^_]+)_/g, '<em class="text-slate-400">$1</em>');

      return (
        <span
          key={idx}
          className="block"
          dangerouslySetInnerHTML={{ __html: italicFormatted || '&nbsp;' }}
        />
      );
    });
  };

  const formatTimestamp = (dateStr) => {
    if (!dateStr) return '';
    try {
      const d = new Date(dateStr);
      return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
    } catch {
      return '';
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-sm flex justify-end">
        <motion.div
          initial={{ x: '100%' }}
          animate={{ x: 0 }}
          exit={{ x: '100%' }}
          transition={{ type: 'spring', damping: 25, stiffness: 200 }}
          className="relative w-full max-w-md bg-[#0C1322] border-l border-white/10 h-full flex flex-col shadow-2xl overflow-hidden"
        >
          {/* Header */}
          <div className="px-5 py-4 border-b border-white/10 bg-[#080E1A] flex items-center justify-between">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400">
                <Smartphone className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white flex items-center space-x-1.5">
                  <span>WhatsApp Alerts Feed</span>
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                </h3>
                <p className="text-[11px] text-slate-400">
                  Real-time log of notifications sent by bot
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-1">
              {notifications.length > 0 && (
                <button
                  onClick={onClearNotifications}
                  title="Clear Notification History"
                  className="p-1.5 text-slate-400 hover:text-rose-400 rounded-lg hover:bg-white/5 transition"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
              <button
                onClick={onClose}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-white/5 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Quick Ping Test Form */}
          <div className="p-3.5 bg-slate-900/60 border-b border-white/5">
            <form onSubmit={handleTestPing} className="space-y-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                Send Test Alert to Phone
              </span>
              <div className="flex space-x-1.5">
                <input
                  type="text"
                  placeholder="10-digit number"
                  value={testPhone}
                  onChange={(e) => setTestPhone(e.target.value)}
                  className="flex-1 px-2.5 py-1.5 bg-slate-950 border border-white/10 rounded-lg text-xs text-white focus:outline-none focus:border-blue-500 font-mono"
                />
                <button
                  type="submit"
                  disabled={sending}
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center space-x-1 transition"
                >
                  <Send className="w-3 h-3" />
                  <span>{sending ? '...' : 'Ping'}</span>
                </button>
              </div>
              {feedback && (
                <p className={`text-[11px] ${feedback.type === 'success' ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {feedback.text}
                </p>
              )}
            </form>
          </div>

          {/* WhatsApp Chat Bubbles List */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-950/40">
            {notifications.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-400">
                <Smartphone className="w-10 h-10 mb-3 text-slate-400" />
                <h4 className="text-sm font-bold text-slate-300">No Alerts Sent Yet</h4>
                <p className="text-xs text-slate-400 mt-1 max-w-xs">
                  Click <strong className="text-white">"Simulate WL Drop"</strong> on any ticket card to trigger a live WhatsApp notification preview!
                </p>
              </div>
            ) : (
              notifications.map((notif) => {
                const isDelivered = notif.status === 'DELIVERED';
                const isSimulated = notif.status === 'SIMULATED';

                return (
                  <motion.div
                    key={notif.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex flex-col items-end"
                  >
                    {/* Realistic WhatsApp Outgoing Bubble */}
                    <div className="max-w-[88%] bg-[#005C4B] text-slate-100 rounded-2xl rounded-tr-sm p-3.5 shadow-md border border-emerald-500/20 text-xs font-sans leading-relaxed">
                      
                      {/* Formatted Message Body */}
                      <div className="text-[12px] font-sans">
                        {formatWhatsAppText(notif.message)}
                      </div>

                      {/* Bubble Footer */}
                      <div className="flex items-center justify-end space-x-1.5 mt-2 text-[10px] text-emerald-200/70 pt-1 border-t border-emerald-600/30">
                        {isSimulated && (
                          <span className="px-1.5 py-0.2 rounded bg-emerald-900/60 text-emerald-300 text-[9px] font-bold">
                            MOCK
                          </span>
                        )}
                        <span>{formatTimestamp(notif.created_at)}</span>
                        {isDelivered ? (
                          <CheckCheck className="w-3.5 h-3.5 text-cyan-300" title="Delivered to WhatsApp" />
                        ) : (
                          <Check className="w-3.5 h-3.5 text-emerald-300" title="Sent" />
                        )}
                      </div>

                    </div>

                    <span className="text-[9px] text-slate-400 mt-1 font-mono pr-1">
                      To: +{notif.phone || '919876543210'}
                    </span>
                  </motion.div>
                );
              })
            )}
          </div>

        </motion.div>
      </div>
    </AnimatePresence>
  );
}
