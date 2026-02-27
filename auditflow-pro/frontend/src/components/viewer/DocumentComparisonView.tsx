// frontend/src/components/viewer/DocumentComparisonView.tsx

import React, { useRef, useState } from 'react';
import { ReactZoomPanPinchRef } from 'react-zoom-pan-pinch';
import DocumentViewer from './DocumentViewer';
import { Link2, Link2Off } from 'lucide-react';

interface ComparisonProps {
  loanApplicationId: string;
  leftDoc: { id: string; type: string; page: number };
  rightDoc: { id: string; type: string; page: number };
  sharedHighlights?: any[]; 
}

const DocumentComparisonView: React.FC<ComparisonProps> = ({ loanApplicationId, leftDoc, rightDoc, sharedHighlights }) => {
  // References to synchronize scrolling
  const leftRef = useRef<ReactZoomPanPinchRef>(null);
  const rightRef = useRef<ReactZoomPanPinchRef>(null);
  const [isSyncEnabled, setIsSyncEnabled] = useState(true);

  // When the left viewer pans/zooms, apply exact state to the right viewer
  const handleLeftTransform = (state: { scale: number; positionX: number; positionY: number }) => {
    if (isSyncEnabled && rightRef.current) {
      rightRef.current.setTransform(state.positionX, state.positionY, state.scale);
    }
  };

  // When the right viewer pans/zooms, apply exact state to the left viewer
  const handleRightTransform = (state: { scale: number; positionX: number; positionY: number }) => {
    if (isSyncEnabled && leftRef.current) {
      leftRef.current.setTransform(state.positionX, state.positionY, state.scale);
    }
  };

  return (
    <div className="h-[800px] flex flex-col bg-white p-4 rounded-lg shadow border border-gray-200">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-bold text-gray-800">Side-by-Side Document Comparison</h3>
        
        <button 
          onClick={() => setIsSyncEnabled(!isSyncEnabled)}
          className={`flex items-center space-x-2 px-3 py-1.5 rounded text-sm font-medium transition-colors ${isSyncEnabled ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'}`}
        >
          {isSyncEnabled ? <><Link2 size={16}/> <span>Scroll Synced</span></> : <><Link2Off size={16}/> <span>Scroll Independent</span></>}
        </button>
      </div>
      
      {/* Split-view layout */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4 h-full min-h-0">
        <div className="h-full flex flex-col border border-gray-300 rounded overflow-hidden shadow-sm">
          <div className="bg-gray-800 text-white text-xs px-3 py-1 font-mono flex justify-between">
            <span>Source 1: {leftDoc.id}</span>
          </div>
          <div className="flex-1 overflow-hidden">
            <DocumentViewer 
              documentId={leftDoc.id} 
              loanApplicationId={loanApplicationId} 
              fileType={leftDoc.type}
              initialPage={leftDoc.page}
              highlights={sharedHighlights}
              syncRef={leftRef}
              onZoomPan={handleLeftTransform}
            />
          </div>
        </div>

        <div className="h-full flex flex-col border border-gray-300 rounded overflow-hidden shadow-sm">
          <div className="bg-blue-800 text-white text-xs px-3 py-1 font-mono flex justify-between">
            <span>Source 2: {rightDoc.id}</span>
          </div>
          <div className="flex-1 overflow-hidden">
            <DocumentViewer 
              documentId={rightDoc.id} 
              loanApplicationId={loanApplicationId} 
              fileType={rightDoc.type}
              initialPage={rightDoc.page}
              highlights={sharedHighlights}
              syncRef={rightRef}
              onZoomPan={handleRightTransform}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentComparisonView;
