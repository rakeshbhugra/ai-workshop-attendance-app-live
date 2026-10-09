import { Navigate } from "react-router";
import { loginUrl, useMe, useProviders } from "./queries";
import "@/features/workspace/workspace.css";

const LABELS: Record<string, string> = {
  google: "Continue with Google",
  dev: "Continue with local dev login",
};

/** One button per provider the API has switched on. Plain links, not fetch:
 *  the browser must follow the redirect to the provider's consent screen. */
export function LoginPage() {
  const me = useMe();
  const providers = useProviders();
  if (me.isSuccess) return <Navigate to="/" replace />;
  return (
    <div className="auth-page"><section className="auth-card">
      <img src="/schoolnet/schoolnet-logo.png" alt="Schoolnet, Learning for life" />
      <h1>Welcome to Workshop Hub</h1>
      <p>Manage students, record attendance, and understand participation.</p>
      <div className="auth-actions">
        {providers.data?.map((p) => (
          <a
            key={p}
            href={loginUrl(p)}
            className={`button ${p === "google" ? "primary" : "secondary"}`}
          >
            {LABELS[p] ?? `Continue with ${p}`}
          </a>
        ))}
        {providers.isPending && <p role="status">Loading sign-in options…</p>}
        {providers.isError && <><p role="alert">Sign-in options could not be loaded.</p><button className="button secondary" onClick={() => void providers.refetch()}>Try again</button></>}
        {providers.data?.length === 0 && <p>No sign-in method is configured.</p>}
      </div>
      {providers.data?.includes("dev") && <div className="notice">Local development access is enabled. Google sign-in can be configured later.</div>}
    </section></div>
  );
}
