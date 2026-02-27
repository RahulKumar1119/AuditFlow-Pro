// frontend/src/components/audit/InconsistencyPanel.tsx

import React, { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, Filter, FileText, ChevronUp, ChevronDown } from 'lucide-react';

interface SourceDoc {
  documentId: string;
  type: string;
  page: number;
}

interface Inconsistency {
  id: string;
  field_name: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  expected_value: string;
  actual_value: string;
  sources: SourceDoc[];
}

interface Props {
  inconsistencies: Inconsistency[];
}

type SortKey = 'field_name' | 'severity';

const InconsistencyPanel: React.FC<Props> = ({ inconsistencies }) => {
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [sortConfig, setSortConfig] = useState<{ key: SortKey; direction: 'asc' | 'desc' }>({
    key: 'severity',
    direction: 'desc'
  });

  const processedInconsistencies = useMemo(() => {
    // 1. Filter by severity
    let processed = inconsistencies.filter(inc => 
      severityFilter === 'ALL' || inc.severity === severityFilter
    );

    // 2. Sort by weight or alphabetical
    processed.sort((a, b) => {
      if (sortConfig.key === 'severity') {
        const severityWeight: Record<string, number> = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };
        const aWeight = severityWeight[a.severity] || 0;
        const bWeight = severityWeight[b.severity] || 0;
        if (aWeight < bWeight) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aWeight > bWeight) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      } else {
        const aVal = a.field_name.toLowerCase();
        const bVal = b.field_name.toLowerCase();
        if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      }
    });

    return processed;
  }, [inconsistencies, severityFilter, sortConfig]);

  const handleSort = (key: SortKey) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc'
    }));
  };

  const getSeverityBadge = (severity: string) => {
    const styles: Record<string, string> = {
      CRITICAL: 'bg-red-100 text-red-800 border-red-200',
      HIGH: 'bg-orange-100 text-orange-800 border-orange-200',
      MEDIUM: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      LOW: 'bg-gray-100 text-gray-800 border-gray-200'
    };
    return `px-2 py-1 text-xs font-bold rounded-full border ${styles[severity] || styles.LOW}`;
  };

  return (
    <div className="bg-white shadow rounded-lg overflow-hidden border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
        <h3 className="text-lg font-medium text-gray-900 flex items-center">
          <AlertCircle className="mr-2 text-red-500" size={20} />
          Detected Inconsistencies ({processedInconsistencies.length})
        </h3>
        <div className="flex items-center space-x-2">
          <Filter size={16} className="text-gray-400" />
          <select 
            className="text-sm border rounded p-1 bg-white"
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>
      </div>
      
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-white">
            <tr>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-50 transition-colors"
                onClick={() => handleSort('field_name')}
              >
                <div className="flex items-center space-x-1">
                  <span>Field</span>
                  {sortConfig.key === 'field_name' && (sortConfig.direction === 'asc' ? <ChevronUp size={14}/> : <ChevronDown size={14}/>)}
                </div>
              </th>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-50 transition-colors"
                onClick={() => handleSort('severity')}
              >
                <div className="flex items-center space-x-1">
                  <span>Severity</span>
                  {sortConfig.key === 'severity' && (sortConfig.direction === 'asc' ? <ChevronUp size={14}/> : <ChevronDown size={14}/>)}
                </div>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Expected (Golden Record)</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actual Found</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Source Documents</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {processedInconsistencies.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-gray-500">No inconsistencies match the current filter.</td>
              </tr>
            ) : (
              processedInconsistencies.map((inc) => (
                <tr key={inc.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">{inc.field_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap"><span className={getSeverityBadge(inc.severity)}>{inc.severity}</span></td>
                  <td className="px-6 py-4 text-sm text-green-700 bg-green-50/30 font-medium">{inc.expected_value}</td>
                  <td className="px-6 py-4 text-sm text-red-700 bg-red-50/30 font-medium">{inc.actual_value}</td>
                  <td className="px-6 py-4 text-sm">
                    <ul className="space-y-1">
                      {inc.sources?.map((source, idx) => (
                        <li key={idx}>
                          <Link 
                            to={`/documents/${source.documentId}/view?page=${source.page}`}
                            className="flex items-center text-blue-600 hover:text-blue-800 hover:underline"
                          >
                            <FileText size={14} className="mr-1" />
                            {source.type} (Page {source.page})
                          </Link>
                        </li>
                      ))}
                    </ul>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default InconsistencyPanel;
