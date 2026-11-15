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

// Helper to guard Firestore promises against hanging indefinitely
function withTimeout<T>(promise: Promise<T>, timeoutMs: number = 8000, fallbackValue: T): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((resolve) => setTimeout(() => resolve(fallbackValue), timeoutMs))
  ]);
}

/**
 * Local storage cache helpers to guarantee instant, flicker-free, and offline-resilient profile loading
 */
export function getCachedProfile(uid: string): UserProfile | null {
  if (!uid) return null;
  try {
    const raw = localStorage.getItem(`mythora_user_profile_${uid}`);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && parsed.username && typeof parsed.username === 'string' && parsed.username.trim() !== '') {
        return parsed as UserProfile;
      }
    }
  } catch {}
  return null;
}

export function setCachedProfile(uid: string, profile: UserProfile): void {
  if (!uid || !profile) return;
  try {
    localStorage.setItem(`mythora_user_profile_${uid}`, JSON.stringify(profile));
  } catch {}
}

export function clearCachedProfile(uid: string): void {
  if (!uid) return;
  try {
    localStorage.removeItem(`mythora_user_profile_${uid}`);
  } catch {}
}

/**
 * Validates username format and checks uniqueness case-insensitively in Firestore.
 * Allows current user to keep/re-verify their own username.
 */
export async function isUsernameAvailable(
  rawUsername: string,
  currentUid?: string
): Promise<{ available: boolean; error?: string }> {
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
    // 1. Direct document lookup in the dedicated 'usernames' uniqueness index with timeout
    const usernameRef = doc(db, "usernames", lower);
    const snap = await withTimeout(getDoc(usernameRef), 5000, null);
    if (snap && snap.exists()) {
      const data = snap.data();
      // If this record belongs to the current user, it is already their own username!
      if (currentUid && data?.uid === currentUid) {
        return { available: true };
      }
      return { available: false, error: "Username is already taken. Please choose another." };
    }

    // 2. Secondary check across 'users' collection on usernameLowercase with timeout
    const q = query(collection(db, "users"), where("usernameLowercase", "==", lower));
    const userQuerySnap = await withTimeout(getDocs(q), 5000, null);
    if (userQuerySnap && !userQuerySnap.empty) {
      const belongsToOther = userQuerySnap.docs.some(d => {
        const docUid = d.data()?.uid || d.id;
        return !currentUid || docUid !== currentUid;
      });
      if (belongsToOther) {
        return { available: false, error: "Username is already taken. Please choose another." };
      }
    }

    return { available: true };
  } catch (err: any) {
    console.warn("[Firestore] Username check warning:", err);
    // If offline or permission check occurs, proceed
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
    const snap = await withTimeout(getDocs(q), 3500, null);
    return snap ? !snap.empty : false;
  } catch (err) {
    console.warn("[Firestore] Email registration query warning:", err);
    return false;
  }
}

/**
 * Save user profile in Firestore under users/{uid} and record the username reservation.
 * Also immediately writes to local storage cache for permanent instant availability.
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
  const cleanUsername = data.username.trim();
  const lower = cleanUsername.toLowerCase();

  const profile: UserProfile = {
    uid,
    username: cleanUsername,
    usernameLowercase: lower,
    email: data.email.trim().toLowerCase(),
    displayName: data.displayName || cleanUsername,
    photoURL: data.photoURL || null,
    authProvider: data.authProvider,
    createdAt: now,
    lastLoginAt: now
  };

  // 1. Immediately cache locally so the user session and username are never lost
  setCachedProfile(uid, profile);

  // 2. Save user profile doc in 'users/{uid}' with robust timeout
  try {
    const userRef = doc(db, "users", uid);
    await withTimeout(setDoc(userRef, profile, { merge: true }), 8000, undefined);
  } catch (e) {
    console.warn("[Firestore] saveUserProfile write warning:", e);
  }

  // 3. Reserve unique username in 'usernames/{usernameLowercase}'
  try {
    const usernameRef = doc(db, "usernames", lower);
    withTimeout(setDoc(usernameRef, {
      uid,
      username: cleanUsername,
      createdAt: now
    }), 5000, undefined).catch(() => {});
  } catch (e) {
    console.warn("[Firestore] Could not reserve username index doc:", e);
  }

  return profile;
}

/**
 * Fetch user profile from Firestore by UID with local cache fallback and multi-layered lookup.
 */
export async function getUserProfile(uid: string): Promise<UserProfile | null> {
  if (!uid) return null;

  // 1. Check local cache first for instant retrieval
  const cached = getCachedProfile(uid);

  try {
    // 2. Query Firestore by direct UID at 'users/{uid}' with 8s timeout
    const userRef = doc(db, "users", uid);
    const snap = await withTimeout(getDoc(userRef), 8000, null);
    if (snap && snap.exists()) {
      const data = snap.data() as UserProfile;
      if (data && data.username && data.username.trim() !== '') {
        setCachedProfile(uid, data);
        return data;
      }
    }

    // 3. Secondary check: Query by field 'uid' in 'users' collection in case of ID normalization discrepancies
    const q = query(collection(db, "users"), where("uid", "==", uid));
    const querySnap = await withTimeout(getDocs(q), 5000, null);
    if (querySnap && !querySnap.empty) {
      const docData = querySnap.docs[0].data() as UserProfile;
      if (docData && docData.username && docData.username.trim() !== '') {
        setCachedProfile(uid, docData);
        return docData;
      }
    }
  } catch (err) {
    console.warn("[Firestore] getUserProfile warning:", err);
  }

  // 4. Return cached profile if Firestore was slow or temporarily offline
  if (cached && cached.username && cached.username.trim() !== '') {
    return cached;
  }

  return null;
}

/**
 * Update user's last login timestamp without blocking authentication.
 */
export async function updateLastLogin(uid: string): Promise<void> {
  if (!uid) return;
  try {
    const userRef = doc(db, "users", uid);
    await withTimeout(updateDoc(userRef, {
      lastLoginAt: new Date().toISOString()
    }), 4000, undefined);
  } catch {}
}
