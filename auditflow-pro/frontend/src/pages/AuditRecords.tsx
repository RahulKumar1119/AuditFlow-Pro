// frontend/src/pages/AuditRecords.tsx
import { useState, useEffect } from 'react';
import { fetchAudits } from '../services/api';
import type { AuditRecord } from '../services/api';
import { CheckCircle, Clock, Search, Filter } from 'lucide-react';
import { Link } from 'react-router-dom';

const AuditRecords = () => {
  const [audits, setAudits] = useState<AuditRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRisk, setFilterRisk] = useState<string>('ALL');

  useEffect(() => {
    loadAuditRecords();
  }, []);

  const loadAuditRecords = async () => {
    try {
      setLoading(true);
      const data = await fetchAudits(100); // Fetch more records for the list view
      setAudits(data.items || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load audit records';
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

  // Filter audits based on search and risk level
  const filteredAudits = audits.filter(audit => {
    const matchesSearch = searchTerm === '' || 
      audit.loan_application_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (audit.applicant_name && audit.applicant_name.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesRisk = filterRisk === 'ALL' || audit.risk_level === filterRisk;
    
    return matchesSearch && matchesRisk;
  });

  if (loading) return <div className="flex h-64 items-center justify-center">Loading audit records...</div>;
  if (error) return <div className="text-red-600 p-4 border border-red-200 bg-red-50 rounded">{error}</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Audit Records</h1>
        <button 
          onClick={loadAuditRecords}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors text-sm"
        >
          Refresh
        </button>
      </div>

      {/* Search and Filter Bar */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Search Input */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              placeholder="Search by Loan ID or Applicant Name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Risk Level Filter */}
          <div className="flex items-center gap-2">
            <Filter size={20} className="text-gray-400" />
            <select
              value={filterRisk}
              onChange={(e) => setFilterRisk(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="ALL">All Risk Levels</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>
        </div>

        {/* Results Count */}
        <div className="mt-3 text-sm text-gray-600">
          Showing {filteredAudits.length} of {audits.length} records
        </div>
      </div>

      {/* Audit Records Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Loan ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Applicant Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Risk Level</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Inconsistencies</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Score</th>
                <th className="px-6 py-3"></th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredAudits.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-6 py-8 text-center text-sm text-gray-500">
                    {searchTerm || filterRisk !== 'ALL' 
                      ? 'No audit records match your filters.' 
                      : 'No audit records found.'}
                  </td>
                </tr>
              ) : (
                filteredAudits.map((audit) => (
                  <tr key={audit.audit_record_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600">
                      <Link to={`/audits/${audit.audit_record_id}`} className="hover:underline">
                        {audit.loan_application_id}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {audit.applicant_name || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(audit.audit_timestamp || '').toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric'
                      })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <span className="inline-flex items-center space-x-1">
                        {audit.status === 'COMPLETED' ? (
                          <CheckCircle size={14} className="text-green-500"/>
                        ) : (
                          <Clock size={14} className="text-blue-500"/>
                        )}
                        <span>{audit.status}</span>
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={getRiskBadge(audit.risk_level)}>{audit.risk_level}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {audit.inconsistencies?.length || 0}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-gray-900">
                      {audit.risk_score} / 100
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <Link 
                        to={`/audits/${audit.audit_record_id}`} 
                        className="text-blue-600 hover:text-blue-900 hover:underline"
                      >
                        View Details
                      </Link>
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

export default AuditRecords;
