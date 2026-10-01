export async function getIdToken(): Promise<string | null> {
  return "local-dev-token";
}

export function signOut(): void {
  // No-op in local development.
}
