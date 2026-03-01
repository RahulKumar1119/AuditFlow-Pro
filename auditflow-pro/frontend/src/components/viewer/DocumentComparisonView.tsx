// frontend/src/components/viewer/DocumentComparisonView.tsx

import { useRef, useState } from 'react';
import type { ReactZoomPanPinchRef } from 'react-zoom-pan-pinch';
import DocumentViewer from './DocumentViewer';
import { Link2, Link2Off } from 'lucide-react';

interface Highlight {
  id: string;
  page: number;
  box: { Width: number; Height: number; Left: number; Top: number };
  value: string;
  isFocused?: boolean;
}

interface ComparisonProps {
  loanApplicationId: string;
  leftDoc: { id: string; type: string; page: number };
  rightDoc: { id: string; type: string; page: number };
  sharedHighlights?: Highlight[]; 
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
    <div className="h-[800px] flex flex-col bg-gradient-to-br from-white to-gray-50 p-6 rounded-xl shadow-xl border border-gray-200">
      {/* Enhanced header with gradient */}
      <div className="flex justify-between items-center mb-6 pb-4 border-b-2 border-gradient-to-r from-blue-200 to-indigo-200">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg shadow-md">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
            Side-by-Side Document Comparison
          </h3>
        </div>
        
        {/* Enhanced sync toggle button */}
        <button 
          onClick={() => setIsSyncEnabled(!isSyncEnabled)}
          className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 shadow-md hover:shadow-lg ${
            isSyncEnabled 
              ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white hover:from-blue-600 hover:to-indigo-700' 
              : 'bg-gradient-to-r from-gray-100 to-gray-200 text-gray-700 hover:from-gray-200 hover:to-gray-300 border border-gray-300'
          }`}
        >
          {isSyncEnabled ? (
            <>
              <Link2 size={18} className="animate-pulse" />
              <span>Scroll Synced</span>
            </>
          ) : (
            <>
              <Link2Off size={18} />
              <span>Scroll Independent</span>
            </>
          )}
        </button>
      </div>
      
      {/* Enhanced split-view layout */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6 h-full min-h-0">
        {/* Left document panel */}
        <div className="h-full flex flex-col border-2 border-gray-300 rounded-xl overflow-hidden shadow-lg hover:shadow-xl transition-shadow duration-200">
          <div className="bg-gradient-to-r from-slate-700 to-slate-800 text-white px-4 py-2.5 font-semibold flex items-center justify-between shadow-md">
            <div className="flex items-center space-x-2">
              <span className="text-xs bg-slate-600 px-2 py-1 rounded-md">Source 1</span>
              <span className="text-sm">{leftDoc.id}</span>
            </div>
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

        {/* Right document panel */}
        <div className="h-full flex flex-col border-2 border-blue-300 rounded-xl overflow-hidden shadow-lg hover:shadow-xl transition-shadow duration-200">
          <div className="bg-gradient-to-r from-blue-700 to-indigo-800 text-white px-4 py-2.5 font-semibold flex items-center justify-between shadow-md">
            <div className="flex items-center space-x-2">
              <span className="text-xs bg-blue-600 px-2 py-1 rounded-md">Source 2</span>
              <span className="text-sm">{rightDoc.id}</span>
            </div>
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
