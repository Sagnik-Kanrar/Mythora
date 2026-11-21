import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Clapperboard, 
  Sparkles, 
  Lock, 
  Unlock, 
  X, 
  Crown, 
  Play, 
  Layers, 
  Film,
  Zap,
  CheckCircle2,
  ArrowRight
} from 'lucide-react';
import { PlanId } from '../../config/plansConfig';
import { sound } from '../../services/audioService';

interface StoryAnimationModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentPlan: PlanId;
  onUpgradeToUltra: () => void;
}

export const StoryAnimationModal: React.FC<StoryAnimationModalProps> = ({
  isOpen,
  onClose,
  currentPlan,
  onUpgradeToUltra,
}) => {
  const isUnlocked = currentPlan === 'ultra';

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 overflow-y-auto">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => {
            sound.playPaperRustle();
            onClose();
          }}
          className="fixed inset-0 bg-black/85 backdrop-blur-md"
        />

        {/* Modal Window */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          transition={{ duration: 0.2 }}
          className="relative w-full max-w-2xl bg-[#140F0C] border border-[#C49A61]/50 rounded-2xl shadow-[0_0_50px_rgba(0,0,0,0.9),0_0_20px_rgba(196,154,97,0.15)] overflow-hidden z-10 font-sans my-8"
        >
          {/* Ornate Top Banner / Foil Ribbon */}
          <div className="bg-gradient-to-r from-[#2A1D13] via-[#3D2919] to-[#2A1D13] border-b border-[#C49A61]/40 px-5 sm:px-7 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#D4AF37] to-[#8C6D3E] p-0.5 shadow-md flex items-center justify-center">
                <div className="w-full h-full bg-[#1A130E] rounded-[10px] flex items-center justify-center">
                  <Clapperboard className="w-5 h-5 text-[#F3D4A0]" />
                </div>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-serif font-bold text-[#F3D4A0] text-lg sm:text-xl">
                    Story Animation
                  </span>
                  <span className="px-2 py-0.5 text-[10px] font-bold tracking-widest uppercase bg-[#C49A61]/25 text-[#F5EDE3] border border-[#C49A61]/60 rounded-full flex items-center gap-1">
                    <Crown className="w-2.5 h-2.5 text-[#F3D4A0]" />
                    Ultra Exclusive
                  </span>
                </div>
                <p className="text-xs text-[#A89886] font-serif italic">
                  Living Cinematic Visualization for Fiction Manuscripts
                </p>
              </div>
            </div>

            <button
              onClick={() => {
                sound.playPaperRustle();
                onClose();
              }}
              className="w-8 h-8 rounded-full bg-[#201712] hover:bg-[#33241B] border border-[#4A3728] hover:border-[#C49A61] text-[#A89886] hover:text-[#F3D4A0] flex items-center justify-center transition-colors"
              title="Close Preview"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="p-5 sm:p-7 space-y-6">
            {/* Visual Cinematic Preview Canvas */}
            <div className="relative rounded-xl overflow-hidden border border-[#423122] bg-[#0A0806] shadow-2xl aspect-video flex flex-col justify-between group">
              {/* Animated Cinematic Simulation Layer */}
              <div className="absolute inset-0 bg-gradient-to-t from-black via-black/40 to-transparent z-10" />

              {/* Atmospheric Background Illustration */}
              <div 
                className="absolute inset-0 opacity-40 mix-blend-screen scale-105 group-hover:scale-110 transition-transform duration-1000"
                style={{
                  backgroundImage: `radial-gradient(circle at 50% 40%, rgba(196,154,97,0.3) 0%, transparent 60%), radial-gradient(circle at 80% 80%, rgba(110,60,20,0.4) 0%, transparent 50%)`,
                }}
              />

              {/* Filmstrip Sprocket Holes Top & Bottom */}
              <div className="relative z-20 w-full bg-black/60 backdrop-blur-sm border-b border-[#2C2117] px-3 py-1.5 flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-[#C49A61] animate-ping" />
                  <span className="font-mono text-[11px] text-[#C49A61] font-bold tracking-wider uppercase">
                    {isUnlocked ? "RENDER PASS: CINEMATIC REEL ACTIVE" : "PREVIEW SIMULATION: ULTRA REQUIRED"}
                  </span>
                </div>
                <span className="font-mono text-[10px] text-[#8C7A68]">
                  FRAME: 0144 / ACT II • CH. 3
                </span>
              </div>

              {/* Center Scene Composition */}
              <div className="relative z-20 flex-1 flex flex-col items-center justify-center p-6 text-center">
                {isUnlocked ? (
                  <div className="space-y-3">
                    <div className="w-14 h-14 rounded-full bg-[#C49A61]/20 border border-[#C49A61] mx-auto flex items-center justify-center shadow-[0_0_25px_rgba(196,154,97,0.4)]">
                      <Play className="w-6 h-6 text-[#F3D4A0] ml-1" />
                    </div>
                    <p className="font-serif text-sm sm:text-base text-[#F4ECE2] max-w-sm font-medium">
                      "The amber streetlamp cut through the Thames fog as Detective Vance turned the brass key..."
                    </p>
                    <span className="inline-block px-3 py-1 text-xs font-semibold bg-[#261B13] border border-[#C49A61]/40 text-[#F3D4A0] rounded-full">
                      ✓ Story Animation Engine Unlocked
                    </span>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="w-14 h-14 rounded-full bg-[#1F1712] border border-[#5A432F] mx-auto flex items-center justify-center shadow-inner">
                      <Lock className="w-6 h-6 text-[#C49A61]" />
                    </div>
                    <div className="space-y-1">
                      <h4 className="font-serif text-base sm:text-lg font-bold text-[#F5EDE3]">
                        Cinematic Manuscript Synthesis
                      </h4>
                      <p className="font-sans text-xs sm:text-[13px] text-[#A69584] max-w-md mx-auto">
                        Ultra subscribers can convert chapter text into animated storyboards, complete with camera staging, character positioning, and dramatic lighting.
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Bottom Film Strip Indicator */}
              <div className="relative z-20 w-full bg-black/80 backdrop-blur-sm border-t border-[#2C2117] px-4 py-2 flex items-center justify-between text-xs text-[#8C7A68]">
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1 text-[#C49A61]">
                    <Layers className="w-3.5 h-3.5" /> 3D Staging
                  </span>
                  <span className="flex items-center gap-1 text-[#C49A61]">
                    <Film className="w-3.5 h-3.5" /> 24 FPS Animatics
                  </span>
                </div>
                <span className="font-typewriter text-[11px] text-[#B09E8C]">
                  {isUnlocked ? "Status: Full Access" : "Status: Restricted to Ultra"}
                </span>
              </div>
            </div>

            {/* Feature Breakdown Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <div className="p-3.5 rounded-xl bg-[#1A1410] border border-[#2F2318] space-y-1.5">
                <div className="flex items-center gap-2 text-[#F3D4A0] font-serif font-bold text-sm">
                  <Film className="w-4 h-4 text-[#C49A61]" />
                  <span>Scene-to-Cinema Engine</span>
                </div>
                <p className="text-xs text-[#9E8E7D] leading-relaxed">
                  Translates written sensory descriptions, character gaze directions, and physical blocking directly into visual animatic keyframes.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-[#1A1410] border border-[#2F2318] space-y-1.5">
                <div className="flex items-center gap-2 text-[#F3D4A0] font-serif font-bold text-sm">
                  <Zap className="w-4 h-4 text-[#C49A61]" />
                  <span>Dossier Entity Rigging</span>
                </div>
                <p className="text-xs text-[#9E8E7D] leading-relaxed">
                  Automatically extracts character physical traits, costumes, and height parameters from your archive dossiers into the animated scene.
                </p>
              </div>
            </div>

            {/* Upgrade Banner & Call-To-Action */}
            <div className="pt-2 border-t border-[#2C2117]">
              {isUnlocked ? (
                <div className="flex items-center justify-between p-3.5 rounded-xl bg-[#201812] border border-[#C49A61]/50">
                  <div className="flex items-center gap-2.5">
                    <CheckCircle2 className="w-5 h-5 text-[#C49A61]" />
                    <div>
                      <p className="text-sm font-bold text-[#F5EDE3]">Ultra Membership Active</p>
                      <p className="text-xs text-[#A69584]">You have full access to Story Animation generation.</p>
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      sound.playPaperRustle();
                      onClose();
                    }}
                    className="px-4 py-2 rounded-lg bg-[#C49A61] hover:bg-[#D8AC74] text-[#120D08] font-bold text-xs uppercase tracking-wider transition-all"
                  >
                    Got It
                  </button>
                </div>
              ) : (
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-gradient-to-r from-[#22170F] to-[#2E2015] border border-[#C49A61]/50 shadow-md">
                  <div className="space-y-0.5 text-center sm:text-left">
                    <div className="flex items-center justify-center sm:justify-start gap-1.5 text-sm font-bold text-[#F3D4A0]">
                      <Crown className="w-4 h-4 text-[#C49A61]" />
                      <span>Unlock with Ultra Tier</span>
                    </div>
                    <p className="text-xs text-[#A89886]">
                      {currentPlan === 'pro' 
                        ? "Upgrade from Pro to Ultra (₹799 / approx. $9.00 USD per month) to activate unlimited Story Animation."
                        : "Available exclusively for Ultra tier subscribers (₹799 / approx. $9.00 USD per month)."}
                    </p>
                  </div>

                  <button
                    onClick={() => {
                      sound.playPaperRustle();
                      onClose();
                      onUpgradeToUltra();
                    }}
                    className="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-gradient-to-r from-[#C49A61] via-[#D8AC74] to-[#C49A61] hover:brightness-110 text-[#120D08] font-bold text-xs uppercase tracking-wider transition-all shadow-lg flex items-center justify-center gap-2 cursor-pointer"
                  >
                    <span>Upgrade to Ultra</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
