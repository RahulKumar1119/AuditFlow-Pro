// frontend/src/components/layout/MainLayout.jsx

import React from 'react';
import { Outlet, Navigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { LogOut, FileText, LayoutDashboard, Settings } from 'lucide-react'; // Standard UI icons

const MainLayout = () => {
  const { user, logout } = useAuth();

  // Protect the layout - redirect to login if not authenticated
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Extract user info (Assuming email is the username)
  const username = user.attributes?.email || user.username || 'User';
  const groups = user.signInUserSession?.accessToken?.payload['cognito:groups'] || [];

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-slate-800 text-white flex flex-col hidden md:flex">
        <div className="p-4 text-2xl font-bold border-b border-slate-700">
          AuditFlow
        </div>
        <nav className="flex-1 p-4 space-y-2">
          <Link to="/dashboard" className="flex items-center space-x-2 p-2 rounded hover:bg-slate-700">
            <LayoutDashboard size={20} />
            <span>Dashboard</span>
          </Link>
          <Link to="/audits" className="flex items-center space-x-2 p-2 rounded hover:bg-slate-700">
            <FileText size={20} />
            <span>Audit Records</span>
          </Link>
          {groups.includes('Administrator') && (
            <Link to="/settings" className="flex items-center space-x-2 p-2 rounded hover:bg-slate-700">
              <Settings size={20} />
              <span>Admin Settings</span>
            </Link>
          )}
        </nav>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="flex h-16 items-center justify-between bg-white px-6 shadow">
          <div className="md:hidden font-bold text-xl">AuditFlow</div>
          <div className="flex items-center space-x-4 ml-auto">
            <span className="text-sm text-gray-600">Logged in as: {username}</span>
            <button 
              onClick={logout}
              className="flex items-center space-x-1 text-sm text-red-600 hover:text-red-800"
            >
              <LogOut size={16} />
              <span>Logout</span>
            </button>
          </div>
        </header>

        {/* Page Content injected here */}
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default MainLayout;
