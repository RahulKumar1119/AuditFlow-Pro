// frontend/src/components/viewer/DocumentViewer.tsx

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Document, Page, pdfjs } from 'react-pdf';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';
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
}

const DocumentViewer: React.FC<Props> = ({ documentId, loanApplicationId, fileType, highlights = [], initialPage = 1 }) => {
  const [numPages, setNumPages] = useState<number>(1);
  const [pageNumber, setPageNumber] = useState<number>(initialPage);

  // Task 21.4: Fetch and cache the pre-signed URL via React Query
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

  if (isLoading) return <div className="flex h-96 items-center justify-center bg-gray-50 border rounded animate-pulse">Loading secure document...</div>;
  if (isError || !data?.view_url) return <div className="flex h-96 items-center justify-center bg-red-50 text-red-500 border rounded">Failed to load document securely.</div>;

  return (
    <div className="flex flex-col h-full bg-gray-100 border border-gray-300 rounded-lg overflow-hidden">
      {/* Task 21.1: Toolbar with Zoom, Pan, and explicit Navigation controls */}
      <div className="flex items-center justify-between px-4 py-2 bg-white border-b border-gray-300 shadow-sm">
        <div className="flex items-center space-x-2">
          <button 
            disabled={pageNumber <= 1} 
            onClick={() => setPageNumber(1)} 
            className="p-1 rounded hover:bg-gray-100 disabled:opacity-50" title="Jump to Top"
          >
            <ArrowUpToLine size={18} />
          </button>
          <button 
            disabled={pageNumber <= 1} 
            onClick={() => setPageNumber(p => p - 1)} 
            className="p-1 rounded hover:bg-gray-100 disabled:opacity-50"
          >
            <ChevronLeft size={18} />
          </button>
          <span className="text-sm font-medium">Page {pageNumber} of {numPages}</span>
          <button 
            disabled={pageNumber >= numPages} 
            onClick={() => setPageNumber(p => p + 1)} 
            className="p-1 rounded hover:bg-gray-100 disabled:opacity-50"
          >
            <ChevronRight size={18} />
          </button>
          <button 
            disabled={pageNumber >= numPages} 
            onClick={() => setPageNumber(numPages)} 
            className="p-1 rounded hover:bg-gray-100 disabled:opacity-50" title="Jump to Bottom"
          >
            <ArrowDownToLine size={18} />
          </button>
        </div>
      </div>

      {/* Task 21.1: Embedded viewer with zoom and pan controls */}
      <div className="flex-1 overflow-hidden relative cursor-grab active:cursor-grabbing bg-gray-200">
        <TransformWrapper initialScale={1} minScale={0.5} maxScale={4} centerOnInit>
          {({ zoomIn, zoomOut, resetTransform }) => (
            <>
              <div className="absolute top-4 right-4 z-10 flex flex-col space-y-2 bg-white rounded shadow-md p-1">
                <button onClick={() => zoomIn()} className="p-1.5 hover:bg-gray-100 rounded" title="Zoom In"><ZoomIn size={18} /></button>
                <button onClick={() => zoomOut()} className="p-1.5 hover:bg-gray-100 rounded" title="Zoom Out"><ZoomOut size={18} /></button>
                <button onClick={() => resetTransform()} className="p-1.5 hover:bg-gray-100 rounded" title="Reset Zoom"><Maximize size={18} /></button>
              </div>

              <TransformComponent wrapperClass="w-full h-full flex items-center justify-center">
                <div className="relative inline-block shadow-lg bg-white">
                  {/* Render Document (PDF or Image) */}
                  {isPdf ? (
                    <Document file={data.view_url} onLoadSuccess={onDocumentLoadSuccess} loading="Rendering PDF...">
                      <Page pageNumber={pageNumber} renderTextLayer={false} renderAnnotationLayer={false} width={800} />
                    </Document>
                  ) : (
                    <img src={data.view_url} alt="Document" className="max-w-[800px] h-auto pointer-events-none" />
                  )}

                  {/* Task 21.2: Highlight Bounding Boxes Overlay */}
                  {currentPageHighlights.map((hl) => (
                    <div
                      key={hl.id}
                      title={hl.value} // Tooltip on hover
                      className={`absolute border-2 transition-colors duration-200 ${hl.isFocused ? 'border-red-500 bg-red-500/20 z-10' : 'border-blue-500 bg-blue-500/10 hover:bg-blue-500/30'}`}
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
