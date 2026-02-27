// frontend/src/components/dashboard/AuditQueue.test.tsx

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AuditQueue from './AuditQueue';
import * as api from '../../services/api';

// Mock Router Navigation
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

// Mock API
vi.mock('../../services/api', () => ({
  fetchAudits: vi.fn()
}));

const mockData = {
  items: [
    { audit_record_id: '1', loan_application_id: 'L-100', applicant_name: 'Alice', status: 'COMPLETED', risk_score: 20, audit_timestamp: '2026-01-01T10:00:00Z' },
    { audit_record_id: '2', loan_application_id: 'L-200', applicant_name: 'Bob', status: 'PENDING', risk_score: 85, audit_timestamp: '2026-01-02T10:00:00Z' },
    { audit_record_id: '3', loan_application_id: 'L-300', applicant_name: 'Charlie', status: 'FAILED', risk_score: 50, audit_timestamp: '2026-01-03T10:00:00Z' },
  ]
};

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } } // Disable retries for faster tests
});

const renderComponent = () => render(
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <AuditQueue />
    </BrowserRouter>
  </QueryClientProvider>
);

describe('AuditQueue Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.spyOn(api, 'fetchAudits').mockResolvedValue(mockData);
  });

  it('renders the table and highlights high risk applications', async () => {
    renderComponent();
    
    // Wait for Bob (who has a risk score of 85) to appear
    const bobRow = await screen.findByText('L-200');
    expect(bobRow).toBeDefined();
    
    // Task 19.1: High risk (> 50) should be highlighted
    const bobScore = screen.getByText('85');
    expect(bobScore.className).toContain('text-red-600');
  });

  it('filters data by search term', async () => {
    renderComponent();
    await screen.findByText('Alice'); // Wait for load
    
    // Search for Charlie
    const searchInput = screen.getByPlaceholderText(/Search ID or Applicant Name/i);
    fireEvent.change(searchInput, { target: { value: 'Charlie' } });

    expect(screen.queryByText('Alice')).toBeNull();
    expect(screen.getByText('Charlie')).toBeDefined();
  });

  it('filters data by minimum risk score', async () => {
    renderComponent();
    await screen.findByText('Alice'); 
    
    // Set min risk to 60
    const minRiskInput = screen.getByRole('spinbutton'); // The number input
    fireEvent.change(minRiskInput, { target: { value: '60' } });

    // Only Bob (85) should remain
    expect(screen.queryByText('Alice')).toBeNull();
    expect(screen.queryByText('Charlie')).toBeNull();
    expect(screen.getByText('Bob')).toBeDefined();
  });

  it('sorts data by risk score when clicking header', async () => {
    renderComponent();
    await screen.findByText('Alice');

    const riskHeader = screen.getByText('Risk Score');
    
    // Click once for Ascending
    fireEvent.click(riskHeader);
    let rows = screen.getAllByRole('row');
    // Header is rows[0]. Alice (20) should be first data row.
    expect(rows[1].textContent).toContain('Alice'); 

    // Click again for Descending
    fireEvent.click(riskHeader);
    rows = screen.getAllByRole('row');
    // Bob (85) should now be first data row.
    expect(rows[1].textContent).toContain('Bob'); 
  });

  it('navigates to detail view on row click', async () => {
    renderComponent();
    
    const aliceRow = await screen.findByText('Alice');
    // Task 19.4: Click the row to navigate
    fireEvent.click(aliceRow);

    expect(mockNavigate).toHaveBeenCalledWith('/audits/1');
  });
});
