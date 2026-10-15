import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
import HeroQuickAdd from './components/HeroQuickAdd';
import TicketCard from './components/TicketCard';
import WhatsAppModal from './components/WhatsAppModal';
import NotificationSidebar from './components/NotificationSidebar';
import {
  Train,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Zap,
  Smartphone,
  ShieldCheck,
  RefreshCw,
  Info
} from 'lucide-react';

export default function App() {
  const [tickets, setTickets] = useState([]);
  const [systemStatus, setSystemStatus] = useState({
    mode: 'simulation',
    hasRapidApiKey: false,
    hasGeminiApiKey: false,
    irctc: { inMaintenance: false, statusLabel: 'Operational' }
  });
  const [whatsAppStatus, setWhatsAppStatus] = useState({
    status: 'disconnected',
    qrDataUrl: null,
    connectedUser: null
  });
  const [notifications, setNotifications] = useState([]);
  const [isWhatsAppModalOpen, setIsWhatsAppModalOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // Fetch all tickets
  const fetchTickets = useCallback(async () => {
    try {
      const res = await fetch('/api/pnrs');
      const data = await res.json();
      if (data.success) {
        setTickets(data.data || []);
      }
    } catch (err) {
      console.error('Failed to fetch tickets:', err);
    }
  }, []);

  // Fetch system status
  const fetchSystemStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/system/status');
      const data = await res.json();
      if (data.success) {
        setSystemStatus(data.data);
        if (data.data.whatsapp) {
          setWhatsAppStatus(data.data.whatsapp);
        }
      }
    } catch (err) {
      console.error('Failed to fetch system status:', err);
    }
  }, []);

  // Fetch notifications
  const fetchNotifications = useCallback(async () => {
    try {
      const res = await fetch('/api/notifications');
      const data = await res.json();
      if (data.success) {
        setNotifications(data.data || []);
      }
    } catch (err) {
      console.error('Failed to fetch notifications:', err);
    }
  }, []);

  // Initialize data and real-time SSE listener
  useEffect(() => {
    fetchTickets();
    fetchSystemStatus();
    fetchNotifications();

    // Setup Server-Sent Events (SSE) for live updates
    const eventSource = new EventSource('/api/stream');

    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);

        if (payload.type === 'WHATSAPP_STATUS') {
          setWhatsAppStatus(payload.data);
        } else if (payload.type === 'IRCTC_STATUS') {
          setSystemStatus((prev) => ({ ...prev, irctc: payload.data }));
        } else if (
          payload.type === 'PNR_UPDATED' ||
          payload.type === 'PNR_ADDED' ||
          payload.type === 'PNR_DELETED' ||
          payload.type === 'PNR_CONFIRMED'
        ) {
          fetchTickets();
        } else if (payload.type === 'NEW_NOTIFICATION') {
          setNotifications((prev) => [payload.data, ...prev]);
        } else if (payload.type === 'SYSTEM_MODE_CHANGED') {
          setSystemStatus((prev) => ({ ...prev, mode: payload.mode }));
        }
      } catch (err) {
        console.error('SSE parse error:', err);
      }
    };

    eventSource.onerror = () => {
      // Reconnect handled automatically by EventSource
    };

    return () => {
      eventSource.close();
    };
  }, [fetchTickets, fetchSystemStatus, fetchNotifications]);

  // Action: Add PNR
  const handleAddPnr = async (pnr, phone, ticketDetails = null) => {
    setIsLoading(true);
    try {
      const payload = { pnr, phone, ...(ticketDetails || {}) };
      const res = await fetch('/api/pnrs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok || !data.success) throw new Error(data.detail || data.error || 'Failed to add PNR');

      await fetchTickets();
      showToast(`PNR ${pnr} added to live tracking! Alerts active.`);
    } finally {
      setIsLoading(false);
    }
  };

  // Action: Upload ticket screenshot / PDF
  const handleUploadTicket = async (file) => {
    const formData = new FormData();
    formData.append('ticket', file);

    const res = await fetch('/api/upload-ticket', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || data.error || 'Failed to extract ticket');
    return data.data;
  };

  // Action: Simulate WL Drop
  const handleSimulateDrop = async (pnr) => {
    const res = await fetch(`/api/pnrs/${pnr}/simulate-drop`, { method: 'POST' });
    const data = await res.json();
    if (!data.success) throw new Error(data.error || 'Drop simulation failed');
    await fetchTickets();
    showToast(`⚡ Waitlist dropped by ${data.movement} berths! WhatsApp alert sent.`, 'success');
  };

  // Action: Simulate CNF
  const handleSimulateConfirm = async (pnr) => {
    const res = await fetch(`/api/pnrs/${pnr}/simulate-confirm`, { method: 'POST' });
    const data = await res.json();
    if (!data.success) throw new Error(data.error || 'Confirm simulation failed');
    await fetchTickets();
    showToast(`🎉 Ticket Confirmed! Seat allocated.`, 'success');
  };

  // Action: Force Check
  const handleForceCheck = async (pnr) => {
    const res = await fetch(`/api/pnrs/${pnr}/check`, { method: 'POST' });
    const data = await res.json();
    if (!data.success) throw new Error(data.error || 'Check failed');
    await fetchTickets();
    showToast(`PNR ${pnr} verified. Status up-to-date.`);
  };

  // Action: Toggle tracking status
  const handleToggleStatus = async (pnr) => {
    const res = await fetch(`/api/pnrs/${pnr}/status`, { method: 'PATCH' });
    const data = await res.json();
    if (data.success) {
      await fetchTickets();
      showToast(`PNR ${pnr} tracking ${data.status.toLowerCase()}.`);
    }
  };

  // Action: Delete PNR
  const handleDeleteTicket = async (pnr) => {
    if (!window.confirm(`Are you sure you want to stop tracking PNR ${pnr}?`)) return;
    const res = await fetch(`/api/pnrs/${pnr}`, { method: 'DELETE' });
    const data = await res.json();
    if (data.success) {
      await fetchTickets();
      showToast(`PNR ${pnr} removed.`);
    }
  };

  // Action: WhatsApp Reconnect
  const handleWhatsAppReconnect = async () => {
    await fetch('/api/whatsapp/reconnect', { method: 'POST' });
    showToast('Regenerating WhatsApp QR Code...');
  };

  // Action: WhatsApp Disconnect
  const handleWhatsAppDisconnect = async () => {
    await fetch('/api/whatsapp/disconnect', { method: 'POST' });
    showToast('WhatsApp unlinked.');
  };

  // Action: Test Ping
  const handleTestPing = async (phone) => {
    const res = await fetch('/api/whatsapp/test-ping', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone })
    });
    const data = await res.json();
    if (!data.success) throw new Error(data.error || 'Ping failed');
    return data;
  };

  // Action: Toggle Mode
  const handleToggleMode = async () => {
    const newMode = systemStatus.mode === 'simulation' ? 'live' : 'simulation';
    const res = await fetch('/api/system/mode', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: newMode })
    });
    const data = await res.json();
    if (data.success) {
      setSystemStatus((prev) => ({ ...prev, mode: newMode }));
      showToast(
        newMode === 'simulation'
          ? 'Switched to Simulation Mode (100% Free / Zero API Cost)'
          : 'Switched to Live RapidAPI Mode',
        'info'
      );
    }
  };

  // Action: Toggle Maintenance Window Override
  const handleToggleMaintenance = async () => {
    const res = await fetch('/api/system/toggle-maintenance', { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      setSystemStatus((prev) => ({ ...prev, irctc: data.data }));
      showToast(
        data.data.inMaintenance
          ? 'IRCTC Maintenance simulated (Auto-polling paused)'
          : 'IRCTC Servers set to operational',
        'info'
      );
    }
  };

  // Action: Clear Notifications
  const handleClearNotifications = async () => {
    await fetch('/api/notifications', { method: 'DELETE' });
    setNotifications([]);
    showToast('Alert feed history cleared.');
  };

  return (
    <div className="min-h-screen bg-[#080C14] text-slate-100 flex flex-col font-sans">
      
      {/* Toast Notification Alert */}
      {toast && (
        <div className="fixed top-20 right-6 z-50 flex items-center space-x-2 px-4 py-3 rounded-xl bg-slate-900 border border-white/10 shadow-2xl text-xs font-semibold animate-slide-in">
          {toast.type === 'error' ? (
            <AlertCircle className="w-4 h-4 text-rose-400" />
          ) : toast.type === 'info' ? (
            <Info className="w-4 h-4 text-blue-400" />
          ) : (
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          )}
          <span className="text-white">{toast.message}</span>
        </div>
      )}

      {/* Top Navigation */}
      <Navbar
        systemStatus={systemStatus}
        whatsAppStatus={whatsAppStatus}
        onOpenWhatsAppModal={() => setIsWhatsAppModalOpen(true)}
        onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
        notificationCount={notifications.length}
        onToggleMode={handleToggleMode}
        onToggleMaintenance={handleToggleMaintenance}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-10">
        
        {/* Hero Section & Quick Add Bar */}
        <HeroQuickAdd
          onAddPnr={handleAddPnr}
          onUploadTicket={handleUploadTicket}
          isLoading={isLoading}
        />

        {/* Active Tracked Tickets Grid */}
        <section className="space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="flex items-center space-x-2.5">
                <h2 className="text-xl font-bold text-white tracking-wide">
                  Active Tracked Journeys
                </h2>
                <span className="px-2.5 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-mono font-bold">
                  {tickets.length} {tickets.length === 1 ? 'ticket' : 'tickets'}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Automatic background polling with strict state diffing & instant WhatsApp movement dispatches
              </p>
            </div>

            {/* Quick action info banner */}
            <div className="hidden sm:flex items-center space-x-2 text-xs text-slate-400 bg-slate-900/60 border border-white/5 px-3 py-1.5 rounded-xl">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              <span>Click <strong>"Simulate WL Drop"</strong> on any ticket to test live WhatsApp alerts immediately</span>
            </div>
          </div>

          {/* Tickets List */}
          {tickets.length === 0 ? (
            <div className="p-12 text-center rounded-2xl bg-slate-900/40 border border-white/5 space-y-3">
              <Train className="w-12 h-12 text-slate-400 mx-auto" />
              <h3 className="text-base font-bold text-slate-300">No PNRs currently tracked</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Enter your 10-digit PNR in the quick-add bar above or click one of the quick test presets to start tracking your waitlist movement!
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-6">
              {tickets.map((ticket) => (
                <TicketCard
                  key={ticket.pnr}
                  ticket={ticket}
                  onSimulateDrop={handleSimulateDrop}
                  onSimulateConfirm={handleSimulateConfirm}
                  onForceCheck={handleForceCheck}
                  onToggleStatus={handleToggleStatus}
                  onDelete={handleDeleteTicket}
                />
              ))}
            </div>
          )}
        </section>

      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 bg-[#060910] py-6 text-xs text-slate-400 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-2">
            <span className="font-mono font-bold text-white">RailPulse Engine</span>
            <span>•</span>
            <span>Zero-Cost IRCTC Smart Tracker</span>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-[11px]">
            <span className="flex items-center space-x-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>IRCTC Night Window Protection (23:45–00:30 IST)</span>
            </span>
            <span className="flex items-center space-x-1">
              <Smartphone className="w-3.5 h-3.5 text-blue-400" />
              <span>Baileys WhatsApp Bot Multi-Device Protocol</span>
            </span>
          </div>
        </div>
      </footer>

      {/* Modals & Drawers */}
      <WhatsAppModal
        isOpen={isWhatsAppModalOpen}
        onClose={() => setIsWhatsAppModalOpen(false)}
        whatsAppStatus={whatsAppStatus}
        onReconnect={handleWhatsAppReconnect}
        onDisconnect={handleWhatsAppDisconnect}
        onTestPing={handleTestPing}
      />

      <NotificationSidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        notifications={notifications}
        onClearNotifications={handleClearNotifications}
        onSendTestPing={handleTestPing}
      />

    </div>
  );
}
