import { Navigate, Outlet } from "react-router";
import { useMe } from "./queries";

/** Gate for the app shell: blank until /me answers, then the page or /login. */
export function RequireAuth() {
  const me = useMe();
  if (me.isPending) return <p role="status">Checking your session…</p>;
  if (me.isError) return <Navigate to="/login" replace />;
  return <Outlet />;
}
