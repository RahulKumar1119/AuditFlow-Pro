// auditflow-pro/frontend/src/components/dashboard/Dashboard.test.jsx
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Dashboard from './Dashboard';
import { fetchAudits } from '../../services/api';

// Mock the API service
jest.mock('../../services/api');

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
    jest.clearAllMocks();
  });

  test('displays loading state initially', () => {
    fetchAudits.mockImplementation(() => new Promise(() => {})); // Never resolves
    renderDashboard();
    expect(screen.getByText(/loading dashboard/i)).toBeInTheDocument();
  });

  test('renders metrics and data table on successful fetch', async () => {
    fetchAudits.mockResolvedValueOnce(mockAudits);
    renderDashboard();

    // Wait for the data to load
    await waitFor(() => {
      expect(screen.queryByText(/loading dashboard/i)).not.toBeInTheDocument();
    });

    // Check Metrics logic
    expect(screen.getByText('2')).toBeInTheDocument(); // Total processed
    expect(screen.getByText('1')).toBeInTheDocument(); // High/Critical risk (Jane Doe)

    // Check Table data
    expect(screen.getByText('loan-123')).toBeInTheDocument();
    expect(screen.getByText('Jane Doe')).toBeInTheDocument();
    expect(screen.getByText('CRITICAL')).toBeInTheDocument();
    expect(screen.getByText('95 / 100')).toBeInTheDocument();
  });

  test('displays error message on API failure', async () => {
    fetchAudits.mockRejectedValueOnce(new Error('Network Error'));
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument();
    });
  });
});
