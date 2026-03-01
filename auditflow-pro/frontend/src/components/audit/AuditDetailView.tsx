// frontend/src/components/audit/AuditDetailView.tsx

import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchAuditById, logPiiAccess } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import { ShieldAlert, ArrowLeft, ShieldCheck, Eye, EyeOff, AlertCircle, User, DollarSign, Calendar, FileText, TrendingUp } from 'lucide-react';
import InconsistencyPanel from './InconsistencyPanel';

interface CognitoUser {
  signInUserSession?: {
    accessToken?: {
      payload?: {
        'cognito:groups'?: string[];
      };
    };
  };
}

const AuditDetailView: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [unmaskedFields, setUnmaskedFields] = useState<Set<string>>(new Set());

  // Extract user roles from Cognito token
  const cognitoUser = user as unknown as CognitoUser;
  const groups = cognitoUser?.signInUserSession?.accessToken?.payload?.['cognito:groups'] || [];
  const isAdmin = groups.includes('Administrator');

  const { data: audit, isLoading, isError } = useQuery({
    queryKey: ['audit', id],
    queryFn: () => fetchAuditById(id!),
    enabled: !!id
  });

  const handleUnmask = async (fieldName: string) => {
    if (!isAdmin) return;
    setUnmaskedFields(prev => new Set(prev).add(fieldName));
    await logPiiAccess(id!, fieldName);
  };

  const renderPiiField = (fieldName: string, value: string, isSensitive: boolean = false) => {
    if (!isSensitive) return value;
    
    if (!isAdmin) return '***-**-' + value.slice(-4); 

    const isUnmasked = unmaskedFields.has(fieldName);
    
    return (
      <div className="flex items-center space-x-2">
        <span className="font-mono text-sm">{isUnmasked ? value : '•••-••-••••'}</span>
        <button 
          onClick={() => isUnmasked ? setUnmaskedFields(prev => { const next = new Set(prev); next.delete(fieldName); return next; }) : handleUnmask(fieldName)}
          className="text-gray-400 hover:text-blue-600 focus:outline-none transition-colors p-1 rounded hover:bg-blue-50"
          title={isUnmasked ? "Hide PII" : "Reveal PII"}
        >
          {isUnmasked ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading audit details...</p>
        </div>
      </div>
    );
  }

  if (isError || !audit) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-600 font-medium">Failed to load audit record</p>
          <Link to="/dashboard" className="text-blue-600 hover:text-blue-800 mt-4 inline-block">
            Return to Dashboard
          </Link>
        </div>
      </div>
    );
  }

  const isHighRisk = audit.risk_score > 50;
  const riskColor = audit.risk_score >= 80 ? 'red' : audit.risk_score >= 50 ? 'orange' : audit.risk_score >= 25 ? 'yellow' : 'green';
  const riskBgColor = {
    red: 'bg-red-50 border-red-200',
    orange: 'bg-orange-50 border-orange-200',
    yellow: 'bg-yellow-50 border-yellow-200',
    green: 'bg-green-50 border-green-200'
  }[riskColor];
  const riskTextColor = {
    red: 'text-red-700',
    orange: 'text-orange-700',
    yellow: 'text-yellow-700',
    green: 'text-green-700'
  }[riskColor];
  const riskIconColor = {
    red: 'text-red-600',
    orange: 'text-orange-600',
    yellow: 'text-yellow-600',
    green: 'text-green-600'
  }[riskColor];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50/30 pb-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Breadcrumb */}
        <Link 
          to="/dashboard" 
          className="inline-flex items-center text-sm font-medium text-gray-600 hover:text-blue-600 transition-colors group"
        >
          <ArrowLeft size={16} className="mr-2 group-hover:-translate-x-1 transition-transform" />
          Back to Audit Queue
        </Link>

        {/* Header Card */}
        <div className="bg-white rounded-xl shadow-lg overflow-hidden border border-gray-200">
          <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-8 py-6">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-2">
                  <FileText className="text-white" size={28} />
                  <h1 className="text-3xl font-bold text-white">
                    {audit.loan_application_id}
                  </h1>
                </div>
                <p className="text-blue-100 text-sm">
                  Audit ID: {audit.audit_record_id}
                </p>
                <div className="mt-4 flex items-center space-x-4">
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-white/20 text-white backdrop-blur-sm">
                    <Calendar size={14} className="mr-1.5" />
                    {new Date(audit.audit_timestamp || '').toLocaleDateString()}
                  </span>
                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${
                    audit.status === 'COMPLETED' ? 'bg-green-500/20 text-green-100' : 
                    audit.status === 'PENDING' ? 'bg-yellow-500/20 text-yellow-100' : 
                    'bg-gray-500/20 text-gray-100'
                  }`}>
                    {audit.status}
                  </span>
                </div>
              </div>
              
              {/* Risk Score Badge */}
              <div className={`${riskBgColor} border-2 rounded-2xl p-6 text-center min-w-[180px] shadow-lg backdrop-blur-sm bg-white/90`}>
                <div className="flex items-center justify-center space-x-2 mb-3">
                  {isHighRisk ? (
                    <ShieldAlert className={riskIconColor} size={28} />
                  ) : (
                    <ShieldCheck className={riskIconColor} size={28} />
                  )}
                  <span className={`text-sm font-bold uppercase tracking-wider ${riskTextColor}`}>
                    {audit.risk_level}
                  </span>
                </div>
                <div className={`text-5xl font-black ${riskTextColor} mb-2`}>
                  {audit.risk_score}
                </div>
                <div className="text-xs text-gray-600 font-medium">Risk Score / 100</div>
                <div className="mt-3 w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full transition-all duration-500 ${
                      riskColor === 'red' ? 'bg-red-600' :
                      riskColor === 'orange' ? 'bg-orange-600' :
                      riskColor === 'yellow' ? 'bg-yellow-600' :
                      'bg-green-600'
                    }`}
                    style={{ width: `${audit.risk_score}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sidebar */}
          <div className="lg:col-span-1 space-y-6">
            {/* Golden Record Card */}
            <div className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-200 hover:shadow-lg transition-shadow">
              <div className="bg-gradient-to-r from-emerald-500 to-teal-500 px-6 py-4">
                <div className="flex items-center space-x-2">
                  <ShieldCheck className="text-white" size={20} />
                  <h3 className="text-lg font-bold text-white">Golden Record</h3>
                </div>
                <p className="text-emerald-100 text-xs mt-1">Verified applicant data</p>
              </div>
              <div className="p-6 space-y-5">
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                    <User className="text-blue-600" size={20} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                      Applicant Name
                    </label>
                    <div className="text-sm font-semibold text-gray-900 truncate">
                      {audit.golden_record?.first_name?.value} {audit.golden_record?.last_name?.value}
                    </div>
                  </div>
                </div>

                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                    <FileText className="text-purple-600" size={20} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1 flex items-center">
                      Social Security Number
                      {isAdmin && (
                        <span className="ml-2 px-2 py-0.5 rounded-full text-[10px] bg-blue-100 text-blue-800 border border-blue-200 font-bold">
                          ADMIN
                        </span>
                      )}
                    </label>
                    <div className="text-sm font-semibold text-gray-900">
                      {renderPiiField('ssn', audit.golden_record?.ssn?.value || '', true)}
                    </div>
                  </div>
                </div>

                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                    <DollarSign className="text-green-600" size={20} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                      Annual Income
                    </label>
                    <div className="text-sm font-semibold text-gray-900">
                      ${audit.golden_record?.annual_income?.value?.toLocaleString() || 'N/A'}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Risk Factors Card */}
            {audit.risk_factors && audit.risk_factors.length > 0 && (
              <div className="bg-white rounded-xl shadow-md overflow-hidden border border-red-200 hover:shadow-lg transition-shadow">
                <div className="bg-gradient-to-r from-red-500 to-pink-500 px-6 py-4">
                  <div className="flex items-center space-x-2">
                    <TrendingUp className="text-white" size={20} />
                    <h3 className="text-lg font-bold text-white">Risk Factors</h3>
                  </div>
                  <p className="text-red-100 text-xs mt-1">{audit.risk_factors.length} contributing factors</p>
                </div>
                <div className="divide-y divide-red-100">
                  {audit.risk_factors.map((factor: { description: string }, idx: number) => (
                    <div key={idx} className="p-4 hover:bg-red-50/50 transition-colors">
                      <div className="flex items-start space-x-3">
                        <AlertCircle size={18} className="text-red-500 flex-shrink-0 mt-0.5" />
                        <p className="text-sm text-gray-700 leading-relaxed">{factor.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Main Content - Inconsistencies */}
          <div className="lg:col-span-2">
            <InconsistencyPanel inconsistencies={audit.inconsistencies || []} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuditDetailView;
