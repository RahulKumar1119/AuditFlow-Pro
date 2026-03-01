// frontend/src/pages/Upload.tsx
import React, { useState } from 'react';
import UploadZone from '../components/upload/UploadZone';
import { FileText } from 'lucide-react';

const Upload: React.FC = () => {
  const [loanApplicationId, setLoanApplicationId] = useState('');

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-3">
        <FileText className="h-8 w-8 text-blue-600" />
        <h1 className="text-2xl font-bold text-gray-900">Upload Documents</h1>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <div className="mb-6">
          <label htmlFor="loanId" className="block text-sm font-medium text-gray-700 mb-2">
            Loan Application ID (Optional)
          </label>
          <input
            type="text"
            id="loanId"
            value={loanApplicationId}
            onChange={(e) => setLoanApplicationId(e.target.value)}
            placeholder="Enter loan application ID to associate documents"
            className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
          />
          <p className="mt-2 text-sm text-gray-500">
            If provided, all uploaded documents will be associated with this loan application.
          </p>
        </div>

        <UploadZone loanApplicationId={loanApplicationId || undefined} />
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-blue-900 mb-2">Upload Guidelines</h3>
        <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
          <li>Supported formats: PDF, JPEG, PNG, TIFF</li>
          <li>Maximum file size: 50MB per file</li>
          <li>Multiple files can be uploaded simultaneously</li>
          <li>Documents are automatically classified and processed</li>
          <li>You can view audit results in the Dashboard after processing completes</li>
        </ul>
      </div>
    </div>
  );
};

export default Upload;
