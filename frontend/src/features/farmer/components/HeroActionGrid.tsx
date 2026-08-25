/**
 * HeroActionGrid Component.
 *
 * Prominent 3-action launcher for farmers:
 * 1. 🎤 Voice Query (Multilingual Spoken Advisory)
 * 2. 💬 Ask KrishiOS (AI Decision Assistant)
 * 3. 📷 Crop Doctor (Camera & Image Diagnostics)
 */

import React from 'react';
import { Mic, MessageSquare, Camera } from 'lucide-react';

interface HeroActionGridProps {
  onSelectAction: (action: 'voice' | 'text' | 'vision') => void;
}

export const HeroActionGrid: React.FC<HeroActionGridProps> = ({ onSelectAction }) => {
  return (
    <section aria-label="Quick Actions" className="space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="text-small font-bold uppercase tracking-wider text-text-secondary">
          Ask KrishiOS Intelligence
        </h2>
        <span className="text-caption text-primary-600 font-medium">Multilingual AI</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* 1. Voice Action */}
        <button
          type="button"
          onClick={() => onSelectAction('voice')}
          className="group relative flex items-center sm:flex-col sm:items-start p-4 bg-gradient-to-br from-primary-700 to-primary-800 text-white rounded-xl shadow-md hover:shadow-lg hover:from-primary-800 hover:to-primary-900 transition-all text-left cursor-pointer border border-primary-600/50 active:scale-[0.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-400"
        >
          <div className="w-12 h-12 rounded-xl bg-white/15 backdrop-blur-sm flex items-center justify-center text-white mr-4 sm:mr-0 sm:mb-3 group-hover:scale-110 transition-transform">
            <Mic className="w-6 h-6 animate-pulse" aria-hidden="true" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-1.5">
              <span className="text-body font-bold">Speak Question</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] bg-primary-900/60 text-primary-200 border border-primary-500/40">
                Voice
              </span>
            </div>
            <p className="text-caption text-primary-100/90 mt-0.5">
              Telugu, Hindi, or English voice query
            </p>
          </div>
        </button>

        {/* 2. Text Query Action */}
        <button
          type="button"
          onClick={() => onSelectAction('text')}
          className="group relative flex items-center sm:flex-col sm:items-start p-4 bg-surface text-text rounded-xl shadow-sm hover:shadow-md border border-border hover:border-primary-400 transition-all text-left cursor-pointer active:scale-[0.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
        >
          <div className="w-12 h-12 rounded-xl bg-primary-50 text-primary-700 flex items-center justify-center mr-4 sm:mr-0 sm:mb-3 group-hover:scale-110 transition-transform">
            <MessageSquare className="w-6 h-6" aria-hidden="true" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-1.5">
              <span className="text-body font-bold text-text">Ask AI Assistant</span>
            </div>
            <p className="text-caption text-text-secondary mt-0.5">
              Pest, fertilizer, weather, or market query
            </p>
          </div>
        </button>

        {/* 3. Vision Crop Doctor Action */}
        <button
          type="button"
          onClick={() => onSelectAction('vision')}
          className="group relative flex items-center sm:flex-col sm:items-start p-4 bg-surface text-text rounded-xl shadow-sm hover:shadow-md border border-border hover:border-accent-400 transition-all text-left cursor-pointer active:scale-[0.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500"
        >
          <div className="w-12 h-12 rounded-xl bg-accent-50 text-accent-700 flex items-center justify-center mr-4 sm:mr-0 sm:mb-3 group-hover:scale-110 transition-transform">
            <Camera className="w-6 h-6" aria-hidden="true" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-1.5">
              <span className="text-body font-bold text-text">Analyze Crop</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] bg-accent-100 text-accent-800">
                Photo
              </span>
            </div>
            <p className="text-caption text-text-secondary mt-0.5">
              Identify pests, diseases, or deficiencies
            </p>
          </div>
        </button>
      </div>
    </section>
  );
};

export default HeroActionGrid;
