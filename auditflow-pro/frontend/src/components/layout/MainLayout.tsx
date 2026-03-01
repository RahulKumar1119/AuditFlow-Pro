// frontend/src/components/layout/MainLayout.tsx

import React, { useState, useEffect } from 'react';
import { Outlet, Navigate, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { LogOut, FileText, LayoutDashboard, Settings, Menu, X, Upload as UploadIcon } from 'lucide-react';

const MainLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(false);

  // Protect the layout - redirect to login if not authenticated
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Extract user info
  const username = user.signInDetails?.loginId || user.username || 'User';
  
  // Get user groups from token (for role-based access)
  // Note: In AWS Amplify v6, groups might be in different location
  const groups: string[] = [];
  
  // Close mobile menu when route changes
  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  const handleLogout = async (): Promise<void> => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const isActivePath = (path: string): boolean => {
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  const navLinkClass = (path: string): string => {
    const baseClass = "flex items-center space-x-2 p-2 rounded transition-colors";
    return isActivePath(path) 
      ? `${baseClass} bg-slate-700 text-white` 
      : `${baseClass} hover:bg-slate-700 text-gray-300 hover:text-white`;
  };

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar Navigation - Desktop */}
      <aside className="w-64 bg-slate-800 text-white flex-col hidden md:flex">
        <div className="p-4 text-2xl font-bold border-b border-slate-700">
          AuditFlow-Pro
        </div>
        <nav className="flex-1 p-4 space-y-2">
          <Link to="/dashboard" className={navLinkClass('/dashboard')}>
            <LayoutDashboard size={20} />
            <span>Dashboard</span>
          </Link>
          <Link to="/upload" className={navLinkClass('/upload')}>
            <UploadIcon size={20} />
            <span>Upload Documents</span>
          </Link>
          <Link to="/audits" className={navLinkClass('/audits')}>
            <FileText size={20} />
            <span>Audit Records</span>
          </Link>
          {groups.includes('Administrator') && (
            <Link to="/settings" className={navLinkClass('/settings')}>
              <Settings size={20} />
              <span>Admin Settings</span>
            </Link>
          )}
        </nav>
        <div className="p-4 border-t border-slate-700 text-xs text-gray-400">
          <p>Secure • Encrypted • Compliant</p>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="flex h-16 items-center justify-between bg-white px-6 shadow-sm">
          {/* Mobile menu button */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="md:hidden p-2 rounded-md hover:bg-gray-100"
            aria-label="Toggle menu"
          >
            {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>

          <div className="md:hidden font-bold text-xl text-slate-800">AuditFlow-Pro</div>
          
          <div className="flex items-center space-x-4 ml-auto">
            <span className="text-sm text-gray-600 hidden sm:inline">
              Logged in as: <span className="font-medium">{username}</span>
            </span>
            <button 
              onClick={handleLogout}
              className="flex items-center space-x-1 text-sm text-red-600 hover:text-red-800 transition-colors px-3 py-1 rounded hover:bg-red-50"
              aria-label="Logout"
            >
              <LogOut size={16} />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </header>

        {/* Mobile Navigation Menu */}
        {isMobileMenuOpen && (
          <div className="md:hidden bg-slate-800 text-white">
            <nav className="p-4 space-y-2">
              <Link to="/dashboard" className={navLinkClass('/dashboard')}>
                <LayoutDashboard size={20} />
                <span>Dashboard</span>
              </Link>
              <Link to="/upload" className={navLinkClass('/upload')}>
                <UploadIcon size={20} />
                <span>Upload Documents</span>
              </Link>
              <Link to="/audits" className={navLinkClass('/audits')}>
                <FileText size={20} />
                <span>Audit Records</span>
              </Link>
              {groups.includes('Administrator') && (
                <Link to="/settings" className={navLinkClass('/settings')}>
                  <Settings size={20} />
                  <span>Admin Settings</span>
                </Link>
              )}
            </nav>
          </div>
        )}

        {/* Page Content injected here */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          <div className="max-w-7xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};

export default MainLayout;
