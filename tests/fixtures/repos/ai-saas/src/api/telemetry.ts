import posthog from "posthog-js";

export function trackSignup(email: string) {
  posthog.capture("signup", { email, cookie: document.cookie });
}
