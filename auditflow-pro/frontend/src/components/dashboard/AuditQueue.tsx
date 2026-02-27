// frontend/src/components/dashboard/AuditQueue.tsx

import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchAudits } from '../../services/api';
import { Search, ChevronUp, ChevronDown, Filter, AlertTriangle } from 'lucide-react';

// Interfaces for our state
interface SortConfig {
  key: 'risk_score' | 'audit_timestamp' | 'status';
  direction: 'asc' | 'desc';
}

interface FilterState {
  search: string;
  status: string;
  minRisk: number;
}

const AuditQueue: React.FC = () => {
  const navigate = useNavigate();

  // Task 19.2: Persist filter and sort preferences in local storage
  const [filters, setFilters] = useState<FilterState>(() => {
    const saved = localStorage.getItem('auditQueueFilters');
    return saved ? JSON.parse(saved) : { search: '', status: 'ALL', minRisk: 0 };
  });

  const [sortConfig, setSortConfig] = useState<SortConfig>(() => {
    const saved = localStorage.getItem('auditQueueSort');
    return saved ? JSON.parse(saved) : { key: 'audit_timestamp', direction: 'desc' };
  });

  // Save to local storage whenever filters or sort change
  useEffect(() => {
    localStorage.setItem('auditQueueFilters', JSON.stringify(filters));
  }, [filters]);

  useEffect(() => {
    localStorage.setItem('auditQueueSort', JSON.stringify(sortConfig));
  }, [sortConfig]);

  // Task 19.1 & 19.3: Fetch data with React Query, polling every 30 seconds
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['audits'],
    queryFn: () => fetchAudits(100), // Fetch up to 100 for client-side filtering
    refetchInterval: 30000, // 30 seconds real-time polling
  });

  // Task 19.2: Implement sorting and filtering logic
  const processedAudits = useMemo(() => {
    if (!data?.items) return [];
    
    let filtered = data.items.filter((audit: any) => {
      // 1. Search by Loan ID or Applicant Name
      const searchMatch = 
        (audit.loan_application_id || '').toLowerCase().includes(filters.search.toLowerCase()) ||
        (audit.applicant_name || '').toLowerCase().includes(filters.search.toLowerCase());
      
      // 2. Filter by Status
      const statusMatch = filters.status === 'ALL' || audit.status === filters.status;
      
      // 3. Filter by Risk Score Threshold
      const riskMatch = (audit.risk_score || 0) >= filters.minRisk;

      return searchMatch && statusMatch && riskMatch;
    });

    // Sort Logic
    filtered.sort((a: any, b: any) => {
      let aVal = a[sortConfig.key];
      let bVal = b[sortConfig.key];

      if (sortConfig.key === 'audit_timestamp') {
        aVal = new Date(aVal || 0).getTime();
        bVal = new Date(bVal || 0).getTime();
      }

      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [data, filters, sortConfig]);

  const handleSort = (key: SortConfig['key']) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  // Helper for status badges (Task 19.1)
  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      PENDING: 'bg-gray-100 text-gray-800',
      PROCESSING: 'bg-blue-100 text-blue-800',
      COMPLETED: 'bg-green-100 text-green-800',
      FAILED: 'bg-red-100 text-red-800'
    };
    return `px-2 py-1 text-xs font-semibold rounded-full ${styles[status] || styles.PENDING}`;
  };

  if (isLoading) return <div className="p-8 text-center text-gray-500">Loading audit queue...</div>;
  if (isError) return <div className="p-8 text-center text-red-500">Error: {(error as Error).message}</div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-gray-900">Audit Queue</h2>
        <span className="text-sm text-gray-500">Auto-updates every 30s</span>
      </div>

      {/* Filters Toolbar */}
      <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 flex flex-wrap gap-4 items-center justify-between">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            placeholder="Search ID or Applicant Name..."
            value={filters.search}
            onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
            className="w-full pl-10 pr-4 py-2 border rounded-md focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <Filter size={18} className="text-gray-400" />
            <select
              value={filters.status}
              onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value }))}
              className="border rounded-md px-3 py-2 bg-white"
            >
              <option value="ALL">All Statuses</option>
              <option value="PENDING">Pending</option>
              <option value="PROCESSING">Processing</option>
              <option value="COMPLETED">Completed</option>
              <option value="FAILED">Failed</option>
            </select>
          </div>
          
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-600 font-medium">Min Risk:</span>
            <input
              type="number"
              min="0" max="100"
              value={filters.minRisk}
              onChange={(e) => setFilters(prev => ({ ...prev, minRisk: Number(e.target.value) }))}
              className="border rounded-md px-3 py-2 w-20"
            />
          </div>
        </div>
      </div>

      {/* Data Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden border border-gray-200">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th 
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors" 
                  onClick={() => handleSort('audit_timestamp')}
                >
                  <div className="flex items-center space-x-1">
                    <span>Upload Date</span>
                    {sortConfig.key === 'audit_timestamp' && (sortConfig.direction === 'asc' ? <ChevronUp size={14}/> : <ChevronDown size={14}/>)}
                  </div>
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Loan ID / Applicant
                </th>
                <th 
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors" 
                  onClick={() => handleSort('status')}
                >
                  <div className="flex items-center space-x-1">
                    <span>Status</span>
                    {sortConfig.key === 'status' && (sortConfig.direction === 'asc' ? <ChevronUp size={14}/> : <ChevronDown size={14}/>)}
                  </div>
                </th>
                <th 
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors" 
                  onClick={() => handleSort('risk_score')}
                >
                  <div className="flex items-center space-x-1">
                    <span>Risk Score</span>
                    {sortConfig.key === 'risk_score' && (sortConfig.direction === 'asc' ? <ChevronUp size={14}/> : <ChevronDown size={14}/>)}
                  </div>
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {processedAudits.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-gray-500">
                    No applications match your filters.
                  </td>
                </tr>
              ) : (
                processedAudits.map((audit: any) => {
                  // Task 19.1: Highlight high-risk applications
                  const isHighRisk = audit.risk_score > 50; 
                  
                  return (
                    // Task 19.4: Make table rows clickable to view detailed audit records
                    <tr 
                      key={audit.audit_record_id} 
                      onClick={() => navigate(`/audits/${audit.audit_record_id}`)}
                      className={`cursor-pointer hover:bg-blue-50 transition-colors ${isHighRisk ? 'bg-red-50' : ''}`}
                    >
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(audit.audit_timestamp).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-blue-600">{audit.loan_application_id}</div>
                        <div className="text-sm text-gray-500">{audit.applicant_name || 'Processing...'}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={getStatusBadge(audit.status)}>{audit.status}</span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className={`flex items-center space-x-2 text-sm font-bold ${isHighRisk ? 'text-red-600' : 'text-gray-900'}`}>
                          <span>{audit.risk_score || 0}</span>
                          {isHighRisk && <AlertTriangle size={16} className="text-red-500" />}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AuditQueue;
