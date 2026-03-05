import { Metadata } from "next";
import { ReactNode } from "react";
import { AdminSidebar } from "./components/admin-sidebar";
import { AdminHeader } from "./components/admin-header";

export const metadata: Metadata = {
  title: "Admin Dashboard - Goblin Assistant",
  description: "System monitoring and operations dashboard - Admin Only",
};

// Admin-only layout with role verification
export default async function AdminLayout({ children }: { children: ReactNode }) {
  // Server-side admin check
  // In production, this would verify the JWT token has admin role
  // For now, we allow access but the middleware will handle auth
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Admin warning banner */}
      <div className="bg-amber-500/90 text-slate-900 text-center py-2 text-sm font-semibold">
        🔒 Admin Area - Internal Use Only
      </div>
      <AdminHeader />
      <div className="flex">
        <AdminSidebar />
        <main className="flex-1 p-6">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
