// auditflow-pro/frontend/src/components/dashboard/Dashboard.tsx
import { useState, useEffect } from 'react';
import { fetchAudits } from '../../services/api';
import type { AuditRecord } from '../../services/api';
import { AlertTriangle, CheckCircle, Clock } from 'lucide-react';
import { Link } from 'react-router-dom';

const Dashboard = () => {
  const [audits, setAudits] = useState<AuditRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const data = await fetchAudits(50); // Fetch top 50 recent records
      setAudits(data.items || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load dashboard data';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Helper for risk badge styling
  const getRiskBadge = (level: string) => {
    const styles: Record<string, string> = {
      CRITICAL: 'bg-red-100 text-red-800 border-red-200',
      HIGH: 'bg-orange-100 text-orange-800 border-orange-200',
      MEDIUM: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      LOW: 'bg-green-100 text-green-800 border-green-200',
      UNKNOWN: 'bg-gray-100 text-gray-800 border-gray-200'
    };
    const style = styles[level];
    return `px-2 py-1 text-xs font-semibold rounded-full border ${style !== undefined ? style : styles.UNKNOWN}`;
  };

  if (loading) return <div className="flex h-64 items-center justify-center">Loading dashboard...</div>;
  if (error) return <div className="text-red-600 p-4 border border-red-200 bg-red-50 rounded">{error}</div>;

  // Calculate top-level metrics
  const totalAudits = audits.length;
  const highRiskCount = audits.filter(a => a.risk_level === 'HIGH' || a.risk_level === 'CRITICAL').length;
  const completedCount = audits.filter(a => a.status === 'COMPLETED').length;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard Overview</h1>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="bg-white rounded-lg shadow p-5 flex items-center space-x-4 border-l-4 border-blue-500">
          <div className="p-3 bg-blue-100 rounded-full text-blue-600"><Clock size={24} /></div>
          <div>
            <p className="text-sm font-medium text-gray-500">Total Processed</p>
            <p className="text-2xl font-bold text-gray-900">{totalAudits}</p>
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-5 flex items-center space-x-4 border-l-4 border-red-500">
          <div className="p-3 bg-red-100 rounded-full text-red-600"><AlertTriangle size={24} /></div>
          <div>
            <p className="text-sm font-medium text-gray-500">High/Critical Risk</p>
            <p className="text-2xl font-bold text-gray-900">{highRiskCount}</p>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-5 flex items-center space-x-4 border-l-4 border-green-500">
          <div className="p-3 bg-green-100 rounded-full text-green-600"><CheckCircle size={24} /></div>
          <div>
            <p className="text-sm font-medium text-gray-500">Completed Audits</p>
            <p className="text-2xl font-bold text-gray-900">{completedCount}</p>
          </div>
        </div>
      </div>

      {/* Data Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-lg font-medium text-gray-900">Recent Loan Applications</h2>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Loan ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Applicant Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Risk Level</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Score</th>
                <th className="px-6 py-3"></th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {audits.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-4 text-center text-sm text-gray-500">No audit records found.</td>
                </tr>
              ) : (
                audits.map((audit) => (
                  <tr key={audit.audit_record_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600">
                      <Link to={`/audits/${audit.audit_record_id}`}>{audit.loan_application_id}</Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{audit.applicant_name || 'Unknown'}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(audit.audit_timestamp || '').toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <span className="inline-flex items-center space-x-1">
                        {audit.status === 'COMPLETED' ? <CheckCircle size={14} className="text-green-500"/> : <Clock size={14} className="text-blue-500"/>}
                        <span>{audit.status}</span>
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={getRiskBadge(audit.risk_level)}>{audit.risk_level}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-gray-900">
                      {audit.risk_score} / 100
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <Link to={`/audits/${audit.audit_record_id}`} className="text-blue-600 hover:text-blue-900">View Details</Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
