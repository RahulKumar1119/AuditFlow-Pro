// frontend/src/components/audit/InconsistencyPanel.tsx

import React, { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, Filter, FileText, ChevronUp, ChevronDown, AlertTriangle, XCircle, Info } from 'lucide-react';

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
    let processed = inconsistencies.filter(inc => 
      severityFilter === 'ALL' || inc.severity === severityFilter
    );

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

  const getSeverityConfig = (severity: string) => {
    const configs: Record<string, { badge: string; icon: JSX.Element; bg: string }> = {
      CRITICAL: {
        badge: 'bg-red-100 text-red-800 border-red-300',
        icon: <XCircle size={16} className="text-red-600" />,
        bg: 'bg-red-50/50'
      },
      HIGH: {
        badge: 'bg-orange-100 text-orange-800 border-orange-300',
        icon: <AlertTriangle size={16} className="text-orange-600" />,
        bg: 'bg-orange-50/50'
      },
      MEDIUM: {
        badge: 'bg-yellow-100 text-yellow-800 border-yellow-300',
        icon: <AlertCircle size={16} className="text-yellow-600" />,
        bg: 'bg-yellow-50/50'
      },
      LOW: {
        badge: 'bg-gray-100 text-gray-800 border-gray-300',
        icon: <Info size={16} className="text-gray-600" />,
        bg: 'bg-gray-50/50'
      }
    };
    return configs[severity] || configs.LOW;
  };

  const severityCounts = useMemo(() => {
    return {
      CRITICAL: inconsistencies.filter(i => i.severity === 'CRITICAL').length,
      HIGH: inconsistencies.filter(i => i.severity === 'HIGH').length,
      MEDIUM: inconsistencies.filter(i => i.severity === 'MEDIUM').length,
      LOW: inconsistencies.filter(i => i.severity === 'LOW').length,
    };
  }, [inconsistencies]);

  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-200">
      {/* Header */}
      <div className="bg-gradient-to-r from-red-500 to-pink-500 px-6 py-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-white/20 rounded-lg flex items-center justify-center backdrop-blur-sm">
              <AlertCircle className="text-white" size={22} />
            </div>
            <div>
              <h3 className="text-xl font-bold text-white">Data Inconsistencies</h3>
              <p className="text-red-100 text-sm">{processedInconsistencies.length} issues detected</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-gray-50 border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center space-x-2">
            <Filter size={18} className="text-gray-500" />
            <span className="text-sm font-medium text-gray-700">Filter by severity:</span>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setSeverityFilter('ALL')}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                severityFilter === 'ALL'
                  ? 'bg-blue-600 text-white shadow-md'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              All ({inconsistencies.length})
            </button>
            <button
              onClick={() => setSeverityFilter('CRITICAL')}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                severityFilter === 'CRITICAL'
                  ? 'bg-red-600 text-white shadow-md'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              Critical ({severityCounts.CRITICAL})
            </button>
            <button
              onClick={() => setSeverityFilter('HIGH')}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                severityFilter === 'HIGH'
                  ? 'bg-orange-600 text-white shadow-md'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              High ({severityCounts.HIGH})
            </button>
            <button
              onClick={() => setSeverityFilter('MEDIUM')}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                severityFilter === 'MEDIUM'
                  ? 'bg-yellow-600 text-white shadow-md'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              Medium ({severityCounts.MEDIUM})
            </button>
            <button
              onClick={() => setSeverityFilter('LOW')}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                severityFilter === 'LOW'
                  ? 'bg-gray-600 text-white shadow-md'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
              }`}
            >
              Low ({severityCounts.LOW})
            </button>
          </div>
        </div>
      </div>
      
      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th 
                className="px-6 py-4 text-left text-xs font-bold text-gray-600 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors group"
                onClick={() => handleSort('field_name')}
              >
                <div className="flex items-center space-x-2">
                  <span>Field Name</span>
                  {sortConfig.key === 'field_name' && (
                    sortConfig.direction === 'asc' ? <ChevronUp size={16} className="text-blue-600"/> : <ChevronDown size={16} className="text-blue-600"/>
                  )}
                </div>
              </th>
              <th 
                className="px-6 py-4 text-left text-xs font-bold text-gray-600 uppercase tracking-wider cursor-pointer hover:bg-gray-100 transition-colors group"
                onClick={() => handleSort('severity')}
              >
                <div className="flex items-center space-x-2">
                  <span>Severity</span>
                  {sortConfig.key === 'severity' && (
                    sortConfig.direction === 'asc' ? <ChevronUp size={16} className="text-blue-600"/> : <ChevronDown size={16} className="text-blue-600"/>
                  )}
                </div>
              </th>
              <th className="px-6 py-4 text-left text-xs font-bold text-gray-600 uppercase tracking-wider">
                Expected Value
              </th>
              <th className="px-6 py-4 text-left text-xs font-bold text-gray-600 uppercase tracking-wider">
                Actual Value
              </th>
              <th className="px-6 py-4 text-left text-xs font-bold text-gray-600 uppercase tracking-wider">
                Source Documents
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {processedInconsistencies.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center">
                  <div className="flex flex-col items-center justify-center space-y-3">
                    <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center">
                      <Filter className="text-gray-400" size={32} />
                    </div>
                    <p className="text-gray-500 font-medium">No inconsistencies match the current filter</p>
                    <button
                      onClick={() => setSeverityFilter('ALL')}
                      className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                    >
                      Clear filter
                    </button>
                  </div>
                </td>
              </tr>
            ) : (
              processedInconsistencies.map((inc) => {
                const config = getSeverityConfig(inc.severity);
                return (
                  <tr key={inc.id} className={`hover:bg-gray-50 transition-colors ${config.bg}`}>
                    <td className="px-6 py-4">
                      <span className="text-sm font-semibold text-gray-900">{inc.field_name}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center space-x-2">
                        {config.icon}
                        <span className={`px-3 py-1 text-xs font-bold rounded-full border ${config.badge}`}>
                          {inc.severity}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span className="text-sm font-medium text-green-700 bg-green-50 px-3 py-1 rounded-md border border-green-200">
                          {inc.expected_value}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                        <span className="text-sm font-medium text-red-700 bg-red-50 px-3 py-1 rounded-md border border-red-200">
                          {inc.actual_value}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="space-y-2">
                        {inc.sources?.map((source, idx) => (
                          <Link 
                            key={idx}
                            to={`/documents/${source.documentId}/view?page=${source.page}`}
                            className="flex items-center space-x-2 text-blue-600 hover:text-blue-800 hover:bg-blue-50 px-2 py-1 rounded-md transition-colors group"
                          >
                            <FileText size={16} className="flex-shrink-0" />
                            <span className="text-sm font-medium group-hover:underline">
                              {source.type} <span className="text-gray-500">• Page {source.page}</span>
                            </span>
                          </Link>
                        ))}
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
  );
};

export default InconsistencyPanel;
