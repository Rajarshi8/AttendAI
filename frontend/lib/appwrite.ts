import { Account, Client, Databases, ID, Models, RealtimeResponseEvent } from "appwrite";

const endpoint =
  process.env.NEXT_PUBLIC_APPWRITE_ENDPOINT || "https://nyc.cloud.appwrite.io/v1";
const projectId =
  process.env.NEXT_PUBLIC_APPWRITE_PROJECT_ID || "69d53599001c62969125";

const client = new Client().setEndpoint(endpoint).setProject(projectId);

export const account = new Account(client);
export const databases = new Databases(client);
export { client };

// ─── Connection warmup ────────────────────────────────────────────────────────

let pingAttempted = false;

export function ensureAppwriteConnection() {
  if (pingAttempted) return;
  pingAttempted = true;
  void client.ping().catch(() => {
    pingAttempted = false;
  });
}

// ─── Auth helpers ─────────────────────────────────────────────────────────────

export async function signup(email: string, password: string, name: string) {
  const createdUser = await account.create(ID.unique(), email, password, name);
  await login(email, password);
  return createdUser;
}

export function login(email: string, password: string) {
  return account.createEmailPasswordSession(email, password);
}

export function logout() {
  return account.deleteSession("current");
}

export async function getCurrentUser(): Promise<Models.User<Models.Preferences> | null> {
  try {
    return await account.get();
  } catch {
    return null;
  }
}

export async function getAuthJwt(): Promise<string | null> {
  try {
    const jwt = await account.createJWT();
    return jwt.jwt;
  } catch {
    return null;
  }
}

// ─── Realtime helpers ─────────────────────────────────────────────────────────

const dbId = process.env.NEXT_PUBLIC_APPWRITE_DATABASE_ID || "";
const sessionsCollectionId =
  process.env.NEXT_PUBLIC_APPWRITE_SESSIONS_COLLECTION_ID || "";

/**
 * Subscribe to Appwrite Realtime updates on the sessions collection.
 * Returns the unsubscribe function — call it on component unmount.
 *
 * @param callback  Called with the raw Appwrite realtime payload on every change.
 */
export function subscribeToSessions(
  callback: (event: RealtimeResponseEvent<Record<string, unknown>>) => void,
): () => void {
  if (!dbId || !sessionsCollectionId) {
    console.warn(
      "[AttendAI] NEXT_PUBLIC_APPWRITE_DATABASE_ID or NEXT_PUBLIC_APPWRITE_SESSIONS_COLLECTION_ID is not set. Realtime disabled.",
    );
    return () => {};
  }

  const channel = `databases.${dbId}.collections.${sessionsCollectionId}.documents`;
  const unsubscribe = client.subscribe(channel, callback);
  return unsubscribe;
}
