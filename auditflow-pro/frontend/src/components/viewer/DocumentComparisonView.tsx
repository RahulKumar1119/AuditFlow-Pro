// frontend/src/components/viewer/DocumentComparisonView.tsx

import React from 'react';
import DocumentViewer from './DocumentViewer';

interface ComparisonProps {
  loanApplicationId: string;
  leftDoc: { id: string; type: string; page: number };
  rightDoc: { id: string; type: string; page: number };
  sharedHighlights?: any[]; // Pass highlights to both to synchronize the view
}

const DocumentComparisonView: React.FC<ComparisonProps> = ({ loanApplicationId, leftDoc, rightDoc, sharedHighlights }) => {
  return (
    <div className="h-[800px] flex flex-col bg-white p-4 rounded-lg shadow border border-gray-200">
      <h3 className="text-lg font-bold text-gray-800 mb-4">Side-by-Side Document Comparison</h3>
      
      {/* Task 21.3: Split-view layout */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4 h-full min-h-0">
        <div className="h-full flex flex-col">
          <div className="bg-gray-800 text-white text-xs px-3 py-1 rounded-t-md font-mono">Source 1: {leftDoc.id}</div>
          <div className="flex-1 overflow-hidden">
            <DocumentViewer 
              documentId={leftDoc.id} 
              loanApplicationId={loanApplicationId} 
              fileType={leftDoc.type}
              initialPage={leftDoc.page}
              highlights={sharedHighlights}
            />
          </div>
        </div>

        <div className="h-full flex flex-col">
          <div className="bg-blue-800 text-white text-xs px-3 py-1 rounded-t-md font-mono">Source 2: {rightDoc.id}</div>
          <div className="flex-1 overflow-hidden">
            <DocumentViewer 
              documentId={rightDoc.id} 
              loanApplicationId={loanApplicationId} 
              fileType={rightDoc.type}
              initialPage={rightDoc.page}
              highlights={sharedHighlights}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentComparisonView;
