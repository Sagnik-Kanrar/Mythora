import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import {
  auth,
  googleProvider,
  UserProfile,
  isUsernameAvailable,
  checkEmailRegistered,
  saveUserProfile,
  getUserProfile,
  updateLastLogin
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

interface AuthContextType {
  user: FirebaseUser | null;
  profile: UserProfile | null;
  loading: boolean;
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
  const [authModalOpen, setAuthModalOpen] = useState<boolean>(false);
  const [authModalMode, setAuthModalMode] = useState<AuthModalMode>('signin');
  const [pendingGoogleUser, setPendingGoogleUser] = useState<FirebaseUser | null>(null);
  const [accountNotFoundMsg, setAccountNotFoundMsg] = useState<string | null>(null);

  // Restore session persistently on reload
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      setUser(currentUser);
      if (currentUser) {
        try {
          const loadedProfile = await getUserProfile(currentUser.uid);
          if (loadedProfile && loadedProfile.username) {
            setProfile(loadedProfile);
            updateLastLogin(currentUser.uid).catch(() => {});
          } else {
            // First time Google or missing username
            setProfile(null);
          }
        } catch (e) {
          console.warn("[Auth] Error fetching profile on auth change:", e);
        }
      } else {
        setProfile(null);
      }
      setLoading(false);
    });

    return () => unsubscribe();
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

      // Fetch or sync profile
      let userProfile = await getUserProfile(signedInUser.uid);
      if (!userProfile) {
        // Fallback profile if missing
        userProfile = await saveUserProfile(signedInUser.uid, {
          username: signedInUser.displayName || cleanEmail.split('@')[0],
          email: cleanEmail,
          displayName: signedInUser.displayName || cleanEmail.split('@')[0],
          authProvider: 'password'
        });
      }

      setProfile(userProfile);
      updateLastLogin(signedInUser.uid).catch(() => {});
      closeAuthModal();
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

      // Check whether their profile already exists in Firestore
      const existingProfile = await getUserProfile(googleUser.uid);
      if (existingProfile && existingProfile.username) {
        // Profile exists: sign them in directly without asking for username
        setProfile(existingProfile);
        updateLastLogin(googleUser.uid).catch(() => {});
        closeAuthModal();
      } else {
        // First-time Google user: prompt for unique username
        setPendingGoogleUser(googleUser);
        setAuthModalMode('username_prompt');
        setAuthModalOpen(true);
      }
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
   * Complete First-Time Google Sign-In with Chosen Unique Username
   */
  const submitGoogleUsername = async (username: string) => {
    const cleanUsername = username.trim();
    const targetUser = pendingGoogleUser || user;

    if (!targetUser) {
      throw new Error("No authenticated session found. Please sign in again.");
    }

    const check = await isUsernameAvailable(cleanUsername);
    if (!check.available) {
      throw new Error(check.error || "Username is not available.");
    }

    // Update Firebase Auth profile
    try {
      await updateProfile(targetUser, { displayName: cleanUsername });
    } catch (e) {
      console.warn("[Auth] Failed to set Google user displayName:", e);
    }

    // Save profile to Firestore
    const newProfile = await saveUserProfile(targetUser.uid, {
      username: cleanUsername,
      email: targetUser.email || '',
      displayName: targetUser.displayName || cleanUsername,
      photoURL: targetUser.photoURL || null,
      authProvider: 'google'
    });

    setProfile(newProfile);
    setPendingGoogleUser(null);
    closeAuthModal();
  };

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
