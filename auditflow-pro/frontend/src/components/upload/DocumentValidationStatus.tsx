// frontend/src/components/upload/DocumentValidationStatus.tsx

import { useState, useEffect } from 'react';
import { CheckCircle, AlertCircle, Clock, XCircle } from 'lucide-react';

interface DocumentValidationStatusProps {
  loanApplicationId: string;
  onStatusChange?: (isValid: boolean) => void;
}

interface DocumentStatus {
  document_id: string;
  file_name: string;
  document_type: string;
  processing_status: 'COMPLETED' | 'PROCESSING' | 'FAILED' | 'PENDING';
  classification_confidence: number;
  extracted_data_fields: number;
  validation_errors?: string[];
}

const DocumentValidationStatus: React.FC<DocumentValidationStatusProps> = ({ 
  loanApplicationId, 
  onStatusChange 
}) => {
  const [documents, setDocuments] = useState<DocumentStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    const fetchDocumentStatus = async () => {
      try {
        setLoading(true);
        // Query DynamoDB for documents with this loan_application_id
        const response = await fetch(
          `${import.meta.env.VITE_API_URL || ''}/documents?loan_application_id=${loanApplicationId}`,
          {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json'
            }
          }
        );

        if (!response.ok) {
          throw new Error('Failed to fetch document status');
        }

        const data = await response.json();
        const docs = data.items || [];
        setDocuments(docs);

        // Check if all documents are valid
        const allValid = docs.length > 0 && docs.every((doc: DocumentStatus) => 
          doc.processing_status === 'COMPLETED' && 
          doc.classification_confidence > 0.7 &&
          !doc.validation_errors?.length
        );
        
        onStatusChange?.(allValid);

        // Stop auto-refresh if all documents are processed
        if (docs.length > 0 && docs.every((doc: DocumentStatus) => 
          doc.processing_status === 'COMPLETED' || doc.processing_status === 'FAILED'
        )) {
          setAutoRefresh(false);
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to fetch document status';
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    fetchDocumentStatus();

    // Auto-refresh every 3 seconds if still processing
    const interval = autoRefresh ? setInterval(fetchDocumentStatus, 3000) : undefined;
    return () => clearInterval(interval);
  }, [loanApplicationId, autoRefresh, onStatusChange]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'PROCESSING':
        return <Clock className="h-5 w-5 text-blue-500 animate-spin" />;
      case 'FAILED':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <AlertCircle className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      'COMPLETED': 'bg-green-100 text-green-800 border-green-200',
      'PROCESSING': 'bg-blue-100 text-blue-800 border-blue-200',
      'FAILED': 'bg-red-100 text-red-800 border-red-200',
      'PENDING': 'bg-gray-100 text-gray-800 border-gray-200'
    };
    return styles[status] || styles['PENDING'];
  };

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.9) return 'bg-green-100 text-green-800';
    if (confidence >= 0.7) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  if (loading && documents.length === 0) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center space-x-2">
          <Clock className="h-5 w-5 text-blue-500 animate-spin" />
          <p className="text-sm text-blue-800">Loading document validation status...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center space-x-2">
          <AlertCircle className="h-5 w-5 text-red-500" />
          <p className="text-sm text-red-800">{error}</p>
        </div>
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <p className="text-sm text-gray-600">No documents uploaded yet for this loan application.</p>
      </div>
    );
  }

  const allValid = documents.every(doc => 
    doc.processing_status === 'COMPLETED' && 
    doc.classification_confidence > 0.7 &&
    !doc.validation_errors?.length
  );

  const allProcessed = documents.every(doc => 
    doc.processing_status === 'COMPLETED' || doc.processing_status === 'FAILED'
  );

  return (
    <div className="space-y-4">
      {/* Overall Status Summary */}
      <div className={`border rounded-lg p-4 ${
        allValid ? 'bg-green-50 border-green-200' : 
        allProcessed ? 'bg-yellow-50 border-yellow-200' : 
        'bg-blue-50 border-blue-200'
      }`}>
        <div className="flex items-center space-x-3">
          {allValid ? (
            <>
              <CheckCircle className="h-6 w-6 text-green-600" />
              <div>
                <p className="font-semibold text-green-900">All Documents Valid</p>
                <p className="text-sm text-green-800">{documents.length} document(s) successfully processed and validated</p>
              </div>
            </>
          ) : allProcessed ? (
            <>
              <AlertCircle className="h-6 w-6 text-yellow-600" />
              <div>
                <p className="font-semibold text-yellow-900">Processing Complete - Review Required</p>
                <p className="text-sm text-yellow-800">Some documents need review or have low confidence scores</p>
              </div>
            </>
          ) : (
            <>
              <Clock className="h-6 w-6 text-blue-600 animate-spin" />
              <div>
                <p className="font-semibold text-blue-900">Processing Documents</p>
                <p className="text-sm text-blue-800">Classification and extraction in progress...</p>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Individual Document Status */}
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-gray-900">Document Details</h3>
        {documents.map((doc) => (
          <div key={doc.document_id} className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-start justify-between">
              <div className="flex items-start space-x-3 flex-1">
                {getStatusIcon(doc.processing_status)}
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <p className="font-medium text-gray-900">{doc.file_name}</p>
                    <span className={`px-2 py-1 text-xs font-semibold rounded border ${getStatusBadge(doc.processing_status)}`}>
                      {doc.processing_status}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 mt-1">
                    Type: <span className="font-medium">{doc.document_type}</span>
                  </p>
                </div>
              </div>
            </div>

            {/* Confidence Score */}
            <div className="mt-3 flex items-center space-x-2">
              <span className="text-xs text-gray-600">Classification Confidence:</span>
              <div className="flex items-center space-x-2">
                <div className="w-24 bg-gray-200 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full ${
                      doc.classification_confidence >= 0.9 ? 'bg-green-500' :
                      doc.classification_confidence >= 0.7 ? 'bg-yellow-500' :
                      'bg-red-500'
                    }`}
                    style={{ width: `${doc.classification_confidence * 100}%` }}
                  ></div>
                </div>
                <span className={`text-xs font-semibold px-2 py-1 rounded ${getConfidenceBadge(doc.classification_confidence)}`}>
                  {(doc.classification_confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>

            {/* Extracted Fields Count */}
            {doc.processing_status === 'COMPLETED' && (
              <p className="text-xs text-gray-600 mt-2">
                Extracted Fields: <span className="font-medium">{doc.extracted_data_fields}</span>
              </p>
            )}

            {/* Validation Errors */}
            {doc.validation_errors && doc.validation_errors.length > 0 && (
              <div className="mt-3 bg-red-50 border border-red-200 rounded p-2">
                <p className="text-xs font-semibold text-red-800 mb-1">Validation Issues:</p>
                <ul className="text-xs text-red-700 space-y-1">
                  {doc.validation_errors.map((error, idx) => (
                    <li key={idx} className="flex items-start space-x-1">
                      <span>•</span>
                      <span>{error}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Action Buttons */}
      {allValid && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-sm text-green-800">
            ✓ All documents are valid and ready for audit processing. You can now proceed to the dashboard to view audit results.
          </p>
        </div>
      )}
    </div>
  );
};

export default DocumentValidationStatus;
