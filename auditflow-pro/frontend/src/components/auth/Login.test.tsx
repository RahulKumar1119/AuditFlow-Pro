// src/components/auth/Login.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import Login from './Login';
import * as AuthContextModule from '../../contexts/AuthContext';

// Mock React Router
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('Login Component', () => {
  const mockLogin = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Spy on the useAuth hook to inject our mock login function
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      login: mockLogin,
      user: null,
      logout: vi.fn(),
      checkUser: vi.fn()
    });
  });

  const renderLogin = () => {
    return render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    );
  };

  it('renders login form correctly', () => {
    renderLogin();
    expect(screen.getByPlaceholderText(/email address/i)).toBeDefined();
    expect(screen.getByPlaceholderText(/password/i)).toBeDefined();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeDefined();
  });

  it('shows error when email format is invalid', async () => {
    renderLogin();
    
    const emailInput = screen.getByPlaceholderText(/email address/i);
    const passwordInput = screen.getByPlaceholderText(/password/i);
    const submitButton = screen.getByRole('button', { name: /sign in/i });
    
    fireEvent.change(emailInput, { target: { value: 'invalid-email' } });
    fireEvent.change(passwordInput, { target: { value: 'password' } });
    
    // Submit the form (not just click the button)
    const form = submitButton.closest('form');
    if (form) {
      fireEvent.submit(form);
    }
    
    const errorMessage = await screen.findByText(/please enter a valid email address/i);
    expect(errorMessage).toBeDefined();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it('calls login function and navigates on success', async () => {
    mockLogin.mockResolvedValueOnce({ success: true });
    renderLogin();

    fireEvent.change(screen.getByPlaceholderText(/email address/i), { target: { value: 'test@example.com' } });
    fireEvent.change(screen.getByPlaceholderText(/password/i), { target: { value: 'Password123!' } });
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'Password123!');
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    });
  });
});
