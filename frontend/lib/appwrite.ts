import { Account, Client, Databases, ID, Models } from "appwrite";

const endpoint = process.env.NEXT_PUBLIC_APPWRITE_ENDPOINT || "https://nyc.cloud.appwrite.io/v1";
const projectId = process.env.NEXT_PUBLIC_APPWRITE_PROJECT_ID || "69d53599001c62969125";

const client = new Client().setEndpoint(endpoint).setProject(projectId);

export const account = new Account(client);
export const databases = new Databases(client);
export { client };

let pingAttempted = false;

export function ensureAppwriteConnection() {
  if (pingAttempted) return;
  pingAttempted = true;

  // Ping Appwrite backend once on app load to verify SDK connectivity.
  void client.ping().catch(() => {
    pingAttempted = false;
  });
}

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
