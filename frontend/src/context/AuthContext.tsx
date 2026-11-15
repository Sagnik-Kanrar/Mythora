import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import {
  auth,
  googleProvider,
  UserProfile,
  isUsernameAvailable,
  checkEmailRegistered,
  saveUserProfile,
  getUserProfile,
  updateLastLogin,
  getCachedProfile,
  setCachedProfile,
  clearCachedProfile
} from '../services/firebase';
import {
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  sendPasswordResetEmail,
  updateProfile,
  onAuthStateChanged,
  User as FirebaseUser
} from 'firebase/auth';

export type AuthModalMode = 'signin' | 'signup' | 'forgot' | 'username_prompt';

/**
 * Check if the browser holds a previously authenticated Firebase session or cached profile
 */
export function hasStoredAuthSession(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    if (localStorage.getItem('mythora_has_authenticated_session') === 'true') {
      return true;
    }
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && (key.startsWith('firebase:authUser') || key.startsWith('mythora_user_profile_'))) {
        return true;
      }
    }
  } catch {}
  return false;
}

interface AuthContextType {
  user: FirebaseUser | null;
  profile: UserProfile | null;
  loading: boolean;
  isRestoringSession: boolean;
  authModalOpen: boolean;
  authModalMode: AuthModalMode;
  pendingGoogleUser: FirebaseUser | null;
  accountNotFoundMsg: string | null;
  openAuthModal: (mode?: AuthModalMode) => void;
  closeAuthModal: () => void;
  setAuthModalMode: (mode: AuthModalMode) => void;
  clearAccountNotFound: () => void;
  signUpWithEmail: (email: string, pass: string, username: string) => Promise<void>;
  signInWithEmail: (email: string, pass: string) => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  submitUsername: (username: string) => Promise<void>;
  submitGoogleUsername: (username: string) => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  signOutUser: () => Promise<void>;
  getIdToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<FirebaseUser | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isRestoringSession, setIsRestoringSession] = useState<boolean>(() => {
    return hasStoredAuthSession();
  });
  const [authModalOpen, setAuthModalOpen] = useState<boolean>(false);
  const [authModalMode, setAuthModalMode] = useState<AuthModalMode>('signin');
  const [pendingGoogleUser, setPendingGoogleUser] = useState<FirebaseUser | null>(null);
  const [accountNotFoundMsg, setAccountNotFoundMsg] = useState<string | null>(null);

  // Restore session persistently on reload using Firebase UID as permanent identity
  useEffect(() => {
    let isMounted = true;

    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      // If a stored session is being verified for a returning user, ensure indicator is active
      if (currentUser && !profile) {
        if (isMounted) setIsRestoringSession(true);
      }

      setUser(currentUser);
      if (currentUser) {
        try {
          try {
            localStorage.setItem('mythora_has_authenticated_session', 'true');
          } catch {}

          // 1. Primary lookup by UID in Firestore
          let loadedProfile = await getUserProfile(currentUser.uid);

          // 2. If not found in Firestore, check local storage cache
          if (!loadedProfile || !loadedProfile.username) {
            loadedProfile = getCachedProfile(currentUser.uid);
          }

          // 3. If still missing, check if Firebase Auth has displayName from previous registration
          if ((!loadedProfile || !loadedProfile.username) && currentUser.displayName && currentUser.displayName.trim() !== '') {
            // Self-heal profile and persist in Firestore under users/{uid}
            loadedProfile = await saveUserProfile(currentUser.uid, {
              username: currentUser.displayName.trim(),
              email: currentUser.email || '',
              displayName: currentUser.displayName.trim(),
              photoURL: currentUser.photoURL || null,
              authProvider: currentUser.providerData[0]?.providerId === 'google.com' ? 'google' : 'password'
            });
          }

          if (loadedProfile && loadedProfile.username && loadedProfile.username.trim() !== '') {
            if (isMounted) setProfile(loadedProfile);
            updateLastLogin(currentUser.uid).catch(() => {});
          } else {
            // Missing profile or username
            if (isMounted) setProfile(null);
          }
        } catch (e) {
          console.warn("[Auth] Error fetching profile on auth change:", e);
        }
      } else {
        try {
          localStorage.removeItem('mythora_has_authenticated_session');
        } catch {}
        if (isMounted) setProfile(null);
      }

      if (isMounted) {
        setIsRestoringSession(false);
        setLoading(false);
      }
    });

    return () => {
      isMounted = false;
      unsubscribe();
    };
  }, []);

  const openAuthModal = (mode: AuthModalMode = 'signin') => {
    setAuthModalMode(mode);
    setAccountNotFoundMsg(null);
    setAuthModalOpen(true);
  };

  const closeAuthModal = () => {
    setAuthModalOpen(false);
    setAccountNotFoundMsg(null);
    setPendingGoogleUser(null);
  };

  const clearAccountNotFound = () => {
    setAccountNotFoundMsg(null);
  };

  /**
   * Register with Email, Password & Mandatory Unique Username
   */
  const signUpWithEmail = async (email: string, pass: string, username: string) => {
    const cleanEmail = email.trim().toLowerCase();
    const cleanUsername = username.trim();

    // 1. Mandatory Username validation
    const usernameCheck = await isUsernameAvailable(cleanUsername);
    if (!usernameCheck.available) {
      throw new Error(usernameCheck.error || "Username is not available.");
    }

    // 2. Email format validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(cleanEmail)) {
      throw new Error("Please enter a valid email address.");
    }

    // 3. Password Strength check
    if (pass.length < 6) {
      throw new Error("Password must be at least 6 characters long.");
    }
    if (!/(?=.*[a-zA-Z])(?=.*[0-9])/.test(pass)) {
      throw new Error("Password must contain at least one letter and one number.");
    }

    // 4. Create Firebase Auth account
    const userCredential = await createUserWithEmailAndPassword(auth, cleanEmail, pass);
    const createdUser = userCredential.user;
    setUser(createdUser);

    // 5. Update Firebase Auth displayName
    try {
      await updateProfile(createdUser, { displayName: cleanUsername });
    } catch (e) {
      console.warn("[Auth] Failed to set displayName:", e);
    }

    // 6. Save Profile in Firestore
    const newProfile = await saveUserProfile(createdUser.uid, {
      username: cleanUsername,
      email: cleanEmail,
      displayName: cleanUsername,
      photoURL: null,
      authProvider: 'password'
    });

    setProfile(newProfile);
    closeAuthModal();
  };

  /**
   * Sign In with Email & Password
   */
  const signInWithEmail = async (email: string, pass: string) => {
    const cleanEmail = email.trim().toLowerCase();
    setAccountNotFoundMsg(null);

    if (!cleanEmail) {
      throw new Error("Email address is required.");
    }
    if (!pass) {
      throw new Error("Password is required.");
    }

    try {
      const userCredential = await signInWithEmailAndPassword(auth, cleanEmail, pass);
      const signedInUser = userCredential.user;
      setUser(signedInUser);

      // 1. Look up existing Firestore profile using permanent Firebase UID
      let userProfile = await getUserProfile(signedInUser.uid);

      // 2. Check whether a valid username is already saved
      if (userProfile && userProfile.username && userProfile.username.trim() !== '') {
        // If the username exists, load existing profile and continue directly into Mythora
        setProfile(userProfile);
        updateLastLogin(signedInUser.uid).catch(() => {});
        closeAuthModal();
        return;
      }

      // 3. Fallback / Self-healing: Check local storage cache
      const cached = getCachedProfile(signedInUser.uid);
      if (cached && cached.username && cached.username.trim() !== '') {
        setProfile(cached);
        saveUserProfile(signedInUser.uid, cached).catch(() => {});
        updateLastLogin(signedInUser.uid).catch(() => {});
        closeAuthModal();
        return;
      }

      // 4. Fallback / Self-healing: Check Firebase Auth displayName from registration
      if (signedInUser.displayName && signedInUser.displayName.trim() !== '') {
        const healedProfile = await saveUserProfile(signedInUser.uid, {
          username: signedInUser.displayName.trim(),
          email: cleanEmail,
          displayName: signedInUser.displayName.trim(),
          photoURL: signedInUser.photoURL || null,
          authProvider: 'password'
        });
        setProfile(healedProfile);
        updateLastLogin(signedInUser.uid).catch(() => {});
        closeAuthModal();
        return;
      }

      // 5. If and only if profile is genuinely missing and username is blank:
      // Route to username selection
      setAuthModalMode('username_prompt');
      setAuthModalOpen(true);
    } catch (err: any) {
      const code = err.code || '';
      if (
        code === 'auth/user-not-found' ||
        code === 'auth/invalid-credential' ||
        code === 'auth/invalid-login-credentials'
      ) {
        // Check Firestore database to see if this email has an account
        const exists = await checkEmailRegistered(cleanEmail);
        if (!exists) {
          const notFoundText = "You don't have a Mythora account yet. Please create an account first.";
          setAccountNotFoundMsg(notFoundText);
          throw new Error(notFoundText);
        } else {
          throw new Error("Incorrect password. Please verify your credentials or click 'Forgot Password'.");
        }
      } else if (code === 'auth/wrong-password') {
        throw new Error("Incorrect password. Please verify your credentials or click 'Forgot Password'.");
      } else if (code === 'auth/too-many-requests') {
        throw new Error("Too many unsuccessful attempts. Access temporarily restricted for security. Please try again shortly or reset your password.");
      } else if (code === 'auth/network-request-failed') {
        throw new Error("Network connection error. Please inspect your connection and retry.");
      }
      throw err;
    }
  };

  /**
   * Google Sign-In with official popup
   */
  const signInWithGoogle = async () => {
    setAccountNotFoundMsg(null);
    try {
      const result = await signInWithPopup(auth, googleProvider);
      const googleUser = result.user;
      setUser(googleUser);

      // 1. Look up existing Firestore profile using permanent Firebase UID
      const existingProfile = await getUserProfile(googleUser.uid);
      if (existingProfile && existingProfile.username && existingProfile.username.trim() !== '') {
        // Returning Google user: load existing profile and continue directly into Mythora
        setProfile(existingProfile);
        updateLastLogin(googleUser.uid).catch(() => {});
        closeAuthModal();
        return;
      }

      // 2. Check local storage cache in case of sluggish network
      const cached = getCachedProfile(googleUser.uid);
      if (cached && cached.username && cached.username.trim() !== '') {
        setProfile(cached);
        saveUserProfile(googleUser.uid, cached).catch(() => {});
        updateLastLogin(googleUser.uid).catch(() => {});
        closeAuthModal();
        return;
      }

      // 3. First-time Google user or missing username: prompt for unique username
      setPendingGoogleUser(googleUser);
      setAuthModalMode('username_prompt');
      setAuthModalOpen(true);
    } catch (err: any) {
      if (err.code === 'auth/popup-closed-by-user' || err.code === 'auth/cancelled-popup-request') {
        // User closed the popup, handle gracefully without error toast
        return;
      }
      if (err.code === 'auth/popup-blocked') {
        throw new Error("Google sign-in popup was blocked by browser. Please enable popups for this site.");
      }
      throw err;
    }
  };

  /**
   * Complete First-Time Sign-In with Chosen Unique Username
   */
  const submitUsername = async (username: string) => {
    const cleanUsername = username.trim();
    const targetUser = pendingGoogleUser || user || auth.currentUser;

    if (!targetUser) {
      throw new Error("No authenticated session found. Please sign in again.");
    }

    const check = await isUsernameAvailable(cleanUsername, targetUser.uid);
    if (!check.available) {
      throw new Error(check.error || "Username is not available.");
    }

    // Update Firebase Auth profile
    try {
      await updateProfile(targetUser, { displayName: cleanUsername });
    } catch (e) {
      console.warn("[Auth] Failed to set user displayName:", e);
    }

    // Determine auth provider
    const isGoogle = targetUser.providerData.some(p => p.providerId === 'google.com');

    // Save profile to Firestore under users/{uid} and confirm written
    const newProfile = await saveUserProfile(targetUser.uid, {
      username: cleanUsername,
      email: targetUser.email || '',
      displayName: cleanUsername,
      photoURL: targetUser.photoURL || null,
      authProvider: isGoogle ? 'google' : 'password'
    });

    setProfile(newProfile);
    setPendingGoogleUser(null);
    closeAuthModal();
  };

  const submitGoogleUsername = submitUsername;

  /**
   * Forgot Password / Password Reset Email
   */
  const resetPassword = async (email: string) => {
    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      throw new Error("Please enter your registered email address.");
    }

    try {
      await sendPasswordResetEmail(auth, cleanEmail);
    } catch (err: any) {
      if (err.code === 'auth/user-not-found') {
        throw new Error("No Mythora account associated with this email address.");
      } else if (err.code === 'auth/invalid-email') {
        throw new Error("Please enter a valid email address format.");
      }
      throw err;
    }
  };

  /**
   * Sign Out
   */
  const signOutUser = async () => {
    try {
      if (user) {
        clearCachedProfile(user.uid);
      }
      try {
        localStorage.removeItem('mythora_has_authenticated_session');
      } catch {}
      setIsRestoringSession(false);
      await signOut(auth);
      setUser(null);
      setProfile(null);
      setPendingGoogleUser(null);
    } catch (err: any) {
      console.error("[Auth] Sign out error:", err);
      throw err;
    }
  };

  /**
   * Get fresh Firebase ID Token for backend authentication
   */
  const getIdToken = async (): Promise<string | null> => {
    if (!auth.currentUser) return null;
    try {
      return await auth.currentUser.getIdToken();
    } catch {
      return null;
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        profile,
        loading,
        isRestoringSession,
        authModalOpen,
        authModalMode,
        pendingGoogleUser,
        accountNotFoundMsg,
        openAuthModal,
        closeAuthModal,
        setAuthModalMode,
        clearAccountNotFound,
        signUpWithEmail,
        signInWithEmail,
        signInWithGoogle,
        submitUsername,
        submitGoogleUsername,
        resetPassword,
        signOutUser,
        getIdToken
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
