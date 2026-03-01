// frontend/src/contexts/AuthContext.tsx

import { createContext, useState, useEffect, useContext } from 'react';
import type { ReactNode } from 'react';
// V6 Import Syntax
import { signIn, signOut, getCurrentUser } from 'aws-amplify/auth';
import type { AuthUser } from 'aws-amplify/auth';

// Define types for authentication context
export interface AuthContextType {
  user: AuthUser | null;
  login: (email: string, password: string) => Promise<LoginResult>;
  logout: () => Promise<void>;
  checkUser: () => Promise<void>;
}

interface LoginResult {
  success: boolean;
  error?: string;
  code?: string;
}

interface AuthProviderProps {
  children: ReactNode;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    checkUser();
  }, []);

  const checkUser = async (): Promise<void> => {
    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (email: string, password: string): Promise<LoginResult> => {
    try {
      await signIn({ username: email, password });
      // After successful sign in, get the current user
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      return { success: true };
    } catch (error) {
      // Handle account lockout and authentication errors
      const errorMessage = error instanceof Error ? error.message : 'Authentication failed';
      const errorCode = error instanceof Error && 'name' in error ? (error as { name: string }).name : 'UnknownError';
      
      return { 
        success: false, 
        error: errorMessage, 
        code: errorCode 
      };
    }
  };

  const logout = async (): Promise<void> => {
    try {
      await signOut();
      setUser(null);
    } catch (error) {
      console.error('Error signing out: ', error);
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-lg text-gray-600">Loading session...</div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, checkUser }}>
      {children}
    </AuthContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
