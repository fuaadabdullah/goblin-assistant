export interface AccessUser {
  email?: string;
  role?: string;
  roles?: string[];
}

const parseList = (value?: string): string[] =>
  (value || '')
    .split(',')
    .map(item => item.trim().toLowerCase())
    .filter(Boolean);

const ADMIN_EMAILS = parseList(process.env.NEXT_PUBLIC_ADMIN_EMAILS);
const ADMIN_DOMAINS = parseList(process.env.NEXT_PUBLIC_ADMIN_DOMAINS);

export const isAdminUser = (user?: AccessUser | null): boolean => {
  if (!user) return false;

  const role = user.role?.toLowerCase();
  const roles = (user.roles || []).map(r => r.toLowerCase());
  if (role && ['admin', 'owner', 'superuser'].includes(role)) return true;
  if (roles.some(r => ['admin', 'owner', 'superuser'].includes(r))) return true;

  const email = user.email?.toLowerCase();
  if (!email) return false;
  if (ADMIN_EMAILS.includes(email)) return true;

  const domain = email.split('@')[1];
  if (domain && ADMIN_DOMAINS.includes(domain)) return true;

  return false;
};
