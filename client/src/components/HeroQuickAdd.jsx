import React, { useState, useRef } from 'react';
import {
  Search,
  Upload,
  FileText,
  CheckCircle2,
  AlertCircle,
  Zap,
  Sparkles,
  Phone,
  ArrowRight,
  ShieldAlert
} from 'lucide-react';

export default function HeroQuickAdd({
  onAddPnr,
  onUploadTicket,
  isLoading = false
}) {
  const [pnr, setPnr] = useState('');
  const [phone, setPhone] = useState('9876543210');
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [extractedInfo, setExtractedInfo] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');

  const fileInputRef = useRef(null);

  const cleanPnr = pnr.replace(/\D/g, '');
  const isValidPnr = cleanPnr.length === 10;
  const cleanPhone = phone.replace(/\D/g, '');
  const isValidPhone = cleanPhone.length === 10 || (cleanPhone.startsWith('91') && cleanPhone.length === 12);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');

    if (!isValidPnr) {
      setErrorMsg('Please enter a valid 10-digit IRCTC PNR number.');
      return;
    }

    try {
      await onAddPnr(cleanPnr, cleanPhone, extractedInfo);
      setPnr('');
      setExtractedInfo(null);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to start tracking PNR.');
    }
  };

  const handleFileUpload = async (file) => {
    if (!file) return;
    setUploading(true);
    setErrorMsg('');
    try {
      const data = await onUploadTicket(file);
      if (data && data.pnr) {
        setPnr(data.pnr);
        setExtractedInfo(data);
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to extract ticket from file.');
    } finally {
      setUploading(false);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const loadPreset = (presetPnr, presetPhone = '9876543210') => {
    setPnr(presetPnr);
    setPhone(presetPhone);
    setErrorMsg('');
  };

  return (
    <div className="relative pt-6 pb-10">
      {/* Background radial glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-4xl h-80 radial-glow-cyan pointer-events-none -z-10" />

      <div className="text-center max-w-3xl mx-auto mb-8 px-4">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold mb-4">
          <Sparkles className="w-3.5 h-3.5 text-blue-400" />
          <span>Zero-Cost IRCTC Waitlist Prediction & WhatsApp Movement Engine</span>
        </div>
        <h1 className="text-3xl sm:text-5xl font-black text-white tracking-tight leading-tight">
          Track Your Berth Movement. <br />
          <span className="bg-gradient-to-r from-blue-400 via-cyan-400 to-emerald-400 bg-clip-text text-transparent">
            Get WhatsApp Alerts Live.
          </span>
        </h1>
        <p className="mt-3 text-sm sm:text-base text-slate-300 max-w-2xl mx-auto">
          AI confirmation odds calculated from Quota weightings, coach turnover, and charting velocity.
          Instant WhatsApp notification sent whenever your waitlist position jumps!
        </p>
      </div>

      {/* Main Glassmorphic Input Card */}
      <div className="max-w-4xl mx-auto px-4">
        <div className="glass-panel-elevated p-5 sm:p-7 rounded-2xl relative overflow-hidden">
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-3 sm:gap-4 items-center">
              
              {/* 10-digit PNR input */}
              <div className="md:col-span-5 relative">
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1.5 flex items-center justify-between">
                  <span>10-Digit PNR Number</span>
                  {isValidPnr && (
                    <span className="text-emerald-400 flex items-center space-x-1 text-[10px] font-semibold">
                      <CheckCircle2 className="w-3 h-3" />
                      <span>Valid PNR</span>
                    </span>
                  )}
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Search className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    maxLength={10}
                    placeholder="e.g. 2458910342"
                    value={pnr}
                    onChange={(e) => setPnr(e.target.value.replace(/\D/g, ''))}
                    className="w-full pl-10 pr-4 py-3 glass-input rounded-xl text-white font-mono text-base tracking-widest placeholder:tracking-normal placeholder:font-sans placeholder:text-slate-500"
                  />
                </div>
              </div>

              {/* WhatsApp Phone input */}
              <div className="md:col-span-4 relative">
                <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1.5 flex items-center justify-between">
                  <span>WhatsApp Phone</span>
                  <span className="text-slate-400 text-[10px]">Auto-prefixed +91</span>
                </label>
                <div className="relative flex">
                  <span className="inline-flex items-center px-3 rounded-l-xl border border-r-0 border-white/10 bg-slate-900 text-slate-300 font-mono text-xs font-bold">
                    🇮🇳 +91
                  </span>
                  <input
                    type="tel"
                    maxLength={10}
                    placeholder="10-digit mobile"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value.replace(/\D/g, ''))}
                    className="w-full pl-3 pr-4 py-3 glass-input rounded-r-xl text-white font-mono text-sm placeholder:font-sans placeholder:text-slate-500"
                  />
                </div>
              </div>

              {/* Submit CTA Button */}
              <div className="md:col-span-3 pt-1 md:pt-5">
                <button
                  type="submit"
                  disabled={isLoading || !isValidPnr}
                  className="w-full py-3 px-4 rounded-xl font-bold text-sm text-white bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 shadow-lg shadow-blue-500/30 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2 transition transform active:scale-[0.98]"
                >
                  {isLoading ? (
                    <span>Tracking...</span>
                  ) : (
                    <>
                      <span>Track & Alert</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>

            </div>

            {errorMsg && (
              <div className="flex items-center space-x-2 text-rose-400 text-xs px-3 py-2 bg-rose-500/10 border border-rose-500/20 rounded-lg">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            {extractedInfo && (
              <div className="flex items-center justify-between text-xs px-3.5 py-2.5 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-300">
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                  <span>
                    <strong>Extracted from Ticket:</strong> {extractedInfo.trainNumber} - {extractedInfo.trainName} ({extractedInfo.travelClass}) | Status: {extractedInfo.currentStatus}
                  </span>
                </div>
                <span className="text-[10px] text-emerald-400/80 uppercase font-mono tracking-wider">
                  {extractedInfo.extractedBy || 'AI OCR'}
                </span>
              </div>
            )}

            {/* Drag & Drop Ticket Screenshot Section */}
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-3 sm:p-4 text-center cursor-pointer transition ${
                dragActive
                  ? 'border-blue-400 bg-blue-500/10'
                  : 'border-white/10 hover:border-white/20 bg-slate-900/40 hover:bg-slate-900/60'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*,application/pdf"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
              />
              <div className="flex items-center justify-center space-x-2 text-xs text-slate-300">
                <Upload className="w-4 h-4 text-blue-400" />
                <span>
                  {uploading
                    ? 'Scanning ticket with AI OCR...'
                    : 'Or drag & drop IRCTC ticket screenshot / PDF here to auto-fill PNR'}
                </span>
                <span className="hidden sm:inline text-slate-400">(PNG, JPG, PDF)</span>
              </div>
            </div>

            {/* Quick Demo Presets */}
            <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-slate-400">
              <span className="font-semibold text-slate-400 flex items-center space-x-1">
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                <span>Quick Test Presets:</span>
              </span>
              <button
                type="button"
                onClick={() => loadPreset('2458910342')}
                className="px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-white/10 text-slate-300 hover:text-white transition font-mono text-[11px]"
              >
                12952 Tejas (WL 18)
              </button>
              <button
                type="button"
                onClick={() => loadPreset('4129087563')}
                className="px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-white/10 text-slate-300 hover:text-white transition font-mono text-[11px]"
              >
                12628 Karnataka (RLWL 9)
              </button>
              <button
                type="button"
                onClick={() => loadPreset('8391024567')}
                className="px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-white/10 text-slate-300 hover:text-white transition font-mono text-[11px]"
              >
                12302 Howrah (WL 27)
              </button>
            </div>

          </form>

        </div>
      </div>
    </div>
  );
}
