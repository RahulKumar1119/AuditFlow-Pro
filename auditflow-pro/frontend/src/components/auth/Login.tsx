// frontend/src/components/auth/Login.tsx

import { useState } from 'react';
import type { FormEvent } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

const Login: React.FC = () => {
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    setError('');

    // Basic Form Validation
    if (!email || !password) {
      setError('Please enter both email and password.');
      return;
    }

    // Email format validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError('Please enter a valid email address.');
      return;
    }

    setIsLoading(true);
    const result = await login(email, password);
    
    if (result.success) {
      navigate('/dashboard');
    } else {
      // Handle lockout notifications explicitly (Requirement 2.7)
      if (
        result.error?.includes('too many failed attempts') || 
        result.error?.includes('locked') ||
        result.code === 'NotAuthorizedException'
      ) {
        setError(
          result.error || 
          'Incorrect username or password. Your account will be locked for 15 minutes after 3 consecutive failed attempts.'
        );
      } else if (result.code === 'UserNotFoundException') {
        setError('No account found with this email address.');
      } else if (result.code === 'InvalidParameterException') {
        setError('Invalid email or password format.');
      } else {
        // User-friendly error messages (Requirement 1.8)
        setError(result.error || 'Unable to sign in. Please try again.');
      }
    }
    setIsLoading(false);
  };

  // Feature icons data
  const features = [
    { icon: '📊', label: 'Analytics Dashboard', color: 'from-blue-400 to-blue-600' },
    { icon: '🔒', label: 'Secure Processing', color: 'from-green-400 to-green-600' },
    { icon: '📄', label: 'Document Analysis', color: 'from-purple-400 to-purple-600' },
    { icon: '⚡', label: 'Real-time Scoring', color: 'from-orange-400 to-orange-600' },
    { icon: '💾', label: 'Data Storage', color: 'from-indigo-400 to-indigo-600' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-sky-50 to-indigo-100 relative overflow-hidden">
      {/* Futuristic Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Animated gradient orbs */}
        <div className="absolute top-20 left-20 w-96 h-96 bg-blue-300 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-float"></div>
        <div className="absolute bottom-20 right-20 w-96 h-96 bg-indigo-300 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-float-delayed"></div>
        
        {/* Grid lines */}
        <div className="absolute inset-0 bg-grid-slate-200/50 [mask-image:linear-gradient(0deg,white,rgba(255,255,255,0.5))]"></div>
        
        {/* Floating geometric shapes */}
        <div className="absolute top-1/4 right-1/4 w-32 h-32 border-2 border-blue-200/30 rounded-lg rotate-12 animate-spin-slow"></div>
        <div className="absolute bottom-1/3 left-1/4 w-24 h-24 border-2 border-indigo-200/30 rounded-full animate-pulse-slow"></div>
      </div>

      {/* Main Content */}
      <div className="relative z-10 min-h-screen flex flex-col">
        {/* Header with Logo */}
        <div className="pt-8 px-8">
          <div className="flex items-center space-x-4">
            {/* Logo Icon */}
            <div className="relative">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center shadow-xl shadow-blue-500/30 relative overflow-hidden">
                <div className="absolute inset-0 bg-white/20 animate-shimmer"></div>
                <svg className="w-9 h-9 text-white relative z-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {/* Dotted circle border */}
                <div className="absolute inset-0 border-4 border-dashed border-blue-300/40 rounded-2xl animate-spin-very-slow"></div>
              </div>
            </div>
            
            {/* Logo Text */}
            <div>
              <h1 className="text-3xl font-bold text-slate-800">AuditFlow-Pro</h1>
              <p className="text-sm text-slate-600 font-medium">AI-Powered Loan Processing Automation</p>
            </div>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex items-center justify-center px-8 py-12">
          <div className="w-full max-w-6xl">
            <div className="grid lg:grid-cols-2 gap-12 items-center">
              
              {/* Left Side - Illustration Area */}
              <div className="hidden lg:block">
                <div className="relative">
                  {/* Central Platform Illustration */}
                  <div className="relative">
                    {/* Main Dashboard Preview */}
                    <div className="bg-white/80 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/50 p-8 transform hover:scale-105 transition-transform duration-500">
                      <div className="space-y-4">
                        {/* Dashboard Header */}
                        <div className="flex items-center justify-between pb-4 border-b border-slate-200">
                          <div className="flex items-center space-x-3">
                            <div className="w-3 h-3 bg-red-400 rounded-full"></div>
                            <div className="w-3 h-3 bg-yellow-400 rounded-full"></div>
                            <div className="w-3 h-3 bg-green-400 rounded-full"></div>
                          </div>
                          <div className="text-xs text-slate-500 font-mono">Dashboard</div>
                        </div>
                        
                        {/* Charts and Metrics */}
                        <div className="grid grid-cols-2 gap-4">
                          {/* Pie Chart */}
                          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl p-4">
                            <div className="w-20 h-20 mx-auto relative">
                              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                                <circle cx="18" cy="18" r="16" fill="none" stroke="#e0e7ff" strokeWidth="3"/>
                                <circle cx="18" cy="18" r="16" fill="none" stroke="#4f46e5" strokeWidth="3" strokeDasharray="75 25" strokeLinecap="round"/>
                                <circle cx="18" cy="18" r="16" fill="none" stroke="#06b6d4" strokeWidth="3" strokeDasharray="25 75" strokeDashoffset="-75" strokeLinecap="round"/>
                              </svg>
                            </div>
                            <p className="text-xs text-center mt-2 text-slate-600 font-medium">Loan Status</p>
                          </div>
                          
                          {/* Confidence Score */}
                          <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-2xl p-4">
                            <div className="text-center">
                              <div className="text-3xl font-bold text-green-600">92%</div>
                              <p className="text-xs text-slate-600 mt-1">Confidence</p>
                              <div className="mt-2 h-2 bg-green-200 rounded-full overflow-hidden">
                                <div className="h-full w-11/12 bg-gradient-to-r from-green-500 to-emerald-500 rounded-full"></div>
                              </div>
                            </div>
                          </div>
                        </div>
                        
                        {/* Report Preview */}
                        <div className="bg-gradient-to-br from-orange-50 to-red-50 rounded-2xl p-4">
                          <div className="flex items-center justify-between mb-2">
                            <p className="text-xs font-semibold text-slate-700">Mismatch Report</p>
                            <span className="text-xs px-2 py-1 bg-red-100 text-red-600 rounded-full font-medium">3 Issues</span>
                          </div>
                          <div className="space-y-1">
                            <div className="h-2 bg-red-200 rounded-full w-3/4"></div>
                            <div className="h-2 bg-red-200 rounded-full w-1/2"></div>
                            <div className="h-2 bg-red-200 rounded-full w-2/3"></div>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Floating Feature Icons */}
                    <div className="absolute -bottom-8 left-0 right-0 flex justify-center space-x-4">
                      {features.map((feature, index) => (
                        <div
                          key={index}
                          className="group relative"
                          style={{ animationDelay: `${index * 0.1}s` }}
                        >
                          <div className={`w-16 h-16 bg-gradient-to-br ${feature.color} rounded-xl shadow-lg flex items-center justify-center transform hover:scale-110 hover:-translate-y-2 transition-all duration-300 cursor-pointer`}>
                            <span className="text-2xl">{feature.icon}</span>
                          </div>
                          <div className="absolute -bottom-8 left-1/2 transform -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap">
                            <div className="bg-slate-800 text-white text-xs px-3 py-1 rounded-lg">
                              {feature.label}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Tagline */}
                  <div className="mt-20 text-center">
                    <h2 className="text-2xl font-bold text-slate-800 mb-2">
                      Streamlining Loan Processing for the Banking Sector
                    </h2>
                    <p className="text-slate-600">Powered by Advanced AI Technology</p>
                  </div>
                </div>
              </div>

              {/* Right Side - Login Form */}
              <div className="w-full max-w-md mx-auto lg:mx-0">
                <div className="bg-white/90 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/50 p-10">
                  {/* Mobile Logo */}
                  <div className="lg:hidden text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl mb-4 shadow-lg">
                      <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <h1 className="text-2xl font-bold text-slate-800">AuditFlow-Pro</h1>
                  </div>

                  {/* Form Header */}
                  <div className="text-center mb-8">
                    <h2 className="text-3xl font-bold text-slate-800 mb-2">Welcome Back</h2>
                    <p className="text-slate-600">Sign in to access your dashboard</p>
                  </div>

                  {/* Error Alert */}
                  {error && (
                    <div 
                      className="mb-6 rounded-2xl border-2 border-red-200 bg-gradient-to-r from-red-50 to-red-100/50 px-5 py-4 flex items-start space-x-3 animate-shake"
                      role="alert"
                      aria-live="assertive"
                    >
                      <div className="flex-shrink-0 w-6 h-6 bg-red-500 rounded-full flex items-center justify-center">
                        <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                      </div>
                      <span className="text-sm font-medium text-red-800 flex-1">{error}</span>
                    </div>
                  )}

                  {/* Login Form */}
                  <form className="space-y-6" onSubmit={handleSubmit}>
                    <div>
                      <label htmlFor="email" className="block text-sm font-semibold text-slate-700 mb-2">
                        Email Address
                      </label>
                      <div className="relative group">
                        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                          <svg className="h-5 w-5 text-slate-400 group-focus-within:text-blue-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                          </svg>
                        </div>
                        <input
                          id="email"
                          name="email"
                          type="email"
                          autoComplete="email"
                          required
                          className="block w-full pl-12 pr-4 py-4 rounded-2xl border-2 border-slate-200 bg-white text-slate-900 placeholder-slate-400 focus:border-blue-500 focus:outline-none focus:ring-4 focus:ring-blue-500/20 transition-all duration-200 hover:border-slate-300 hover:shadow-sm"
                          placeholder="you@company.com"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          disabled={isLoading}
                        />
                      </div>
                    </div>
                    
                    <div>
                      <label htmlFor="password" className="block text-sm font-semibold text-slate-700 mb-2">
                        Password
                      </label>
                      <div className="relative group">
                        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                          <svg className="h-5 w-5 text-slate-400 group-focus-within:text-blue-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                          </svg>
                        </div>
                        <input
                          id="password"
                          name="password"
                          type="password"
                          autoComplete="current-password"
                          required
                          className="block w-full pl-12 pr-4 py-4 rounded-2xl border-2 border-slate-200 bg-white text-slate-900 placeholder-slate-400 focus:border-blue-500 focus:outline-none focus:ring-4 focus:ring-blue-500/20 transition-all duration-200 hover:border-slate-300 hover:shadow-sm"
                          placeholder="••••••••"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          disabled={isLoading}
                        />
                      </div>
                    </div>

                    {/* Sign In Button */}
                    <button
                      type="submit"
                      disabled={isLoading}
                      className="group relative w-full flex justify-center items-center space-x-2 rounded-2xl bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-700 px-6 py-4 text-base font-semibold text-white shadow-xl shadow-blue-500/30 hover:shadow-2xl hover:shadow-blue-600/40 hover:scale-[1.02] focus:outline-none focus:ring-4 focus:ring-blue-500/50 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 transition-all duration-300 overflow-hidden"
                    >
                      <div className="absolute inset-0 bg-gradient-to-r from-blue-700 via-indigo-700 to-blue-800 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
                      {isLoading ? (
                        <>
                          <svg className="animate-spin h-5 w-5 text-white relative z-10" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          <span className="relative z-10">Signing in...</span>
                        </>
                      ) : (
                        <>
                          <span className="relative z-10">Sign In to Dashboard</span>
                          <svg className="w-5 h-5 relative z-10 group-hover:translate-x-1 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                          </svg>
                        </>
                      )}
                    </button>
                  </form>

                  {/* Footer */}
                  <div className="mt-8 pt-6 border-t-2 border-slate-100">
                    <div className="flex items-center justify-center space-x-2">
                      <div className="flex items-center space-x-2 px-4 py-2 bg-slate-50 rounded-full">
                        <svg className="w-4 h-4 text-slate-400" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                        </svg>
                        <span className="text-xs font-medium text-slate-600">Secure Authentication</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Footer */}
        <div className="pb-6 px-8 text-center text-sm text-slate-500">
          © 2026 AuditFlow-Pro. All rights reserved.
        </div>
      </div>
    </div>
  );
};

export default Login;
