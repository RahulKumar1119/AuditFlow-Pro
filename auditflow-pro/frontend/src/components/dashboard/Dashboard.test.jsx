// auditflow-pro/frontend/src/components/dashboard/Dashboard.test.jsx
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import Dashboard from './Dashboard';
import * as api from '../../services/api';

// Mock the API service
vi.mock('../../services/api');

const mockAudits = {
  items: [
    {
      audit_record_id: 'audit-1',
      loan_application_id: 'loan-123',
      applicant_name: 'Jane Doe',
      audit_timestamp: '2026-02-26T10:00:00Z',
      status: 'COMPLETED',
      risk_level: 'CRITICAL',
      risk_score: 95
    },
    {
      audit_record_id: 'audit-2',
      loan_application_id: 'loan-456',
      applicant_name: 'John Smith',
      audit_timestamp: '2026-02-26T11:00:00Z',
      status: 'COMPLETED',
      risk_level: 'LOW',
      risk_score: 10
    }
  ]
};

describe('Dashboard Component', () => {
  const renderDashboard = () => {
    return render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('displays loading state initially', () => {
    vi.spyOn(api, 'fetchAudits').mockImplementation(() => new Promise(() => {})); // Never resolves
    renderDashboard();
    expect(screen.getByText(/loading dashboard/i)).toBeDefined();
  });

  it('renders metrics and data table on successful fetch', async () => {
    vi.spyOn(api, 'fetchAudits').mockResolvedValueOnce(mockAudits);
    renderDashboard();

    // Wait for the data to load
    await waitFor(() => {
      expect(screen.queryByText(/loading dashboard/i)).toBeNull();
    });

    // Check Metrics logic - use more specific queries
    const metrics = screen.getAllByText('2');
    expect(metrics.length).toBeGreaterThanOrEqual(2); // Total processed and Completed audits
    expect(screen.getByText('1')).toBeDefined(); // High/Critical risk (Jane Doe)

    // Check Table data
    expect(screen.getByText('loan-123')).toBeDefined();
    expect(screen.getByText('Jane Doe')).toBeDefined();
    expect(screen.getByText('CRITICAL')).toBeDefined();
    expect(screen.getByText('95 / 100')).toBeDefined();
  });

  it('displays error message on API failure', async () => {
    vi.spyOn(api, 'fetchAudits').mockRejectedValueOnce(new Error('Network Error'));
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeDefined();
    });
  });
});
