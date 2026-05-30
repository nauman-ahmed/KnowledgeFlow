import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { loginRedirectForRequest } from "@/lib/auth-urls";

const isPublicRoute = createRouteMatcher([
  "/login(.*)",
  "/api/health",
]);

const isProtectedRoute = createRouteMatcher(["/chat(.*)"]);

export default clerkMiddleware(async (auth, req) => {
  if (isPublicRoute(req)) {
    return;
  }
  if (isProtectedRoute(req)) {
    const returnPath = req.nextUrl.pathname + req.nextUrl.search;
    await auth.protect({
      unauthenticatedUrl: loginRedirectForRequest(req.url, returnPath),
    });
  }
});

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
