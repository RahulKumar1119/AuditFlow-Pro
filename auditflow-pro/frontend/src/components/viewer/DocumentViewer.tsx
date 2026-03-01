// frontend/src/components/viewer/DocumentViewer.tsx

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Document, Page, pdfjs } from 'react-pdf';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
import type { ReactZoomPanPinchRef } from 'react-zoom-pan-pinch';
import { fetchDocumentViewUrl } from '../../services/api';
import { ZoomIn, ZoomOut, Maximize, ChevronLeft, ChevronRight, ArrowUpToLine, ArrowDownToLine } from 'lucide-react';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

interface BoundingBox {
  Width: number; Height: number; Left: number; Top: number;
}

interface Highlight {
  id: string;
  page: number;
  box: BoundingBox;
  value: string;
  isFocused?: boolean;
}

interface Props {
  documentId: string;
  loanApplicationId: string;
  fileType: string; // e.g., 'application/pdf', 'image/jpeg'
  highlights?: Highlight[];
  initialPage?: number;
  // Callbacks and refs for synchronized scrolling in side-by-side mode
  onZoomPan?: (state: { scale: number; positionX: number; positionY: number }) => void;
  syncRef?: React.RefObject<ReactZoomPanPinchRef | null>;
}

const DocumentViewer: React.FC<Props> = ({ 
  documentId, 
  loanApplicationId, 
  fileType, 
  highlights = [], 
  initialPage = 1, 
  onZoomPan, 
  syncRef 
}) => {
  const [numPages, setNumPages] = useState<number>(1);
  const [pageNumber, setPageNumber] = useState<number>(initialPage);

  // Listen for initialPage changes from clicks in the InconsistencyPanel
  useEffect(() => {
    setPageNumber(initialPage);
  }, [initialPage]);

  // Fetch and cache the pre-signed URL via React Query
  const { data, isLoading, isError } = useQuery({
    queryKey: ['documentUrl', documentId],
    queryFn: () => fetchDocumentViewUrl(documentId, loanApplicationId),
    staleTime: 14 * 60 * 1000 // Cache for 14 minutes (S3 URL expires in 15m)
  });

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
  };

  const currentPageHighlights = highlights.filter(h => h.page === pageNumber);
  const isPdf = fileType === 'application/pdf';

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-lg shadow-sm">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-blue-700 font-medium">Loading secure document...</p>
        </div>
      </div>
    );
  }
  
  if (isError || !data?.view_url) {
    return (
      <div className="flex h-96 items-center justify-center bg-gradient-to-br from-red-50 to-pink-50 border border-red-200 rounded-lg shadow-sm">
        <div className="text-center">
          <div className="text-red-500 text-5xl mb-4">⚠️</div>
          <p className="text-red-700 font-semibold text-lg">Failed to load document securely</p>
          <p className="text-red-600 text-sm mt-2">Please try again or contact support</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-gray-50 to-gray-100 border border-gray-300 rounded-xl overflow-hidden shadow-lg">
      {/* Enhanced Toolbar with gradient background */}
      <div className="flex items-center justify-between px-6 py-3 bg-gradient-to-r from-slate-700 via-slate-800 to-slate-900 border-b border-slate-600 shadow-md">
        <div className="flex items-center space-x-3">
          <button 
            disabled={pageNumber <= 1} 
            onClick={() => setPageNumber(1)} 
            className="p-2 rounded-lg bg-slate-600/50 hover:bg-slate-600 disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-200 text-white shadow-sm hover:shadow-md" 
            title="Jump to Top"
          >
            <ArrowUpToLine size={18} />
          </button>
          <button 
            disabled={pageNumber <= 1} 
            onClick={() => setPageNumber(p => p - 1)} 
            className="p-2 rounded-lg bg-slate-600/50 hover:bg-slate-600 disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-200 text-white shadow-sm hover:shadow-md"
            title="Previous Page"
          >
            <ChevronLeft size={18} />
          </button>
          <div className="px-4 py-1.5 bg-slate-900/50 rounded-lg border border-slate-600">
            <span className="text-sm font-semibold text-white">Page {pageNumber}</span>
            <span className="text-xs text-slate-300 mx-1">of</span>
            <span className="text-sm font-semibold text-slate-200">{numPages}</span>
          </div>
          <button 
            disabled={pageNumber >= numPages} 
            onClick={() => setPageNumber(p => p + 1)} 
            className="p-2 rounded-lg bg-slate-600/50 hover:bg-slate-600 disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-200 text-white shadow-sm hover:shadow-md"
            title="Next Page"
          >
            <ChevronRight size={18} />
          </button>
          <button 
            disabled={pageNumber >= numPages} 
            onClick={() => setPageNumber(numPages)} 
            className="p-2 rounded-lg bg-slate-600/50 hover:bg-slate-600 disabled:opacity-30 disabled:cursor-not-allowed transition-all duration-200 text-white shadow-sm hover:shadow-md" 
            title="Jump to Bottom"
          >
            <ArrowDownToLine size={18} />
          </button>
        </div>
        
        {/* Document info badge */}
        <div className="flex items-center space-x-2">
          <span className="text-xs text-slate-300 font-medium">
            {isPdf ? '📄 PDF Document' : '🖼️ Image Document'}
          </span>
        </div>
      </div>

      {/* Enhanced viewer with improved zoom controls */}
      <div className="flex-1 overflow-hidden relative cursor-grab active:cursor-grabbing bg-gradient-to-br from-gray-100 via-gray-200 to-gray-300">
        <TransformWrapper 
          ref={syncRef}
          initialScale={1} 
          minScale={0.5} 
          maxScale={4} 
          centerOnInit
          onTransformed={(ref) => onZoomPan && onZoomPan(ref.state)}
        >
          {({ zoomIn, zoomOut, resetTransform }) => (
            <>
              {/* Enhanced zoom control panel */}
              <div className="absolute top-6 right-6 z-10 flex flex-col space-y-2 bg-white/95 backdrop-blur-sm rounded-xl shadow-xl p-2 border border-gray-200">
                <button 
                  onClick={() => zoomIn()} 
                  className="p-2.5 hover:bg-gradient-to-br hover:from-blue-50 hover:to-indigo-50 rounded-lg transition-all duration-200 text-slate-700 hover:text-blue-600 hover:shadow-md group" 
                  title="Zoom In"
                >
                  <ZoomIn size={20} className="group-hover:scale-110 transition-transform" />
                </button>
                <div className="h-px bg-gray-200"></div>
                <button 
                  onClick={() => zoomOut()} 
                  className="p-2.5 hover:bg-gradient-to-br hover:from-blue-50 hover:to-indigo-50 rounded-lg transition-all duration-200 text-slate-700 hover:text-blue-600 hover:shadow-md group" 
                  title="Zoom Out"
                >
                  <ZoomOut size={20} className="group-hover:scale-110 transition-transform" />
                </button>
                <div className="h-px bg-gray-200"></div>
                <button 
                  onClick={() => resetTransform()} 
                  className="p-2.5 hover:bg-gradient-to-br hover:from-blue-50 hover:to-indigo-50 rounded-lg transition-all duration-200 text-slate-700 hover:text-blue-600 hover:shadow-md group" 
                  title="Reset Zoom"
                >
                  <Maximize size={20} className="group-hover:scale-110 transition-transform" />
                </button>
              </div>

              <TransformComponent wrapperClass="w-full h-full flex items-center justify-center">
                <div className="relative inline-block shadow-2xl bg-white rounded-lg overflow-hidden border-4 border-white">
                  {/* Render Document (PDF or Image) */}
                  {isPdf ? (
                    <Document file={data.view_url} onLoadSuccess={onDocumentLoadSuccess} loading="Rendering PDF...">
                      <Page pageNumber={pageNumber} renderTextLayer={false} renderAnnotationLayer={false} width={800} />
                    </Document>
                  ) : (
                    <img src={data.view_url} alt="Document" className="max-w-[800px] h-auto pointer-events-none" />
                  )}

                  {/* Enhanced Highlight Bounding Boxes Overlay */}
                  {currentPageHighlights.map((hl) => (
                    <div
                      key={hl.id}
                      title={hl.value}
                      className={`absolute border-2 transition-all duration-200 rounded-sm ${
                        hl.isFocused 
                          ? 'border-red-500 bg-red-500/25 z-10 shadow-lg ring-2 ring-red-400/50' 
                          : 'border-blue-500 bg-blue-500/15 hover:bg-blue-500/30 hover:border-blue-600 hover:shadow-md'
                      }`}
                      style={{
                        left: `${hl.box.Left * 100}%`,
                        top: `${hl.box.Top * 100}%`,
                        width: `${hl.box.Width * 100}%`,
                        height: `${hl.box.Height * 100}%`,
                      }}
                    />
                  ))}
                </div>
              </TransformComponent>
            </>
          )}
        </TransformWrapper>
      </div>
    </div>
  );
};

export default DocumentViewer;
