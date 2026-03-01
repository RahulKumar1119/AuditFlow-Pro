// frontend/src/components/audit/AuditDetailView.test.tsx

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AuditDetailView from './AuditDetailView';
import * as AuthContextModule from '../../contexts/AuthContext';
import * as api from '../../services/api';

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useParams: () => ({ id: 'test-audit-123' }) };
});

vi.mock('../../services/api', () => ({
  fetchAuditById: vi.fn(),
  logPiiAccess: vi.fn()
}));

const mockAuditData = {
  audit_record_id: 'test-audit-123',
  loan_application_id: 'LOAN-999',
  status: 'COMPLETED',
  risk_score: 75,
  risk_level: 'HIGH',
  golden_record: {
    first_name: { value: 'John' },
    last_name: { value: 'Doe' },
    ssn: { value: '123-45-6789' },
  },
  risk_factors: [{ description: 'Income discrepancy exceeds 10%' }],
  inconsistencies: [
    { id: 'inc-1', field_name: 'Income', severity: 'CRITICAL', expected_value: '$50,000', actual_value: '$40,000', sources: [] },
    { id: 'inc-2', field_name: 'Name', severity: 'LOW', expected_value: 'John', actual_value: 'Jon', sources: [] }
  ]
};

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

describe('AuditDetailView Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(api, 'fetchAuditById').mockResolvedValue(mockAuditData);
  });

  const renderWithRole = (role: string) => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: { signInUserSession: { accessToken: { payload: { 'cognito:groups': [role] } } } },
      login: vi.fn(), logout: vi.fn(), checkUser: vi.fn()
    } as any);

    return render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter><AuditDetailView /></BrowserRouter>
      </QueryClientProvider>
    );
  };

  it('renders complete audit record data', async () => {
    renderWithRole('LoanOfficer');
    
    expect(await screen.findByText(/LOAN-999/)).toBeDefined();
    expect(screen.getByText('75')).toBeDefined();
    expect(screen.getByText('Income discrepancy exceeds 10%')).toBeDefined();
  });

  // Task 20.3 & 20.5: Test PII Masking Logic
  it('masks SSN permanently for Loan Officers', async () => {
    renderWithRole('LoanOfficer');
    
    const maskedSsn = await screen.findByText('***-**-6789');
    expect(maskedSsn).toBeDefined();
    
    // Unmask button should NOT exist for Loan Officers
    expect(screen.queryByTitle('Reveal PII')).toBeNull();
  });

  it('allows Administrators to explicitly unmask PII and logs the access', async () => {
    renderWithRole('Administrator');
    
    // Initially masked with dots
    const hiddenSsn = await screen.findByText('•••-••-••••');
    expect(hiddenSsn).toBeDefined();

    // Click to reveal
    const revealBtn = screen.getByTitle('Reveal PII');
    fireEvent.click(revealBtn);

    // Verify it unmasked
    expect(await screen.findByText('123-45-6789')).toBeDefined();
    
    // Verify API logging was triggered
    expect(api.logPiiAccess).toHaveBeenCalledWith('test-audit-123', 'ssn');
  });

  // Task 20.2 & 20.5: Test Inconsistency Filtering
  it('filters inconsistencies by severity', async () => {
    renderWithRole('LoanOfficer');
    
    await screen.findByText('Income discrepancy exceeds 10%'); // Wait for load
    
    expect(screen.getByText('CRITICAL')).toBeDefined();
    expect(screen.getByText('LOW')).toBeDefined();

    // Filter to CRITICAL only using the button
    const criticalButton = screen.getByRole('button', { name: /Critical \(1\)/i });
    fireEvent.click(criticalButton);

    expect(screen.getByText('CRITICAL')).toBeDefined();
    expect(screen.queryByText('LOW')).toBeNull(); // Low severity should disappear
  });

  // Task 20.2 & 20.5: Test Sorting Logic
  it('sorts inconsistencies by severity weight and field name', async () => {
    // Override the mock to have multiple severities
    vi.spyOn(api, 'fetchAuditById').mockResolvedValueOnce({
      ...mockAuditData,
      inconsistencies: [
        { id: '1', field_name: 'Zip Code', severity: 'LOW', expected_value: '111', actual_value: '222', sources: [] },
        { id: '2', field_name: 'Income', severity: 'CRITICAL', expected_value: '50k', actual_value: '40k', sources: [] },
        { id: '3', field_name: 'Address', severity: 'HIGH', expected_value: 'NY', actual_value: 'NJ', sources: [] }
      ]
    });
    
    renderWithRole('LoanOfficer');
    await screen.findByText('Zip Code');

    // Default sort is Severity Descending (CRITICAL -> HIGH -> LOW)
    let rows = screen.getAllByRole('row');
    expect(rows.length).toBeGreaterThan(3); // Header + 3 data rows
    expect(rows[1].textContent).toContain('CRITICAL'); // rows[0] is the header
    expect(rows[2].textContent).toContain('HIGH');
    expect(rows[3].textContent).toContain('LOW');

    // Click Severity Header to toggle to Ascending (LOW -> HIGH -> CRITICAL)
    const severityHeader = screen.getByText('Severity');
    fireEvent.click(severityHeader);
    
    rows = screen.getAllByRole('row');
    expect(rows[1].textContent).toContain('LOW');
    expect(rows[3].textContent).toContain('CRITICAL');

    // Click Field Header to sort alphabetically (Address -> Income -> Zip Code)
    const fieldHeader = screen.getByText('Field Name');
    fireEvent.click(fieldHeader);
    
    rows = screen.getAllByRole('row');
    // Check that Address appears before Income and Zip Code
    const row1Text = rows[1].textContent || '';
    const row2Text = rows[2].textContent || '';
    const row3Text = rows[3].textContent || '';
    
    expect(row1Text.includes('Address') || row2Text.includes('Address') || row3Text.includes('Address')).toBeTruthy();
    expect(row1Text.includes('Income') || row2Text.includes('Income') || row3Text.includes('Income')).toBeTruthy();
    expect(row1Text.includes('Zip Code') || row2Text.includes('Zip Code') || row3Text.includes('Zip Code')).toBeTruthy();
  });
});
