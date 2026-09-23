export interface AccessUser {
  email?: string | undefined;
  role?: string | undefined;
  roles?: string[] | undefined;
}

const parseList = (value?: string): string[] =>
  (value || '')
    .split(',')
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);

// Deliberately NOT NEXT_PUBLIC_-prefixed: this module is imported by client
// components (e.g. ChatScreen), and a public env var here would inline the
// full admin allowlist into the browser bundle. Keeping these server-only
// means the email/domain checks below only ever match when this code runs
// server-side (e.g. proxy.ts); the backend's admin.py uses the same names.
const ADMIN_EMAILS = parseList(process.env['ADMIN_EMAILS']);
const ADMIN_DOMAINS = parseList(process.env['ADMIN_DOMAINS']);

export const isAdminUser = (user?: AccessUser | null): boolean => {
  if (!user) return false;

  const role = user.role?.toLowerCase();
  const roles = (user.roles || []).map((r) => r.toLowerCase());
  if (role && ['admin', 'owner', 'superuser'].includes(role)) return true;
  if (roles.some((r) => ['admin', 'owner', 'superuser'].includes(r))) return true;

  const email = user.email?.toLowerCase();
  if (!email) return false;
  if (ADMIN_EMAILS.includes(email)) return true;

  const domain = email.split('@')[1];
  if (domain && ADMIN_DOMAINS.includes(domain)) return true;

  return false;
};
