"use client";

import { useAuth } from "@clerk/nextjs";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { loginUrlWithRedirect } from "@/lib/auth-urls";

/**
 * After client-side sign-out, Clerk may navigate to "/" without a full reload.
 * Send signed-out users on / or /chat to /login with redirect_url back to /chat.
 */
export function AuthRedirectHandler() {
  const { isLoaded, isSignedIn } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoaded || isSignedIn) return;
    if (pathname.startsWith("/login")) return;
    if (pathname !== "/" && !pathname.startsWith("/chat")) return;

    router.replace(loginUrlWithRedirect("/chat", window.location.origin));
  }, [isLoaded, isSignedIn, pathname, router]);

  return null;
}
