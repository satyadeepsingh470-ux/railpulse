import React, { useState, useEffect } from 'react';
import {
  Train,
  Smartphone,
  CheckCircle2,
  Bell,
  Sliders,
  Moon,
  Sun,
  ShieldCheck,
  Zap,
  Globe
} from 'lucide-react';

export default function Navbar({
  systemStatus,
  whatsAppStatus,
  onOpenWhatsAppModal,
  onToggleSidebar,
  notificationCount = 0,
  onToggleMode,
  onToggleMaintenance
}) {
  const [istTime, setIstTime] = useState('');

  // Live ticking IST clock
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const istStr = now.toLocaleTimeString('en-IN', {
        timeZone: 'Asia/Kolkata',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
      });
      setIstTime(istStr);
    };

    updateTime();
    const timer = setInterval(updateTime, 1000);
    return () => clearInterval(timer);
  }, []);

  const isConnected = whatsAppStatus?.status === 'connected';
  const isSimulation = systemStatus?.mode === 'simulation';
  const inMaintenance = systemStatus?.irctc?.inMaintenance;

  return (
    <header className="sticky top-0 z-40 w-full border-b border-white/10 bg-[#080C14]/85 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        
        {/* Brand / Logo */}
        <div className="flex items-center space-x-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 via-indigo-600 to-cyan-500 shadow-lg shadow-blue-500/25">
            <Train className="w-5 h-5 text-white" />
            <div className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-emerald-400 rounded-full border-2 border-[#080C14] animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-lg font-black tracking-tight text-white font-mono">
                Rail<span className="text-blue-400">Pulse</span>
              </span>
              <span className="hidden sm:inline-block px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                IRCTC Intelligence
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">
              Smart PNR & Waitlist WhatsApp Tracker
            </p>
          </div>
        </div>

        {/* Center / Right controls */}
        <div className="flex items-center space-x-2 sm:space-x-3">

          {/* Mode Switcher Pill */}
          <button
            onClick={onToggleMode}
            title="Toggle between Zero-Cost Simulation Mode and Live RapidAPI Mode"
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition ${
              isSimulation
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-300 hover:bg-amber-500/20'
                : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/20'
            }`}
          >
            {isSimulation ? <Zap className="w-3.5 h-3.5 text-amber-400" /> : <Globe className="w-3.5 h-3.5 text-emerald-400" />}
            <span className="hidden md:inline">{isSimulation ? 'Mode:' : 'Mode:'}</span>
            <span className="font-bold">{isSimulation ? 'Simulation (Free)' : 'Live RapidAPI'}</span>
          </button>

          {/* IRCTC Maintenance Status Pill */}
          <button
            onClick={onToggleMaintenance}
            title={`IRCTC IST Time: ${istTime}. Click to test toggle maintenance window.`}
            className={`hidden lg:flex items-center space-x-2 px-3 py-1.5 rounded-full text-xs font-medium border transition ${
              inMaintenance
                ? 'bg-purple-900/30 border-purple-500/40 text-purple-300'
                : 'bg-slate-900/60 border-white/10 text-slate-300 hover:border-white/20'
            }`}
          >
            {inMaintenance ? (
              <Moon className="w-3.5 h-3.5 text-purple-400 animate-pulse" />
            ) : (
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
            )}
            <span className="font-mono text-[11px] text-slate-400">{istTime || 'IST'}</span>
            <span className="hidden xl:inline text-[11px]">
              {inMaintenance ? 'IRCTC Maintenance (Paused)' : 'IRCTC Active'}
            </span>
          </button>

          {/* WhatsApp Bot Connection Pill */}
          <button
            onClick={onOpenWhatsAppModal}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-full text-xs font-semibold border transition shadow-sm ${
              isConnected
                ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/25'
                : 'bg-blue-600/20 border-blue-500/40 text-blue-300 hover:bg-blue-600/30'
            }`}
          >
            {isConnected ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>Connected</span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
              </>
            ) : (
              <>
                <Smartphone className="w-3.5 h-3.5 text-blue-400 animate-bounce" />
                <span>Scan QR to Connect</span>
              </>
            )}
          </button>

          {/* Notification Sidebar Trigger */}
          <button
            onClick={onToggleSidebar}
            className="relative p-2 text-slate-300 hover:text-white bg-slate-900/60 hover:bg-slate-800/80 border border-white/10 rounded-full transition"
            title="Open WhatsApp Alert Feed"
          >
            <Bell className="w-4 h-4" />
            {notificationCount > 0 && (
              <span className="absolute -top-1 -right-1 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-rose-500 rounded-full border-2 border-[#080C14]">
                {notificationCount}
              </span>
            )}
          </button>

        </div>
      </div>
    </header>
  );
}
