// frontend/src/components/layout/MainLayout.tsx

import React, { useState, useEffect, useRef } from 'react';
import { Outlet, Navigate, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { LogOut, FileText, LayoutDashboard, Settings, Menu, X, Upload as UploadIcon, User, ChevronDown } from 'lucide-react';
import logoSvg from '../../assets/auditflow-logo.svg';

const MainLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(false);
  const [isProfileDropdownOpen, setIsProfileDropdownOpen] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close mobile menu when route changes
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  // Close profile dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsProfileDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Protect the layout - redirect to login if not authenticated
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Extract user info
  const username = user.signInDetails?.loginId || user.username || 'User';
  
  // Get user groups from token (for role-based access)
  // Note: In AWS Amplify v6, groups might be in different location
  const groups: string[] = [];

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
        <div className="p-4 border-b border-slate-700">
          <div className="flex flex-col items-center space-y-3">
            <img src={logoSvg} alt="AuditFlow-Pro" className="w-12 h-12" />
            <h1 className="text-2xl font-bold text-center">AuditFlow-Pro</h1>
          </div>
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
            {/* Profile Dropdown */}
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setIsProfileDropdownOpen(!isProfileDropdownOpen)}
                className="flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors"
                aria-label="User menu"
              >
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center">
                  <User size={18} className="text-white" />
                </div>
                <span className="text-sm font-medium text-gray-700 hidden sm:inline">{username}</span>
                <ChevronDown size={16} className={`text-gray-500 transition-transform ${isProfileDropdownOpen ? 'rotate-180' : ''}`} />
              </button>

              {/* Dropdown Menu */}
              {isProfileDropdownOpen && (
                <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50">
                  <div className="px-4 py-3 border-b border-gray-100">
                    <p className="text-sm font-medium text-gray-900">{username}</p>
                    <p className="text-xs text-gray-500 mt-1">Logged in</p>
                  </div>
                  
                  <div className="py-1">
                    <button
                      onClick={() => {
                        setIsProfileDropdownOpen(false);
                        // Add profile navigation here if needed
                      }}
                      className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                    >
                      <User size={16} />
                      <span>Profile</span>
                    </button>
                    
                    <button
                      onClick={() => {
                        setIsProfileDropdownOpen(false);
                        // Add settings navigation here if needed
                      }}
                      className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                    >
                      <Settings size={16} />
                      <span>Settings</span>
                    </button>
                  </div>

                  <div className="border-t border-gray-100 py-1">
                    <button
                      onClick={() => {
                        setIsProfileDropdownOpen(false);
                        handleLogout();
                      }}
                      className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                    >
                      <LogOut size={16} />
                      <span>Logout</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
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
