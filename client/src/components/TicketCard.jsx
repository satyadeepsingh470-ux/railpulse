import React, { useState } from 'react';
import { motion } from 'framer-motion';
import confetti from 'canvas-confetti';
import {
  Train,
  ArrowRight,
  Calendar,
  Clock,
  Sparkles,
  RefreshCw,
  Zap,
  PartyPopper,
  Pause,
  Play,
  Trash2,
  TrendingUp,
  ShieldCheck,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import ConfirmationGauge from './ConfirmationGauge';

export default function TicketCard({
  ticket,
  onSimulateDrop,
  onSimulateConfirm,
  onForceCheck,
  onToggleStatus,
  onDelete
}) {
  const [loadingDrop, setLoadingDrop] = useState(false);
  const [loadingConfirm, setLoadingConfirm] = useState(false);
  const [loadingCheck, setLoadingCheck] = useState(false);

  const isConfirmed = ticket.status === 'CONFIRMED' || ticket.current_status.startsWith('CNF');
  const isStopped = ticket.status === 'STOPPED';

  const handleDropClick = async () => {
    setLoadingDrop(true);
    try {
      await onSimulateDrop(ticket.pnr);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingDrop(false);
    }
  };

  const handleConfirmClick = async () => {
    setLoadingConfirm(true);
    try {
      await onSimulateConfirm(ticket.pnr);
      // Trigger canvas-confetti celebration!
      confetti({
        particleCount: 90,
        spread: 70,
        origin: { y: 0.6 }
      });
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingConfirm(false);
    }
  };

  const handleCheckClick = async () => {
    setLoadingCheck(true);
    try {
      await onForceCheck(ticket.pnr);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingCheck(false);
    }
  };

  // Format date
  const formatTravelDate = (dateStr) => {
    if (!dateStr) return 'Upcoming';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  const historyItems = ticket.history || [];

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.3 }}
      className={`ticket-card relative rounded-2xl shadow-xl transition-all duration-300 ${
        isConfirmed
          ? 'border-emerald-500/40 ring-1 ring-emerald-500/20'
          : 'border-white/10 hover:border-white/20'
      }`}
    >
      {/* Semicircle Cutout Notches for realistic railway boarding pass feel */}
      <div className="absolute -left-3.5 top-1/2 -translate-y-1/2 w-7 h-7 bg-[#080C14] rounded-full border border-white/10 z-20 pointer-events-none" />
      <div className="absolute -right-3.5 top-1/2 -translate-y-1/2 w-7 h-7 bg-[#080C14] rounded-full border border-white/10 z-20 pointer-events-none" />

      {/* Card Header */}
      <div className="px-6 py-4 border-b border-white/10 bg-slate-900/60 flex flex-wrap items-center justify-between gap-3">
        {/* Train & Route Details */}
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-blue-500/10 border border-blue-500/20 rounded-xl text-blue-400">
            <Train className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-base font-black text-white font-mono">
                {ticket.train_number}
              </span>
              <span className="text-sm font-semibold text-slate-200">
                {ticket.train_name}
              </span>
            </div>
            <div className="flex items-center space-x-2 text-xs text-slate-400 mt-0.5">
              <span>{ticket.source_station_name || ticket.source_station}</span>
              <ArrowRight className="w-3 h-3 text-slate-400" />
              <span>{ticket.dest_station_name || ticket.dest_station}</span>
            </div>
          </div>
        </div>

        {/* PNR & Status Pills */}
        <div className="flex items-center space-x-2">
          <div className="px-3 py-1 bg-slate-800/80 border border-white/10 rounded-lg text-xs font-mono font-bold text-slate-200">
            PNR: <span className="text-blue-400">{ticket.pnr}</span>
          </div>

          <div
            className={`px-3 py-1 rounded-lg text-xs font-bold border flex items-center space-x-1.5 ${
              isConfirmed
                ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300'
                : isStopped
                ? 'bg-slate-800 border-white/10 text-slate-400'
                : 'bg-blue-500/15 border-blue-500/30 text-blue-300'
            }`}
          >
            {isConfirmed ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>CONFIRMED</span>
              </>
            ) : isStopped ? (
              <>
                <Pause className="w-3.5 h-3.5 text-slate-400" />
                <span>PAUSED</span>
              </>
            ) : (
              <>
                <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
                <span>TRACKING</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Main Boarding Pass Body */}
      <div className="p-6 grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">
        
        {/* Left Section: Journey info, Status, Movement Timeline */}
        <div className="lg:col-span-8 space-y-5">
          
          {/* Key Ticket Badges */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-white/10 text-xs text-slate-300">
              <Calendar className="w-3.5 h-3.5 text-blue-400" />
              <span>{formatTravelDate(ticket.journey_date)}</span>
            </div>
            <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-white/10 text-xs text-slate-300">
              <Clock className="w-3.5 h-3.5 text-indigo-400" />
              <span>Dep: {ticket.journey_time || '16:00'}</span>
            </div>
            <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-white/10 text-xs font-semibold text-slate-300">
              Class: <span className="text-white font-bold">{ticket.travel_class}</span>
            </div>
            <div className="px-3 py-1.5 rounded-lg bg-slate-900 border border-white/10 text-xs font-semibold text-slate-300">
              Quota: <span className="text-white font-bold">{ticket.quota}</span>
            </div>
          </div>

          {/* Current & Booked Status Block */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-3.5 rounded-xl bg-slate-950/60 border border-white/5">
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
                Current Status
              </span>
              <span className={`text-base sm:text-lg font-black font-mono mt-0.5 block ${
                isConfirmed ? 'text-emerald-400' : 'text-blue-400'
              }`}>
                {ticket.current_status}
              </span>
            </div>

            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
                Booking Status
              </span>
              <span className="text-base sm:text-lg font-medium font-mono text-slate-300 mt-0.5 block">
                {ticket.booking_status}
              </span>
            </div>

            <div className="col-span-2 sm:col-span-1">
              <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
                Chart Status
              </span>
              <span className="text-xs sm:text-sm font-semibold text-slate-300 mt-1 block">
                {ticket.chart_prepared ? '✅ Prepared' : '⏳ Chart Not Prepared'}
              </span>
            </div>
          </div>

          {/* Waitlist Movement Sparkline / Step Timeline */}
          {historyItems.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-400 flex items-center space-x-1.5">
                  <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Waitlist Movement History</span>
                </span>
                {ticket.booking_wl_number > ticket.current_wl_number && (
                  <span className="text-emerald-400 font-bold font-mono text-xs flex items-center space-x-1">
                    <span>▲ +{ticket.booking_wl_number - ticket.current_wl_number} berths cleared</span>
                  </span>
                )}
              </div>

              {/* Step Timeline */}
              <div className="flex items-center space-x-2 overflow-x-auto pb-1 pt-1">
                {historyItems.map((step, idx) => (
                  <React.Fragment key={step.id || idx}>
                    <div className="flex-shrink-0 flex flex-col items-center p-2 rounded-lg bg-slate-900/80 border border-white/5 min-w-[90px] text-center">
                      <span className="text-[10px] text-slate-400 font-mono">
                        {step.recorded_at ? new Date(step.recorded_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) : `Step ${idx + 1}`}
                      </span>
                      <span className="text-xs font-black font-mono text-slate-200 mt-0.5">
                        {step.status_label}
                      </span>
                      <span className="text-[10px] text-emerald-400 font-medium">
                        {step.probability}% chance
                      </span>
                    </div>

                    {idx < historyItems.length - 1 && (
                      <ArrowRight className="w-3 h-3 text-slate-400 flex-shrink-0" />
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>
          )}

          {/* AI Intelligence / Prediction Explanation Tip */}
          {(ticket.smart_tip || ticket.prediction_explanation) && (
            <div className="p-3.5 rounded-xl bg-blue-950/20 border border-blue-500/20 text-xs text-blue-200 flex items-start space-x-2.5">
              <Sparkles className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <span className="font-bold text-blue-300 block text-[11px] uppercase tracking-wider">
                  IRCTC Intelligence Tip:
                </span>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {ticket.smart_tip || ticket.prediction_explanation}
                </p>
              </div>
            </div>
          )}

        </div>

        {/* Right Section: Animated Radial Confirmation Gauge */}
        <div className="lg:col-span-4 flex flex-col items-center justify-center p-4 border-t lg:border-t-0 lg:border-l border-white/10 bg-slate-950/30 rounded-xl">
          <ConfirmationGauge
            probability={ticket.confirmation_probability || 50}
            riskBadge={ticket.risk_badge || 'Moderate'}
            size={135}
          />

          <div className="mt-3 text-center">
            <span className="text-[10px] text-slate-400 block font-mono">
              Auto-check: Every 5 mins
            </span>
            <span className="text-[10px] text-slate-400 italic block mt-0.5">
              WhatsApp alerts active for +{ticket.phone}
            </span>
          </div>
        </div>

      </div>

      {/* Card Action Toolbar */}
      <div className="px-6 py-3.5 bg-slate-950/80 border-t border-white/10 flex flex-wrap items-center justify-between gap-2 text-xs">
        
        {/* Simulation / Testing Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          
          {/* Simulate WL Drop */}
          <button
            onClick={handleDropClick}
            disabled={loadingDrop || isConfirmed}
            title="Simulate Waitlist Drop: Tests state diffing and triggers real/mock WhatsApp notification immediately"
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg font-bold bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/30 text-amber-300 transition disabled:opacity-50"
          >
            <Zap className={`w-3.5 h-3.5 text-amber-400 ${loadingDrop ? 'animate-spin' : ''}`} />
            <span>{loadingDrop ? 'Simulating...' : 'Simulate WL Drop (Test WhatsApp)'}</span>
          </button>

          {/* Simulate Confirmed */}
          {!isConfirmed && (
            <button
              onClick={handleConfirmClick}
              disabled={loadingConfirm}
              title="Simulate Berth Confirmation: Triggers confetti celebration and CNF WhatsApp alert"
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg font-bold bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-emerald-300 transition disabled:opacity-50"
            >
              <PartyPopper className={`w-3.5 h-3.5 text-emerald-400 ${loadingConfirm ? 'animate-bounce' : ''}`} />
              <span>{loadingConfirm ? 'Confirming...' : 'Simulate CNF'}</span>
            </button>
          )}

          {/* Force Check Now */}
          <button
            onClick={handleCheckClick}
            disabled={loadingCheck}
            title="Re-query PNR status immediately"
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-white/10 text-slate-300 hover:text-white transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingCheck ? 'animate-spin text-blue-400' : ''}`} />
            <span>Force Check</span>
          </button>

        </div>

        {/* Secondary controls: Pause/Stop & Delete */}
        <div className="flex items-center space-x-2">
          
          <button
            onClick={() => onToggleStatus(ticket.pnr)}
            title={isStopped ? 'Resume Alerts' : 'Pause Alerts'}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-white/5 transition"
          >
            {isStopped ? <Play className="w-4 h-4 text-emerald-400" /> : <Pause className="w-4 h-4" />}
          </button>

          <button
            onClick={() => onDelete(ticket.pnr)}
            title="Delete Ticket"
            className="p-1.5 text-slate-400 hover:text-rose-400 rounded-lg hover:bg-rose-500/10 transition"
          >
            <Trash2 className="w-4 h-4" />
          </button>

        </div>

      </div>

    </motion.div>
  );
}
