import React from 'react';
import { motion } from 'framer-motion';

export default function ConfirmationGauge({ probability = 50, riskBadge = 'Moderate', size = 130 }) {
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clampedProb = Math.max(0, Math.min(100, probability));
  const offset = circumference - (clampedProb / 100) * circumference;

  let color = '#F59E0B'; // Amber
  let glowColor = 'rgba(245, 158, 11, 0.35)';
  let textColor = 'text-amber-400';
  let badgeBg = 'bg-amber-500/15 border-amber-500/30 text-amber-300';

  if (clampedProb >= 75) {
    color = '#10B981'; // Emerald
    glowColor = 'rgba(16, 185, 129, 0.4)';
    textColor = 'text-emerald-400';
    badgeBg = 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300';
  } else if (clampedProb < 45) {
    color = '#F43F5E'; // Rose
    glowColor = 'rgba(244, 63, 94, 0.4)';
    textColor = 'text-rose-400';
    badgeBg = 'bg-rose-500/15 border-rose-500/30 text-rose-300';
  }

  return (
    <div className="flex flex-col items-center justify-center relative select-none">
      <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
        {/* Background track circle */}
        <svg width={size} height={size} className="transform -rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="rgba(255, 255, 255, 0.08)"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          {/* Animated active circle */}
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={circumference}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1.2, ease: "easeOut" }}
            strokeLinecap="round"
            fill="transparent"
            style={{
              filter: `drop-shadow(0 0 8px ${glowColor})`
            }}
          />
        </svg>

        {/* Center Percentage Display */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <motion.span
            key={clampedProb}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.4 }}
            className={`text-2xl font-black tracking-tight ${textColor}`}
          >
            {clampedProb}%
          </motion.span>
          <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
            Confirm %
          </span>
        </div>
      </div>

      {/* Risk Badge */}
      <div className={`mt-2 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${badgeBg} tracking-wide`}>
        {riskBadge}
      </div>
    </div>
  );
}
