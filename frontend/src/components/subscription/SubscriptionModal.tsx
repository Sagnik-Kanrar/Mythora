import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Crown, 
  Sparkles, 
  Check, 
  Lock, 
  Unlock, 
  X, 
  ArrowRight, 
  ShieldCheck, 
  Clapperboard, 
  HelpCircle,
  Gem,
  CheckCircle2,
  Film
} from 'lucide-react';
import { 
  SUBSCRIPTION_PLANS, 
  COMPARISON_TABLE, 
  PRICING_CONFIG,
  formatPriceINR,
  formatPriceUSD,
  PlanId, 
  SubscriptionPlan 
} from '../../config/plansConfig';
import { StoryAnimationModal } from './StoryAnimationModal';
import { sound } from '../../services/audioService';

interface SubscriptionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPlanChanged?: (plan: PlanId) => void;
}

export const SubscriptionModal: React.FC<SubscriptionModalProps> = ({
  isOpen,
  onClose,
  onPlanChanged,
}) => {
  // State for billing cycle toggle
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'annual'>('monthly');

  // Simulated active user plan (Defaults to 'free' so user sees the upgrade paths)
  const [currentPlan, setCurrentPlan] = useState<PlanId>('free');

  // State for opening Story Animation detail dialog
  const [animationModalOpen, setAnimationModalOpen] = useState(false);

  // Transient notification for upgrade simulation
  const [feedbackNotice, setFeedbackNotice] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSelectPlan = (targetPlan: PlanId) => {
    sound.playPaperRustle();

    if (targetPlan === currentPlan) {
      setFeedbackNotice(`You are currently on the ${SUBSCRIPTION_PLANS[targetPlan].name} plan.`);
      setTimeout(() => setFeedbackNotice(null), 3500);
      return;
    }

    // Update simulated plan state
    setCurrentPlan(targetPlan);
    if (onPlanChanged) onPlanChanged(targetPlan);

    const plan = SUBSCRIPTION_PLANS[targetPlan];
    const priceText = targetPlan === 'free' 
      ? '₹0 / $0 USD' 
      : `₹${formatPriceINR(plan.priceINR)} (~$${formatPriceUSD(plan.priceUSD)} USD)`;
    setFeedbackNotice(
      `✓ Switched simulated preview to ${plan.name} tier (${priceText} / month). Dual currency preview active. (Frontend prototype demonstration).`
    );
    setTimeout(() => setFeedbackNotice(null), 4500);
  };

  const handleOpenAnimationPrompt = () => {
    sound.playPaperRustle();
    setAnimationModalOpen(true);
  };

  return (
    <>
      <AnimatePresence>
        <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 md:p-6 overflow-y-auto">
          {/* Backdrop with dark Victorian blur */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => {
              sound.playPaperRustle();
              onClose();
            }}
            className="fixed inset-0 bg-[#0A0806]/85 backdrop-blur-md"
          />

          {/* Modal Container */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 20 }}
            transition={{ duration: 0.22, ease: "easeOut" }}
            className="relative w-full max-w-6xl bg-[#15100C] border border-[#3E3024] rounded-2xl shadow-[0_0_60px_rgba(0,0,0,0.95),0_0_25px_rgba(196,154,97,0.12)] overflow-hidden z-10 font-sans my-auto max-h-[92vh] flex flex-col"
          >
            {/* Header: Victorian Investigator Header with Brass Fittings */}
            <div className="bg-gradient-to-r from-[#1B140F] via-[#261C15] to-[#1B140F] border-b border-[#3A2D22] px-4 sm:px-8 py-5 flex items-center justify-between shrink-0 shadow-md">
              <div className="flex items-center gap-3 sm:gap-4">
                <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-xl bg-gradient-to-br from-[#D4AF37] to-[#7A5A2B] p-0.5 shadow-lg flex items-center justify-center shrink-0">
                  <div className="w-full h-full bg-[#18120D] rounded-[10px] flex items-center justify-center">
                    <Crown className="w-6 h-6 text-[#F3D4A0]" />
                  </div>
                </div>
                <div>
                  <div className="flex items-center gap-2.5">
                    <h2 className="font-serif font-bold text-lg sm:text-2xl text-[#F4ECE2] tracking-wide">
                      Investigator Membership & Dossier Archives
                    </h2>
                    <span className="hidden sm:inline-block px-2.5 py-0.5 text-[11px] font-sans font-bold uppercase tracking-wider bg-[#C49A61]/20 text-[#E5BA78] border border-[#C49A61]/40 rounded-full">
                      Studio Tiers
                    </span>
                  </div>
                  <p className="text-xs sm:text-sm text-[#A89886] font-serif italic mt-0.5">
                    Select the tier of narrative intelligence and universe capacity for your manuscripts.
                  </p>
                </div>
              </div>

              {/* Close Button */}
              <button
                onClick={() => {
                  sound.playPaperRustle();
                  onClose();
                }}
                className="w-9 h-9 rounded-full bg-[#221812] hover:bg-[#38261B] border border-[#4E3929] hover:border-[#C49A61] text-[#A69684] hover:text-[#F3D4A0] flex items-center justify-center transition-colors shadow-sm shrink-0 ml-2"
                title="Close Subscription Window"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Scrollable Modal Body */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-7 md:p-9 space-y-8 scrollbar-thin scrollbar-thumb-[#3A2C20]">
              
              {/* Currency & Billing Schedule Bar */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3.5 sm:px-5 rounded-xl bg-[#1A130E] border border-[#36271D] shadow-inner">
                <div className="flex items-center gap-2.5 text-xs font-sans text-[#E0B77D] flex-wrap">
                  <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-[#110D0A] border border-[#3A2A1D] font-serif font-bold text-sm text-[#F3D4A0]">
                    <span>₹ INR</span>
                    <span className="text-[#8C7A68]">/</span>
                    <span>$ USD</span>
                  </div>
                  <span className="font-semibold tracking-wide text-[#F4ECE2]">Dual Currency Display</span>
                  <span className="text-[#A89886] hidden md:inline">•</span>
                  <span className="text-[#A89886]">USD prices are approximate and may vary with exchange rates.</span>
                </div>

                <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-[#140E0A] border border-[#2E2015] text-xs font-sans text-[#A89886] shrink-0">
                  <span className="w-2 h-2 rounded-full bg-[#C49A61] animate-pulse" />
                  <span className="font-semibold text-[#EDE3D6]">Monthly Billing</span>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[#C49A61] bg-[#C49A61]/15 px-1.5 py-0.5 rounded border border-[#C49A61]/30">
                    Active
                  </span>
                </div>
              </div>

              {/* Transient Interactive Feedback Toast */}
              <AnimatePresence>
                {feedbackNotice && (
                  <motion.div
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    className="p-3 rounded-lg bg-[#241A13] border border-[#C49A61]/60 text-xs text-[#F3D4A0] flex items-center gap-2 shadow-md"
                  >
                    <CheckCircle2 className="w-4 h-4 text-[#C49A61] shrink-0" />
                    <span>{feedbackNotice}</span>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* SECTION: 3 PLAN CARDS (Side by Side on Desktop, Stacked on Mobile) */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-7 items-stretch">
                
                {/* ── PLAN 1: FREE ── */}
                <div className={`relative rounded-2xl bg-[#18120D] p-6 flex flex-col justify-between transition-all duration-300 ${
                  currentPlan === 'free'
                    ? 'border-2 border-[#8C6D3E] shadow-[0_0_20px_rgba(140,109,62,0.25)]'
                    : 'border border-[#2F2318] hover:border-[#4E3929]'
                }`}>
                  <div className="space-y-4">
                    {/* Badge & Plan Name */}
                    <div className="flex items-center justify-between">
                      <span className="px-2.5 py-1 rounded-md text-xs font-typewriter font-bold tracking-widest uppercase bg-[#261E17] text-[#B09E8C] border border-[#3E3024]">
                        FREE
                      </span>
                      {currentPlan === 'free' && (
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-sans font-bold uppercase tracking-wider bg-[#C49A61]/20 text-[#E0B77D] border border-[#C49A61]/40">
                          Active Tier
                        </span>
                      )}
                    </div>

                    <div>
                      <h3 className="font-serif font-bold text-2xl text-[#F4ECE2]">
                        {SUBSCRIPTION_PLANS.free.name}
                      </h3>
                      <p className="text-xs text-[#A89886] font-serif italic mt-1 leading-relaxed">
                        {SUBSCRIPTION_PLANS.free.tagline}
                      </p>
                    </div>

                    {/* Price Display - Simultaneous INR + USD */}
                    <div className="py-4 my-2 border-y border-[#2B1F16] bg-[#140E0A]/60 -mx-6 px-6 rounded-sm">
                      {/* Primary: INR */}
                      <div className="flex items-baseline gap-2 flex-wrap">
                        <span className="font-serif text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#F4ECE2] tracking-tight">
                          ₹0
                        </span>
                        <span className="text-xs font-sans font-bold uppercase tracking-wider text-[#C49A61]">
                          INR
                        </span>
                        <span className="text-xs sm:text-sm font-sans font-semibold text-[#8C7A68]">
                          / month
                        </span>
                      </div>

                      {/* Secondary: USD (Smaller, Muted Text) */}
                      <div className="flex items-center gap-1.5 mt-1.5 text-xs text-[#A89886] font-sans">
                        <span className="font-medium text-[#D8CCC0]">$0 USD</span>
                        <span className="text-[11px] text-[#78695A]">per month</span>
                      </div>
                      <p className="text-[11px] font-sans text-[#78695A] mt-1.5">No payment required • Basic writing & limited AI</p>
                    </div>

                    {/* Features List */}
                    <div className="space-y-2.5 pt-1">
                      <span className="text-[11px] font-sans font-bold uppercase tracking-wider text-[#8C7A68] block">
                        Included In Free:
                      </span>
                      <ul className="space-y-2 text-xs text-[#D8CCC0]">
                        {SUBSCRIPTION_PLANS.free.features.map((feat, idx) => (
                          <li key={idx} className="flex items-start gap-2.5">
                            <Check className="w-4 h-4 text-[#8C7A68] shrink-0 mt-0.5" />
                            <span className="leading-tight">{feat.text}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* CTA Button */}
                  <div className="pt-6 mt-6 border-t border-[#2B1F16]">
                    <button
                      onClick={() => handleSelectPlan('free')}
                      className={`w-full py-3 rounded-xl font-sans text-xs sm:text-sm font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 ${
                        currentPlan === 'free'
                          ? 'bg-[#2B2017] text-[#C49A61] border border-[#4A3728] cursor-default'
                          : 'bg-[#241A13] hover:bg-[#33251B] text-[#EDE3D6] border border-[#423122]'
                      }`}
                    >
                      <span>{currentPlan === 'free' ? 'Current Plan' : 'Get Started'}</span>
                    </button>
                  </div>
                </div>

                {/* ── PLAN 2: PRO (MOST POPULAR) ── */}
                <div className={`relative rounded-2xl bg-[#1C150F] p-6 sm:p-7 flex flex-col justify-between transition-all duration-300 md:-translate-y-2 ${
                  currentPlan === 'pro'
                    ? 'border-2 border-[#C49A61] shadow-[0_0_35px_rgba(196,154,97,0.35)]'
                    : 'border-2 border-[#C49A61]/70 shadow-[0_0_25px_rgba(196,154,97,0.18)] hover:border-[#C49A61]'
                }`}>
                  {/* "MOST POPULAR" Ribbon Label */}
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-gradient-to-r from-[#C49A61] via-[#E2B77D] to-[#C49A61] text-[#120D08] font-sans text-[11px] font-extrabold uppercase tracking-widest shadow-md flex items-center gap-1.5 whitespace-nowrap">
                    <Sparkles className="w-3 h-3 text-[#120D08]" />
                    <span>Most Popular</span>
                  </div>

                  <div className="space-y-4 pt-1">
                    {/* Badge & Plan Name */}
                    <div className="flex items-center justify-between">
                      <span className="px-2.5 py-1 rounded-md text-xs font-typewriter font-bold tracking-widest uppercase bg-[#C49A61]/20 text-[#F3D4A0] border border-[#C49A61]/50">
                        PRO
                      </span>
                      {currentPlan === 'pro' && (
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-sans font-bold uppercase tracking-wider bg-[#C49A61]/25 text-[#F5EDE3] border border-[#C49A61]/50">
                          Active Tier
                        </span>
                      )}
                    </div>

                    <div>
                      <h3 className="font-serif font-bold text-2xl text-[#F4ECE2] flex items-center gap-2">
                        <span>{SUBSCRIPTION_PLANS.pro.name}</span>
                        <Gem className="w-5 h-5 text-[#C49A61]" />
                      </h3>
                      <p className="text-xs text-[#C49A61] font-serif italic mt-1 leading-relaxed">
                        {SUBSCRIPTION_PLANS.pro.tagline}
                      </p>
                    </div>

                    {/* Price Display - Simultaneous INR + USD */}
                    <div className="py-4 my-2 border-y border-[#3E2E20] bg-[#140E0A]/70 -mx-6 sm:-mx-7 px-6 sm:px-7 rounded-sm">
                      {/* Primary: INR */}
                      <div className="flex items-baseline gap-2 flex-wrap">
                        <span className="font-serif text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#F4ECE2] tracking-tight">
                          ₹{formatPriceINR(SUBSCRIPTION_PLANS.pro.priceINR)}
                        </span>
                        <span className="text-xs font-sans font-bold uppercase tracking-wider text-[#C49A61]">
                          INR
                        </span>
                        <span className="text-xs sm:text-sm font-sans font-semibold text-[#A89886]">
                          / month
                        </span>
                      </div>

                      {/* Secondary: USD (Smaller, Muted Text) */}
                      <div className="flex items-center gap-1.5 mt-1.5 text-xs text-[#A89886] font-sans">
                        <span className="font-medium text-[#D8CCC0]">
                          ~ ${formatPriceUSD(SUBSCRIPTION_PLANS.pro.priceUSD)} USD
                        </span>
                        <span className="text-[11px] text-[#78695A]">
                          per month (approx.)
                        </span>
                      </div>
                      <p className="text-[11px] font-sans text-[#C49A61] mt-1.5">Billed monthly in INR • Introductory pricing</p>
                    </div>

                    {/* Features List */}
                    <div className="space-y-2.5 pt-1">
                      <span className="text-[11px] font-sans font-bold uppercase tracking-wider text-[#C49A61] block">
                        Everything in Free, plus:
                      </span>
                      <ul className="space-y-2 text-xs text-[#EADFCF]">
                        {SUBSCRIPTION_PLANS.pro.features.map((feat, idx) => (
                          <li key={idx} className="flex items-start gap-2.5">
                            <Check className="w-4 h-4 text-[#C49A61] shrink-0 mt-0.5" />
                            <span className="leading-tight">{feat.text}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* CTA Button */}
                  <div className="pt-6 mt-6 border-t border-[#3E2E20]">
                    <button
                      onClick={() => handleSelectPlan('pro')}
                      className={`w-full py-3.5 rounded-xl font-sans text-xs sm:text-sm font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 shadow-lg ${
                        currentPlan === 'pro'
                          ? 'bg-[#2A1E14] text-[#C49A61] border border-[#C49A61] cursor-default'
                          : 'bg-gradient-to-r from-[#C49A61] via-[#D8AC74] to-[#C49A61] hover:brightness-110 text-[#120D08] cursor-pointer'
                      }`}
                    >
                      <span>{currentPlan === 'pro' ? 'Current Plan' : 'Upgrade to Pro'}</span>
                      {currentPlan !== 'pro' && <ArrowRight className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* ── PLAN 3: ULTRA (EXCLUSIVE) ── */}
                <div className={`relative rounded-2xl bg-gradient-to-b from-[#1F1710] to-[#16100B] p-6 sm:p-7 flex flex-col justify-between transition-all duration-300 md:-translate-y-2 ${
                  currentPlan === 'ultra'
                    ? 'border-2 border-[#D4AF37] shadow-[0_0_40px_rgba(212,175,55,0.4)]'
                    : 'border-2 border-[#D4AF37]/70 hover:border-[#D4AF37] shadow-[0_0_25px_rgba(212,175,55,0.2)]'
                }`}>
                  {/* "ANIMATION INCLUDED" Ribbon Label */}
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-gradient-to-r from-[#D4AF37] via-[#F3D4A0] to-[#D4AF37] text-[#120D08] font-sans text-[11px] font-extrabold uppercase tracking-widest shadow-lg flex items-center gap-1.5 whitespace-nowrap">
                    <Film className="w-3.5 h-3.5 text-[#120D08]" />
                    <span>Animation Included</span>
                  </div>

                  {/* Exclusive Ultra Accent corner glow */}
                  <div className="absolute top-0 right-0 w-32 h-32 bg-[#D4AF37]/10 rounded-full blur-2xl pointer-events-none" />

                  <div className="space-y-4 pt-1">
                    {/* Badge & Plan Name */}
                    <div className="flex items-center justify-between">
                      <span className="px-2.5 py-1 rounded-md text-xs font-typewriter font-bold tracking-widest uppercase bg-gradient-to-r from-[#D4AF37]/25 to-[#8C6D3E]/25 text-[#F5EDE3] border border-[#D4AF37]/50 flex items-center gap-1.5">
                        <Crown className="w-3 h-3 text-[#D4AF37]" />
                        ULTRA
                      </span>
                      {currentPlan === 'ultra' && (
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-sans font-bold uppercase tracking-wider bg-[#D4AF37]/25 text-[#F5EDE3] border border-[#D4AF37]/60">
                          Active Tier
                        </span>
                      )}
                    </div>

                    <div>
                      <h3 className="font-serif font-bold text-2xl text-[#F4ECE2] flex items-center gap-2">
                        <span>{SUBSCRIPTION_PLANS.ultra.name}</span>
                        <Sparkles className="w-5 h-5 text-[#D4AF37]" />
                      </h3>
                      <p className="text-xs text-[#E0C08A] font-serif italic mt-1 leading-relaxed">
                        {SUBSCRIPTION_PLANS.ultra.tagline}
                      </p>
                    </div>

                    {/* Price Display - Simultaneous INR + USD */}
                    <div className="py-4 my-2 border-y border-[#3E2E20] bg-[#140E0A]/70 -mx-6 sm:-mx-7 px-6 sm:px-7 rounded-sm">
                      {/* Primary: INR */}
                      <div className="flex items-baseline gap-2 flex-wrap">
                        <span className="font-serif text-3xl sm:text-4xl lg:text-5xl font-extrabold text-[#F4ECE2] tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-[#F5EDE3] via-[#F3D4A0] to-[#E0C08A]">
                          ₹{formatPriceINR(SUBSCRIPTION_PLANS.ultra.priceINR)}
                        </span>
                        <span className="text-xs font-sans font-bold uppercase tracking-wider text-[#E0C08A]">
                          INR
                        </span>
                        <span className="text-xs sm:text-sm font-sans font-semibold text-[#A89886]">
                          / month
                        </span>
                      </div>

                      {/* Secondary: USD (Smaller, Muted Text) */}
                      <div className="flex items-center gap-1.5 mt-1.5 text-xs text-[#A89886] font-sans">
                        <span className="font-medium text-[#E0C08A]">
                          ~ ${formatPriceUSD(SUBSCRIPTION_PLANS.ultra.priceUSD)} USD
                        </span>
                        <span className="text-[11px] text-[#78695A]">
                          per month (approx.)
                        </span>
                      </div>
                      <p className="text-[11px] font-sans text-[#E0C08A] mt-1.5">Billed monthly in INR • Exclusive Story Animation</p>
                    </div>

                    {/* Features List */}
                    <div className="space-y-2.5 pt-1">
                      <span className="text-[11px] font-sans font-bold uppercase tracking-wider text-[#E0C08A] block">
                        Everything in Pro, plus:
                      </span>
                      <ul className="space-y-2 text-xs text-[#EADFCF]">
                        {SUBSCRIPTION_PLANS.ultra.features.map((feat, idx) => (
                          <li key={idx} className="flex items-start gap-2.5">
                            {feat.isExclusive ? (
                              <div className="w-4 h-4 rounded-full bg-[#D4AF37]/20 border border-[#D4AF37] flex items-center justify-center shrink-0 mt-0.5">
                                <Film className="w-2.5 h-2.5 text-[#F3D4A0]" />
                              </div>
                            ) : (
                              <Check className="w-4 h-4 text-[#D4AF37] shrink-0 mt-0.5" />
                            )}
                            <span className={feat.isExclusive ? "font-bold text-[#F3D4A0]" : "leading-tight"}>
                              {feat.text}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* CTA Button */}
                  <div className="pt-6 mt-6 border-t border-[#3E2E20]">
                    <button
                      onClick={() => handleSelectPlan('ultra')}
                      className={`w-full py-3.5 rounded-xl font-sans text-xs sm:text-sm font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 shadow-lg ${
                        currentPlan === 'ultra'
                          ? 'bg-[#2E2217] text-[#D4AF37] border border-[#D4AF37] cursor-default'
                          : 'bg-gradient-to-r from-[#D4AF37] via-[#E8C56B] to-[#B38F2D] hover:brightness-110 text-[#120D08] cursor-pointer'
                      }`}
                    >
                      <span>{currentPlan === 'ultra' ? 'Current Plan' : 'Unlock Ultra'}</span>
                      {currentPlan !== 'ultra' && <Crown className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

              </div>

              {/* Currency Assurance Note */}
              <div className="flex items-center justify-center gap-2 py-1 text-xs font-sans text-[#A89886] text-center px-4">
                <span className="text-[#C49A61]">✦</span>
                <span className="font-medium tracking-wide">
                  USD prices are approximate and may vary with exchange rates. Billed in INR.
                </span>
                <span className="text-[#C49A61]">✦</span>
              </div>

              {/* SECTION 4: STORY ANIMATION — ULTRA EXCLUSIVE FEATURE SPOTLIGHT */}
              <div 
                onClick={handleOpenAnimationPrompt}
                className="relative rounded-2xl overflow-hidden border border-[#D4AF37]/50 bg-gradient-to-r from-[#20160F] via-[#2A1E14] to-[#20160F] p-5 sm:p-7 shadow-xl cursor-pointer group hover:border-[#D4AF37] transition-all"
              >
                <div className="flex flex-col md:flex-row items-center justify-between gap-5 relative z-10">
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#D4AF37] to-[#8C6D3E] p-0.5 shadow-md flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
                      <div className="w-full h-full bg-[#1A120D] rounded-[10px] flex items-center justify-center">
                        <Film className="w-6 h-6 text-[#F3D4A0]" />
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <span className="font-serif font-bold text-lg sm:text-xl text-[#F4ECE2]">
                          Story Animation
                        </span>
                        <span className="px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest bg-gradient-to-r from-[#D4AF37]/25 to-[#8C6D3E]/25 text-[#F5EDE3] border border-[#D4AF37]/60 rounded-full flex items-center gap-1">
                          <Crown className="w-3 h-3 text-[#D4AF37]" />
                          Ultra Exclusive
                        </span>
                      </div>
                      <p className="text-xs sm:text-sm text-[#A89886] max-w-2xl leading-relaxed">
                        Transform your written chapters and scenes into living animated animatics. Powered by scene blocking, character rigging, and dynamic cinematic lighting.
                      </p>
                    </div>
                  </div>

                  {/* Status Indicator / Action */}
                  <div className="shrink-0">
                    {currentPlan === 'ultra' ? (
                      <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#281D14] border border-[#D4AF37]/60 text-xs font-bold text-[#F3D4A0]">
                        <Unlock className="w-4 h-4 text-[#D4AF37]" />
                        <span>Unlocked & Active</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#19110B] border border-[#523B27] group-hover:border-[#D4AF37] text-xs font-bold text-[#E5BA78] transition-colors shadow">
                        <Lock className="w-4 h-4 text-[#D4AF37]" />
                        <span>Preview Feature Demo</span>
                        <ArrowRight className="w-3.5 h-3.5 text-[#D4AF37] group-hover:translate-x-0.5 transition-transform" />
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* SECTION 5: PLAN COMPARISON MATRIX */}
              <div className="space-y-4 pt-2">
                <div className="border-b border-[#36271D] pb-3 flex items-center justify-between">
                  <div>
                    <h3 className="font-serif font-bold text-xl text-[#F4ECE2]">
                      Detailed Capabilities Comparison
                    </h3>
                    <p className="text-xs text-[#8C7A68]">
                      Comprehensive breakdown of writing limits and investigation permissions across tiers.
                    </p>
                  </div>
                  <ShieldCheck className="w-5 h-5 text-[#C49A61] shrink-0" />
                </div>

                {/* Comparison Table with Responsive Scroll */}
                <div className="w-full overflow-x-auto rounded-xl border border-[#34261C] bg-[#140F0C] shadow-inner">
                  <table className="w-full text-left text-xs min-w-[620px]">
                    <thead>
                      <tr className="bg-[#1D1611] border-b border-[#34261C] text-[#C49A61] font-serif font-bold text-sm">
                        <th className="py-3.5 px-4 sm:px-6">Investigation Feature</th>
                        <th className="py-3.5 px-4 text-center">Free</th>
                        <th className="py-3.5 px-4 text-center text-[#E5BA78] bg-[#C49A61]/10 border-x border-[#34261C]">
                          Pro (Popular)
                        </th>
                        <th className="py-3.5 px-4 text-center text-[#F3D4A0]">Ultra (Exclusive)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#261B13]">
                      {COMPARISON_TABLE.map((row, idx) => (
                        <tr 
                          key={idx}
                          className={`hover:bg-[#1C140E] transition-colors ${row.isUltraExclusive ? 'bg-[#22160E]/40' : ''}`}
                        >
                          <td className="py-3.5 px-4 sm:px-6">
                            <div className="font-medium text-[#F4ECE2] flex items-center gap-1.5">
                              <span>{row.feature}</span>
                              {row.isUltraExclusive && (
                                <span className="px-1.5 py-0.2 rounded text-[9px] font-bold uppercase bg-[#D4AF37]/20 text-[#D4AF37] border border-[#D4AF37]/40">
                                  Ultra
                                </span>
                              )}
                            </div>
                            {row.description && (
                              <p className="text-[11px] text-[#8C7A68] mt-0.5 leading-snug">
                                {row.description}
                              </p>
                            )}
                          </td>

                          {/* Free Column */}
                          <td className="py-3.5 px-4 text-center text-[#B09E8C]">
                            {row.free === 'Included' ? (
                              <span className="inline-flex items-center gap-1 text-[#8C7A68] font-medium">
                                <Check className="w-4 h-4 text-[#8C7A68]" /> Included
                              </span>
                            ) : row.free === 'Locked' ? (
                              <span className="inline-flex items-center gap-1 text-[#665342]">
                                <Lock className="w-3.5 h-3.5" /> Locked
                              </span>
                            ) : (
                              <span>{row.free}</span>
                            )}
                          </td>

                          {/* Pro Column */}
                          <td className="py-3.5 px-4 text-center text-[#EDE3D6] bg-[#C49A61]/5 border-x border-[#34261C]">
                            {row.pro === 'Included' ? (
                              <span className="inline-flex items-center gap-1 text-[#C49A61] font-semibold">
                                <Check className="w-4 h-4 text-[#C49A61]" /> Included
                              </span>
                            ) : row.pro === 'Locked' ? (
                              <span 
                                onClick={handleOpenAnimationPrompt}
                                className="inline-flex items-center gap-1 text-[#8C7A68] hover:text-[#C49A61] cursor-pointer"
                                title="Click to view Ultra upgrade"
                              >
                                <Lock className="w-3.5 h-3.5" /> Locked
                              </span>
                            ) : (
                              <span className="font-semibold text-[#E0B77D]">{row.pro}</span>
                            )}
                          </td>

                          {/* Ultra Column */}
                          <td className="py-3.5 px-4 text-center text-[#F4ECE2]">
                            {row.ultra === 'Included' ? (
                              <span className="inline-flex items-center gap-1 text-[#D4AF37] font-bold">
                                <Check className="w-4 h-4 text-[#D4AF37]" /> Included
                              </span>
                            ) : row.ultra === 'Exclusive' ? (
                              <button
                                onClick={handleOpenAnimationPrompt}
                                className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-[#D4AF37]/20 border border-[#D4AF37]/60 text-[#F3D4A0] font-bold hover:brightness-110 transition-all cursor-pointer"
                              >
                                <Sparkles className="w-3.5 h-3.5 text-[#D4AF37]" />
                                <span>Exclusive</span>
                              </button>
                            ) : (
                              <span className="font-bold text-[#F3D4A0]">{row.ultra}</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Victorian Assurance Footer */}
              <div className="pt-4 border-t border-[#2C2117] flex flex-col sm:flex-row items-center justify-between text-xs text-[#8C7A68] gap-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-[#C49A61]" />
                  <span>Encrypted manuscript storage. USD prices are approximate and may vary with exchange rates. Private universe memory isolation.</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="hover:text-[#EDE3D6] cursor-pointer">Terms of Service</span>
                  <span>•</span>
                  <span className="hover:text-[#EDE3D6] cursor-pointer">Privacy Canon</span>
                  <span>•</span>
                  <span className="hover:text-[#EDE3D6] cursor-pointer">Billing Support</span>
                </div>
              </div>

            </div>
          </motion.div>
        </div>
      </AnimatePresence>

      {/* Story Animation Dedicated Upgrade Modal */}
      <StoryAnimationModal
        isOpen={animationModalOpen}
        onClose={() => setAnimationModalOpen(false)}
        currentPlan={currentPlan}
        onUpgradeToUltra={() => handleSelectPlan('ultra')}
      />
    </>
  );
};
