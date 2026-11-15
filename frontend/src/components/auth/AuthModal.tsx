import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth, AuthModalMode } from '../../context/AuthContext';
import { sound } from '../../services/audioService';
import { 
  X, 
  Key, 
  User, 
  Mail, 
  Lock, 
  Eye, 
  EyeOff, 
  AlertCircle, 
  CheckCircle2, 
  ArrowRight, 
  ShieldCheck, 
  Sparkles 
} from 'lucide-react';

export const AuthModal: React.FC = () => {
  const {
    user,
    profile,
    authModalOpen,
    authModalMode,
    pendingGoogleUser,
    accountNotFoundMsg,
    closeAuthModal,
    setAuthModalMode,
    clearAccountNotFound,
    signUpWithEmail,
    signInWithEmail,
    signInWithGoogle,
    submitUsername,
    submitGoogleUsername,
    resetPassword
  } = useAuth();

  // Form states
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Auto-close modal and clear processing state as soon as user is authenticated with a profile
  useEffect(() => {
    if (user && authModalOpen) {
      if (profile?.username || authModalMode !== 'username_prompt') {
        setSubmitting(false);
        closeAuthModal();
      }
    }
  }, [user, profile, authModalOpen, authModalMode, closeAuthModal]);

  // Reset form when modal opens or mode changes
  useEffect(() => {
    if (authModalOpen) {
      setSubmitting(false);
      setErrorMessage(null);
      setSuccessMessage(null);
      setPassword('');
      setConfirmPassword('');
      setShowPassword(false);
      if (authModalMode !== 'username_prompt') {
        setUsername('');
      }
    }
  }, [authModalOpen, authModalMode]);

  // Synchronize account not found message
  useEffect(() => {
    if (accountNotFoundMsg) {
      setErrorMessage(accountNotFoundMsg);
    }
  }, [accountNotFoundMsg]);

  if (!authModalOpen) return null;

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget && authModalMode !== 'username_prompt') {
      sound.playPaperRustle();
      closeAuthModal();
    }
  };

  const handleClose = () => {
    sound.playPaperRustle();
    closeAuthModal();
  };

  const switchMode = (mode: AuthModalMode) => {
    sound.playPaperRustle();
    clearAccountNotFound();
    setErrorMessage(null);
    setSuccessMessage(null);
    setAuthModalMode(mode);
  };

  // Submit Handler
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;

    setErrorMessage(null);
    setSuccessMessage(null);
    sound.playTypewriterKeystroke();

    try {
      setSubmitting(true);

      if (authModalMode === 'signin') {
        await signInWithEmail(email, password);
        sound.playPaperRustle();
        closeAuthModal();
      } else if (authModalMode === 'signup') {
        if (password !== confirmPassword) {
          throw new Error("Passwords do not match. Please re-enter.");
        }
        await signUpWithEmail(email, password, username);
        sound.playPaperRustle();
        closeAuthModal();
      } else if (authModalMode === 'forgot') {
        await resetPassword(email);
        setSuccessMessage(`Password reset instructions have been dispatched to ${email.trim()}. Please inspect your inbox.`);
        sound.playPaperRustle();
      } else if (authModalMode === 'username_prompt') {
        const fn = submitUsername || submitGoogleUsername;
        await fn(username);
        sound.playPaperRustle();
        closeAuthModal();
      }
    } catch (err: any) {
      setErrorMessage(err.message || "An authentication error occurred.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleGoogleAuth = async () => {
    if (submitting) return;
    sound.playTypewriterKeystroke();
    setErrorMessage(null);
    setSuccessMessage(null);
    try {
      setSubmitting(true);
      await signInWithGoogle();
    } catch (err: any) {
      setErrorMessage(err.message || "Google authentication encountered an interruption.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div 
      onClick={handleBackdropClick}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md transition-opacity select-none"
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.94, y: 15 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.94, y: 15 }}
        transition={{ duration: 0.22, ease: "easeOut" }}
        className="relative w-full max-w-md rounded-2xl bg-[#18120C]/95 border-2 border-[#8C6F48] shadow-[0_12px_60px_rgba(0,0,0,0.9),0_0_30px_rgba(196,154,97,0.2)] overflow-hidden"
      >
        {/* Top Gold Border Ornament */}
        <div className="h-1.5 w-full bg-gradient-to-r from-[#6B4E2B] via-[#F3D4A0] to-[#6B4E2B]" />

        {/* Close Button (hidden during mandatory username prompt) */}
        {authModalMode !== 'username_prompt' && (
          <button
            type="button"
            onClick={handleClose}
            className="absolute top-4 right-4 p-1.5 rounded-full text-[#A69482] hover:text-[#F3D4A0] hover:bg-[#2B2016] transition-colors z-20"
            title="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        )}

        <div className="p-6 sm:p-7 space-y-5">
          {/* Header */}
          <div className="space-y-1 text-center">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#C49A61]/15 border border-[#C49A61]/35 text-[#E0B77D] text-[10px] font-typewriter uppercase tracking-widest font-bold">
              <Sparkles className="w-3 h-3 text-[#C49A61]" />
              {authModalMode === 'signin' && "MYTHORA ARCHIVES • SIGN IN"}
              {authModalMode === 'signup' && "OFFICIAL REGISTRATION"}
              {authModalMode === 'forgot' && "CREDENTIAL RECOVERY"}
              {authModalMode === 'username_prompt' && "INVESTIGATOR IDENTITY"}
            </div>

            <h2 className="font-serif text-2xl sm:text-[26px] font-bold text-[#F4ECE2] tracking-wide">
              {authModalMode === 'signin' && "Sign In to Mythora"}
              {authModalMode === 'signup' && "Create an Account"}
              {authModalMode === 'forgot' && "Reset Your Password"}
              {authModalMode === 'username_prompt' && "Choose Your Username"}
            </h2>

            <p className="font-sans text-xs text-[#A89886] max-w-xs mx-auto leading-relaxed">
              {authModalMode === 'signin' && "Unlock your case dossiers, narrative timelines, and writing studio."}
              {authModalMode === 'signup' && "Register your unique investigator identity to protect your manuscripts."}
              {authModalMode === 'forgot' && "Enter your registered email address to receive dispatch instructions."}
              {authModalMode === 'username_prompt' && "Choose a permanent unique investigator alias for your dossiers."}
            </p>
          </div>

          {/* Account Not Found Alert Banner (Specific Requirement #5) */}
          {accountNotFoundMsg && authModalMode === 'signin' && (
            <div className="p-3.5 rounded-xl bg-[#2A1412] border border-[#8C2E24] shadow-md space-y-2 text-left">
              <div className="flex items-start gap-2.5">
                <AlertCircle className="w-5 h-5 text-[#E74C3C] shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="font-sans text-xs font-semibold text-[#FADBD8] leading-snug">
                    {accountNotFoundMsg}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => switchMode('signup')}
                className="w-full mt-1 py-1.5 px-3 rounded-lg bg-[#8C2E24] hover:bg-[#B03A2E] text-white text-xs font-sans font-bold uppercase tracking-wider transition-colors flex items-center justify-center gap-1.5 shadow"
              >
                <span>Create an Account Now</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* General Error Alert */}
          {errorMessage && (!accountNotFoundMsg || authModalMode !== 'signin') && (
            <div className="p-3 rounded-lg bg-[#2A1412] border border-[#8C2E24] text-xs text-[#E5A8A3] flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-[#E74C3C] shrink-0" />
              <span className="leading-tight">{errorMessage}</span>
            </div>
          )}

          {/* Success Alert */}
          {successMessage && (
            <div className="p-3 rounded-lg bg-[#142618] border border-[#2E6B38] text-xs text-[#A8E6B0] flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-[#2ECC71] shrink-0" />
              <span className="leading-tight">{successMessage}</span>
            </div>
          )}

          {/* First-Time User Banner */}
          {authModalMode === 'username_prompt' && (pendingGoogleUser || user) && (
            <div className="flex items-center gap-3 p-2.5 rounded-lg bg-[#231A12] border border-[#3E3123]">
              {(pendingGoogleUser?.photoURL || user?.photoURL) ? (
                <img 
                  src={pendingGoogleUser?.photoURL || user?.photoURL || ''} 
                  alt="Profile" 
                  className="w-8 h-8 rounded-full border border-[#C49A61]" 
                />
              ) : (
                <div className="w-8 h-8 rounded-full bg-[#C49A61]/20 border border-[#C49A61] flex items-center justify-center text-xs font-bold text-[#E0B77D]">
                  {((pendingGoogleUser?.displayName || user?.displayName || user?.email || 'I')[0]).toUpperCase()}
                </div>
              )}
              <div className="overflow-hidden">
                <p className="font-sans text-xs font-bold text-[#F4ECE2] truncate">
                  {pendingGoogleUser?.displayName || user?.displayName || 'Investigator'}
                </p>
                <p className="font-sans text-[11px] text-[#A89886] truncate">
                  {pendingGoogleUser?.email || user?.email}
                </p>
              </div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-3.5">
            {/* Username (Mandatory on Signup & Google Prompt) */}
            {(authModalMode === 'signup' || authModalMode === 'username_prompt') && (
              <div className="space-y-1 text-left">
                <label className="block text-xs font-typewriter font-bold uppercase tracking-wider text-[#C49A61]">
                  Username <span className="text-[#E74C3C]">*</span>
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#8C7A68]" />
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="e.g. MasterHolmes_42"
                    minLength={3}
                    maxLength={25}
                    className="w-full pl-9 pr-3 py-2.5 rounded-lg bg-[#140E0A] border border-[#4A3B2C] focus:border-[#C49A61] focus:ring-1 focus:ring-[#C49A61] text-[#F4ECE2] text-xs font-sans placeholder-[#685A4C] outline-none transition-all"
                  />
                </div>
                <p className="text-[10px] font-sans text-[#7A6A59]">
                  3–25 characters. Letters, numbers, underscores. Case-insensitive unique.
                </p>
              </div>
            )}

            {/* Email (Signin, Signup, Forgot) */}
            {authModalMode !== 'username_prompt' && (
              <div className="space-y-1 text-left">
                <label className="block text-xs font-typewriter font-bold uppercase tracking-wider text-[#C49A61]">
                  Email Address <span className="text-[#E74C3C]">*</span>
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#8C7A68]" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="investigator@mythora.studio"
                    className="w-full pl-9 pr-3 py-2.5 rounded-lg bg-[#140E0A] border border-[#4A3B2C] focus:border-[#C49A61] focus:ring-1 focus:ring-[#C49A61] text-[#F4ECE2] text-xs font-sans placeholder-[#685A4C] outline-none transition-all"
                  />
                </div>
              </div>
            )}

            {/* Password (Signin & Signup) */}
            {(authModalMode === 'signin' || authModalMode === 'signup') && (
              <div className="space-y-1 text-left">
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-typewriter font-bold uppercase tracking-wider text-[#C49A61]">
                    Password <span className="text-[#E74C3C]">*</span>
                  </label>
                  {authModalMode === 'signin' && (
                    <button
                      type="button"
                      onClick={() => switchMode('forgot')}
                      className="text-[11px] font-sans text-[#C49A61] hover:text-[#F3D4A0] hover:underline"
                    >
                      Forgot Password?
                    </button>
                  )}
                </div>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#8C7A68]" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    minLength={6}
                    className="w-full pl-9 pr-10 py-2.5 rounded-lg bg-[#140E0A] border border-[#4A3B2C] focus:border-[#C49A61] focus:ring-1 focus:ring-[#C49A61] text-[#F4ECE2] text-xs font-sans placeholder-[#685A4C] outline-none transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#8C7A68] hover:text-[#E0B77D] transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {authModalMode === 'signup' && (
                  <p className="text-[10px] font-sans text-[#7A6A59]">
                    Minimum 6 characters. Must contain letters and numbers.
                  </p>
                )}
              </div>
            )}

            {/* Confirm Password (Signup only) */}
            {authModalMode === 'signup' && (
              <div className="space-y-1 text-left">
                <label className="block text-xs font-typewriter font-bold uppercase tracking-wider text-[#C49A61]">
                  Confirm Password <span className="text-[#E74C3C]">*</span>
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#8C7A68]" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    minLength={6}
                    className="w-full pl-9 pr-10 py-2.5 rounded-lg bg-[#140E0A] border border-[#4A3B2C] focus:border-[#C49A61] focus:ring-1 focus:ring-[#C49A61] text-[#F4ECE2] text-xs font-sans placeholder-[#685A4C] outline-none transition-all"
                  />
                </div>
              </div>
            )}

            {/* Primary Submit Button */}
            <button
              type="submit"
              disabled={submitting}
              className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-[#C49A61] via-[#DDB47D] to-[#C49A61] hover:brightness-110 active:scale-[0.98] text-[#140E0A] font-sans text-xs sm:text-sm font-bold uppercase tracking-wider shadow-lg transition-all disabled:opacity-50 flex items-center justify-center gap-2 mt-2"
            >
              {submitting ? (
                <>
                  <span className="w-4 h-4 border-2 border-[#140E0A] border-t-transparent rounded-full animate-spin" />
                  <span>Processing Dossier...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" />
                  <span>
                    {authModalMode === 'signin' && "Sign In"}
                    {authModalMode === 'signup' && "Create Account"}
                    {authModalMode === 'forgot' && "Send Reset Link"}
                    {authModalMode === 'username_prompt' && "Confirm Username & Enter"}
                  </span>
                </>
              )}
            </button>
          </form>

          {/* Social Auth (Google Sign-In) */}
          {(authModalMode === 'signin' || authModalMode === 'signup') && (
            <div className="space-y-3 pt-1">
              <div className="relative flex items-center justify-center">
                <div className="border-t border-[#3E3123] w-full" />
                <span className="bg-[#18120C] px-3 font-typewriter text-[10px] text-[#7A6A59] uppercase tracking-widest shrink-0">
                  Or Continue With
                </span>
                <div className="border-t border-[#3E3123] w-full" />
              </div>

              <button
                type="button"
                onClick={handleGoogleAuth}
                disabled={submitting}
                className="w-full py-2.5 px-4 rounded-xl bg-[#231A12] hover:bg-[#2C2117] border border-[#4A3B2C] hover:border-[#C49A61]/60 text-[#F4ECE2] font-sans text-xs font-bold transition-all flex items-center justify-center gap-2.5 shadow-sm active:scale-[0.98] disabled:opacity-50"
              >
                {/* Official Google 'G' Icon */}
                <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  />
                </svg>
                <span>Continue with Google</span>
              </button>
            </div>
          )}

          {/* Mode Switchers */}
          <div className="pt-2 text-center text-xs font-sans text-[#8C7A68]">
            {authModalMode === 'signin' && (
              <p>
                Don't have an investigator account?{' '}
                <button
                  type="button"
                  onClick={() => switchMode('signup')}
                  className="font-bold text-[#E0B77D] hover:text-[#F3D4A0] hover:underline ml-1"
                >
                  Create an Account
                </button>
              </p>
            )}

            {authModalMode === 'signup' && (
              <p>
                Already hold an active dossier?{' '}
                <button
                  type="button"
                  onClick={() => switchMode('signin')}
                  className="font-bold text-[#E0B77D] hover:text-[#F3D4A0] hover:underline ml-1"
                >
                  Sign In
                </button>
              </p>
            )}

            {authModalMode === 'forgot' && (
              <p>
                Remembered your credentials?{' '}
                <button
                  type="button"
                  onClick={() => switchMode('signin')}
                  className="font-bold text-[#E0B77D] hover:text-[#F3D4A0] hover:underline ml-1"
                >
                  Return to Sign In
                </button>
              </p>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  );
};
