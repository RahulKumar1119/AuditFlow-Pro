// auditflow-pro/frontend/src/components/dashboard/Dashboard.tsx
import { useState, useEffect } from 'react';
import { fetchAudits } from '../../services/api';
import type { AuditRecord } from '../../services/api';
import { MoreVertical } from 'lucide-react';
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
      const data = await fetchAudits(50);
      setAudits(data.items || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load dashboard data';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      'COMPLETED': 'text-green-600',
      'PENDING': 'text-red-600',
      'PROCESSING': 'text-gray-900'
    };
    return colors[status] || 'text-gray-600';
  };

  const getStatusDot = (status: string) => {
    const colors: Record<string, string> = {
      'COMPLETED': 'bg-green-500',
      'PENDING': 'bg-red-500',
      'PROCESSING': 'bg-gray-900'
    };
    return colors[status] || 'bg-yellow-500';
  };

  const getRiskBadge = (level: string) => {
    const styles: Record<string, string> = {
      'HIGH': 'bg-red-500 text-white',
      'CRITICAL': 'bg-red-600 text-white',
      'MEDIUM': 'bg-yellow-500 text-white',
      'LOW': 'bg-green-500 text-white'
    };
    return styles[level] || 'bg-gray-400 text-white';
  };

  const getRiskLabel = (level: string) => {
    const labels: Record<string, string> = {
      'HIGH': 'High Risk',
      'CRITICAL': 'High Risk',
      'MEDIUM': 'Medium Risk',
      'LOW': 'Low Risk'
    };
    return labels[level] || 'Unknown';
  };

  const getScoreBarColor = (score: number) => {
    if (score >= 90) return 'bg-green-500';
    if (score >= 70) return 'bg-yellow-500';
    if (score >= 50) return 'bg-orange-500';
    return 'bg-red-500';
  };

  if (loading) return <div className="flex h-64 items-center justify-center text-gray-600">Loading dashboard...</div>;
  if (error) return <div className="text-red-600 p-4 border border-red-200 bg-red-50 rounded">{error}</div>;

  return (
    <div className="space-y-6">
      {/* Data Table */}
      <div className="bg-white shadow-sm rounded-lg overflow-hidden border border-gray-200">
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Loan ID</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Applicant Name</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Loan Amount</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Risk Level</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">Score</th>
                <th className="px-6 py-4"></th>
              </tr>
            </thead>
            <tbody className="bg-white">
              {audits.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-sm text-gray-500">No loan applications found.</td>
                </tr>
              ) : (
                audits.map((audit) => (
                  <tr key={audit.audit_record_id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Link 
                        to={`/audits/${audit.audit_record_id}`}
                        className="text-sm font-medium text-gray-900 hover:text-blue-600 underline"
                      >
                        {audit.loan_application_id}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {audit.applicant_name || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      ${Math.floor(Math.random() * 150000 + 50000).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center space-x-2">
                        <span className={`w-2 h-2 rounded-full ${getStatusDot(audit.status)}`}></span>
                        <span className={`text-sm font-medium ${getStatusColor(audit.status)}`}>
                          {audit.status === 'COMPLETED' ? 'Complete' : audit.status === 'PROCESSING' ? 'Processing' : 'Pending'}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-block px-3 py-1 text-xs font-semibold rounded ${getRiskBadge(audit.risk_level)}`}>
                        {getRiskLabel(audit.risk_level)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center space-x-3">
                        <span className="text-sm font-bold text-gray-900 min-w-[60px]">
                          {audit.risk_score} / 100
                        </span>
                        <div className="flex-1 max-w-[100px]">
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div 
                              className={`h-2 rounded-full ${getScoreBarColor(audit.risk_score)}`}
                              style={{ width: `${audit.risk_score}%` }}
                            ></div>
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <button className="text-gray-400 hover:text-gray-600">
                        <MoreVertical size={20} />
                      </button>
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
