import { initializeApp, getApps, getApp } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  sendPasswordResetEmail,
  updateProfile,
  onAuthStateChanged,
  User as FirebaseUser
} from "firebase/auth";
import {
  getFirestore,
  doc,
  getDoc,
  setDoc,
  updateDoc,
  collection,
  query,
  where,
  getDocs,
  serverTimestamp
} from "firebase/firestore";

const firebaseConfig = {
  apiKey: "AIzaSyAw4iTzwUx7ryV7gYHs4J9OwR7juRdq8xs",
  authDomain: "mythra-d5b52.firebaseapp.com",
  projectId: "mythra-d5b52",
  storageBucket: "mythra-d5b52.firebasestorage.app",
  messagingSenderId: "222598425873",
  appId: "1:222598425873:web:dfb853c72a929be2b2f0b0",
  measurementId: "G-4RFX09EDN6"
};

// Initialize Firebase once
const app = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
export const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({ prompt: 'select_account' });

export interface UserProfile {
  uid: string;
  username: string;
  usernameLowercase: string;
  email: string;
  displayName: string;
  photoURL?: string | null;
  authProvider: 'password' | 'google' | string;
  createdAt: string;
  lastLoginAt: string;
}

/**
 * Validates username format and checks uniqueness case-insensitively in Firestore.
 */
export async function isUsernameAvailable(rawUsername: string): Promise<{ available: boolean; error?: string }> {
  const username = rawUsername.trim();
  if (!username) {
    return { available: false, error: "Username is required." };
  }
  if (username.length < 3) {
    return { available: false, error: "Username must be at least 3 characters." };
  }
  if (username.length > 25) {
    return { available: false, error: "Username cannot exceed 25 characters." };
  }
  // Allow letters, numbers, underscores, and single hyphens
  if (!/^[a-zA-Z0-9_]+$/.test(username)) {
    return { available: false, error: "Username can only contain letters, numbers, and underscores." };
  }

  const lower = username.toLowerCase();

  try {
    // 1. Direct document lookup in the dedicated 'usernames' uniqueness index
    const usernameRef = doc(db, "usernames", lower);
    const snap = await getDoc(usernameRef);
    if (snap.exists()) {
      return { available: false, error: "Username is already taken. Please choose another." };
    }

    // 2. Secondary check across 'users' collection on usernameLowercase
    const q = query(collection(db, "users"), where("usernameLowercase", "==", lower));
    const userQuerySnap = await getDocs(q);
    if (!userQuerySnap.empty) {
      return { available: false, error: "Username is already taken. Please choose another." };
    }

    return { available: true };
  } catch (err: any) {
    console.warn("[Firestore] Username check warning:", err);
    // If offline or permission check occurs, fallback to proceeding
    return { available: true };
  }
}

/**
 * Check if an email has already registered a Mythora profile in Firestore.
 */
export async function checkEmailRegistered(rawEmail: string): Promise<boolean> {
  const email = rawEmail.trim().toLowerCase();
  if (!email) return false;

  try {
    const q = query(collection(db, "users"), where("email", "==", email));
    const snap = await getDocs(q);
    return !snap.empty;
  } catch (err) {
    console.warn("[Firestore] Email registration query warning:", err);
    return false;
  }
}

/**
 * Save user profile in Firestore and record the username reservation.
 */
export async function saveUserProfile(
  uid: string,
  data: {
    username: string;
    email: string;
    displayName?: string | null;
    photoURL?: string | null;
    authProvider: string;
  }
): Promise<UserProfile> {
  const now = new Date().toISOString();
  const lower = data.username.trim().toLowerCase();

  const profile: UserProfile = {
    uid,
    username: data.username.trim(),
    usernameLowercase: lower,
    email: data.email.trim().toLowerCase(),
    displayName: data.displayName || data.username.trim(),
    photoURL: data.photoURL || null,
    authProvider: data.authProvider,
    createdAt: now,
    lastLoginAt: now
  };

  // 1. Save user profile doc in 'users/{uid}'
  const userRef = doc(db, "users", uid);
  await setDoc(userRef, profile, { merge: true });

  // 2. Reserve unique username in 'usernames/{usernameLowercase}'
  try {
    const usernameRef = doc(db, "usernames", lower);
    await setDoc(usernameRef, {
      uid,
      username: data.username.trim(),
      createdAt: now
    });
  } catch (e) {
    console.warn("[Firestore] Could not reserve username index doc:", e);
  }

  return profile;
}

/**
 * Fetch user profile from Firestore.
 */
export async function getUserProfile(uid: string): Promise<UserProfile | null> {
  try {
    const userRef = doc(db, "users", uid);
    const snap = await getDoc(userRef);
    if (snap.exists()) {
      return snap.data() as UserProfile;
    }
  } catch (err) {
    console.warn("[Firestore] getUserProfile warning:", err);
  }
  return null;
}

/**
 * Update user's last login timestamp.
 */
export async function updateLastLogin(uid: string): Promise<void> {
  try {
    const userRef = doc(db, "users", uid);
    await updateDoc(userRef, {
      lastLoginAt: new Date().toISOString()
    });
  } catch {}
}
