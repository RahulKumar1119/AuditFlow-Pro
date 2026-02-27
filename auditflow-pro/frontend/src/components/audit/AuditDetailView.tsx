// frontend/src/components/audit/AuditDetailView.tsx

import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchAuditById, logPiiAccess } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import { ShieldAlert, ArrowLeft, ShieldCheck, Eye, EyeOff, AlertCircle } from 'lucide-react';
import InconsistencyPanel from './InconsistencyPanel';

const AuditDetailView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [unmaskedFields, setUnmaskedFields] = useState<Set<string>>(new Set());

  // Extract user roles from Cognito token
  const groups = user?.signInUserSession?.accessToken?.payload['cognito:groups'] || [];
  const isAdmin = groups.includes('Administrator');

  const { data: audit, isLoading, isError } = useQuery({
    queryKey: ['audit', id],
    queryFn: () => fetchAuditById(id!),
    enabled: !!id
  });

  const handleUnmask = async (fieldName: string) => {
    if (!isAdmin) return;
    setUnmaskedFields(prev => new Set(prev).add(fieldName));
    await logPiiAccess(id!, fieldName); // Log the explicit access request
  };

  const renderPiiField = (fieldName: string, value: string, isSensitive: boolean = false) => {
    if (!isSensitive) return value;
    
    // Loan Officers always see masked data
    if (!isAdmin) return '***-**-' + value.slice(-4); 

    // Administrators must click to reveal
    const isUnmasked = unmaskedFields.has(fieldName);
    
    return (
      <div className="flex items-center space-x-2">
        <span className="font-mono">{isUnmasked ? value : '•••-••-••••'}</span>
        <button 
          onClick={() => isUnmasked ? setUnmaskedFields(prev => { const next = new Set(prev); next.delete(fieldName); return next; }) : handleUnmask(fieldName)}
          className="text-gray-400 hover:text-blue-600 focus:outline-none transition-colors"
          title={isUnmasked ? "Hide PII" : "Reveal PII"}
        >
          {isUnmasked ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
    );
  };

  if (isLoading) return <div className="p-8 text-center text-gray-500">Loading audit details...</div>;
  if (isError || !audit) return <div className="p-8 text-center text-red-500">Failed to load audit record.</div>;

  const isHighRisk = audit.risk_score > 50;

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12">
      <Link to="/dashboard" className="inline-flex items-center text-blue-600 hover:text-blue-800 transition-colors">
        <ArrowLeft size={16} className="mr-1" /> Back to Queue
      </Link>

      {/* Header & Risk Score Card */}
      <div className={`bg-white shadow rounded-lg p-6 flex items-start justify-between border-t-4 ${isHighRisk ? 'border-red-600' : 'border-blue-600'}`}>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Loan Application: {audit.loan_application_id}</h1>
          <p className="text-gray-500 mt-1">Audit Record ID: {audit.audit_record_id}</p>
          <div className="mt-4 flex space-x-4">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800">
              Status: {audit.status}
            </span>
          </div>
        </div>
        
        <div className={`p-6 rounded-lg border-2 text-center min-w-[150px] ${isHighRisk ? 'border-red-500 bg-red-50' : 'border-green-500 bg-green-50'}`}>
          <div className="flex items-center justify-center space-x-2 mb-2">
            {isHighRisk ? <ShieldAlert className="text-red-500" size={24} /> : <ShieldCheck className="text-green-500" size={24} />}
            <span className={`text-sm font-bold uppercase tracking-wider ${isHighRisk ? 'text-red-700' : 'text-green-700'}`}>
              {audit.risk_level}
            </span>
          </div>
          <div className={`text-4xl font-black ${isHighRisk ? 'text-red-600' : 'text-green-600'}`}>
            {audit.risk_score}
          </div>
          <div className="text-xs text-gray-500 mt-1">/ 100 Risk Score</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sidebar: Golden Record & Risk Factors */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-white shadow rounded-lg overflow-hidden border border-gray-200">
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
              <h3 className="text-lg font-medium text-gray-900">Golden Record</h3>
              <p className="text-xs text-gray-500 mt-1">Consolidated applicant data</p>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase">Applicant Name</label>
                <div className="mt-1 text-sm font-medium text-gray-900">{audit.golden_record?.first_name?.value} {audit.golden_record?.last_name?.value}</div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase flex items-center">
                  Social Security Number
                  {isAdmin && <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] bg-blue-100 text-blue-800 border border-blue-200">Admin View</span>}
                </label>
                <div className="mt-1 text-sm font-medium text-gray-900">
                  {renderPiiField('ssn', audit.golden_record?.ssn?.value || '', true)}
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 uppercase">Reported Income</label>
                <div className="mt-1 text-sm font-medium text-gray-900">${audit.golden_record?.annual_income?.value?.toLocaleString() || 'N/A'}</div>
              </div>
            </div>
          </div>

          {audit.risk_factors && audit.risk_factors.length > 0 && (
            <div className="bg-white shadow rounded-lg overflow-hidden border border-red-200">
              <div className="px-6 py-4 border-b border-red-200 bg-red-50">
                <h3 className="text-lg font-medium text-red-900">Contributing Risk Factors</h3>
              </div>
              <ul className="divide-y divide-red-100">
                {audit.risk_factors.map((factor: any, idx: number) => (
                  <li key={idx} className="p-4 text-sm text-red-800 bg-white flex items-start">
                    <AlertCircle size={16} className="mt-0.5 mr-2 flex-shrink-0" />
                    {factor.description}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Main Area: Inconsistencies Table */}
        <div className="lg:col-span-2">
          <InconsistencyPanel inconsistencies={audit.inconsistencies || []} />
        </div>
      </div>
    </div>
  );
};

export default AuditDetailView;
