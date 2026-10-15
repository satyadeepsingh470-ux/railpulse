import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, RefreshCw, CheckCircle2, QrCode, Smartphone, LogOut, Send, AlertTriangle } from 'lucide-react';

export default function WhatsAppModal({
  isOpen,
  onClose,
  whatsAppStatus,
  onReconnect,
  onDisconnect,
  onTestPing
}) {
  const [testPhone, setTestPhone] = useState('');
  const [pingSending, setPingSending] = useState(false);
  const [pingFeedback, setPingFeedback] = useState(null);

  if (!isOpen) return null;

  const isConnected = whatsAppStatus?.status === 'connected';
  const isQrReady = whatsAppStatus?.status === 'qr_ready';
  const isConnecting = whatsAppStatus?.status === 'connecting';

  const handleSendPing = async (e) => {
    e.preventDefault();
    if (!testPhone.trim()) return;
    setPingSending(true);
    setPingFeedback(null);
    try {
      const res = await onTestPing(testPhone);
      setPingFeedback({ type: 'success', msg: `Ping sent to +${res.phone || testPhone}!` });
    } catch (err) {
      setPingFeedback({ type: 'error', msg: err.message || 'Failed to send ping' });
    } finally {
      setPingSending(false);
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          transition={{ duration: 0.2 }}
          className="relative w-full max-w-lg bg-[#0F172A] border border-white/10 rounded-2xl shadow-2xl overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-slate-900/60">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400">
                <Smartphone className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white tracking-wide">
                  WhatsApp Alerts Bot
                </h3>
                <p className="text-xs text-slate-400">
                  {isConnected ? 'Device linked & operational' : 'Link your phone to receive instant PNR alerts'}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-white/5 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Body Content */}
          <div className="p-6 space-y-6">
            {isConnected ? (
              // Connected View
              <div className="space-y-5 text-center">
                <div className="inline-flex p-4 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                  <CheckCircle2 className="w-12 h-12" />
                </div>
                <div>
                  <h4 className="text-xl font-bold text-white">WhatsApp Connected!</h4>
                  <p className="text-sm text-slate-300 mt-1">
                    Linked to <span className="font-mono text-emerald-400 font-semibold">+{whatsAppStatus?.connectedUser?.phone || 'Active Device'}</span>
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    User: {whatsAppStatus?.connectedUser?.name || 'Bot Admin'}
                  </p>
                </div>

                {/* Test Ping Input */}
                <form onSubmit={handleSendPing} className="p-4 bg-slate-900/80 border border-white/10 rounded-xl space-y-3 text-left">
                  <label className="text-xs font-semibold text-slate-300 block">
                    Verify WhatsApp Notifications:
                  </label>
                  <div className="flex space-x-2">
                    <input
                      type="text"
                      placeholder="10-digit WhatsApp number"
                      value={testPhone}
                      onChange={(e) => setTestPhone(e.target.value)}
                      className="flex-1 px-3 py-2 bg-slate-950 border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-emerald-500"
                    />
                    <button
                      type="submit"
                      disabled={pingSending}
                      className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-sm font-semibold flex items-center space-x-1.5 transition"
                    >
                      <Send className="w-4 h-4" />
                      <span>{pingSending ? 'Sending...' : 'Test Ping'}</span>
                    </button>
                  </div>
                  {pingFeedback && (
                    <p className={`text-xs ${pingFeedback.type === 'success' ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {pingFeedback.msg}
                    </p>
                  )}
                </form>

                {/* Disconnect Action */}
                <div className="pt-2">
                  <button
                    onClick={onDisconnect}
                    className="inline-flex items-center space-x-2 px-4 py-2 text-xs font-semibold text-rose-400 hover:text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 rounded-lg transition"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>Unlink / Disconnect WhatsApp</span>
                  </button>
                </div>
              </div>
            ) : (
              // Disconnected / QR Ready View
              <div className="space-y-5">
                <div className="flex flex-col items-center justify-center">
                  {whatsAppStatus?.qrDataUrl ? (
                    <div className="p-3 bg-white rounded-2xl shadow-xl border-4 border-emerald-500/30">
                      <img
                        src={whatsAppStatus.qrDataUrl}
                        alt="WhatsApp QR Code"
                        className="w-56 h-56 object-contain"
                      />
                    </div>
                  ) : (
                    <div className="w-56 h-56 flex flex-col items-center justify-center p-6 bg-slate-900 border border-white/10 rounded-2xl text-slate-400">
                      <RefreshCw className={`w-8 h-8 mb-3 text-blue-400 ${isConnecting ? 'animate-spin' : ''}`} />
                      <p className="text-xs text-center">
                        {isConnecting ? 'Generating Baileys QR code...' : 'Preparing WhatsApp QR session...'}
                      </p>
                    </div>
                  )}
                </div>

                {/* Instructions Steps */}
                <div className="p-4 bg-slate-900/70 border border-white/10 rounded-xl space-y-2.5">
                  <h5 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
                    <QrCode className="w-3.5 h-3.5 text-blue-400" />
                    <span>How to connect in 10 seconds:</span>
                  </h5>
                  <ol className="text-xs text-slate-300 space-y-1.5 pl-4 list-decimal">
                    <li>Open <strong className="text-white">WhatsApp</strong> on your phone</li>
                    <li>Tap <strong className="text-white">Settings</strong> or <strong className="text-white">⋮ Menu</strong> ➔ <strong className="text-white">Linked Devices</strong></li>
                    <li>Tap <strong className="text-white">Link a Device</strong> and point your camera here</li>
                  </ol>
                </div>

                {/* Buttons */}
                <div className="flex items-center justify-between pt-2">
                  <button
                    onClick={onReconnect}
                    className="inline-flex items-center space-x-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-white/10 transition"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Regenerate QR Code</span>
                  </button>

                  <span className="text-[11px] text-slate-400 italic">
                    Simulation Mode works even without linking!
                  </span>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
