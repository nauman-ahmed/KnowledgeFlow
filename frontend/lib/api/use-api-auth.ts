"use client";

import { useAuth } from "@clerk/nextjs";
import { useCallback } from "react";

/** Wait for Clerk before calling the backend with a session JWT. */
export function useApiAuth() {
  const { isLoaded, isSignedIn, getToken } = useAuth();

  const getApiToken = useCallback(async (): Promise<string | null> => {
    if (!isLoaded || !isSignedIn) {
      return null;
    }
    return getToken();
  }, [isLoaded, isSignedIn, getToken]);

  return {
    isAuthReady: isLoaded && isSignedIn,
    getApiToken,
  };
}
