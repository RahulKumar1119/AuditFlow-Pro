// frontend/src/components/viewer/DocumentViewer.test.tsx

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import DocumentViewer from './DocumentViewer';
import DocumentComparisonView from './DocumentComparisonView';
import * as api from '../../services/api';

// Mock the API call
vi.mock('../../services/api', () => ({
  fetchDocumentViewUrl: vi.fn()
}));

// Mock react-pdf to prevent canvas rendering errors in the JSDOM test environment
vi.mock('react-pdf', () => ({
  pdfjs: { GlobalWorkerOptions: { workerSrc: '' } },
  Document: ({ children, onLoadSuccess }: any) => {
    // Simulate immediate successful load of a 5-page PDF
    setTimeout(() => onLoadSuccess({ numPages: 5 }), 0);
    return <div data-testid="mock-pdf-document">{children}</div>;
  },
  Page: ({ pageNumber }: any) => <div data-testid={`mock-pdf-page-${pageNumber}`}>Page {pageNumber}</div>
}));

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });

describe('DocumentViewer & Comparison Components', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(api, 'fetchDocumentViewUrl').mockResolvedValue({ view_url: 'http://mock-s3.com/doc.pdf' });
  });

  const renderViewer = (props: any) => render(
    <QueryClientProvider client={queryClient}>
      <DocumentViewer {...props} />
    </QueryClientProvider>
  );

  it('Task 21.1 & 21.4: Fetches URL and renders PDF viewer', async () => {
    renderViewer({ documentId: 'doc-123', loanApplicationId: 'loan-1', fileType: 'application/pdf' });
    
    // Check loading state
    expect(screen.getByText(/Loading secure document/i)).toBeDefined();

    // Check successful render
    await waitFor(() => {
      expect(screen.getByTestId('mock-pdf-document')).toBeDefined();
    });
    expect(api.fetchDocumentViewUrl).toHaveBeenCalledWith('doc-123', 'loan-1');
  });

  it('Task 21.1: Handles pagination correctly', async () => {
    renderViewer({ documentId: 'doc-123', loanApplicationId: 'loan-1', fileType: 'application/pdf', initialPage: 1 });
    
    await waitFor(() => {
      expect(screen.getByText('Page 1 of 5')).toBeDefined();
    });

    const nextBtn = screen.getByRole('button', { name: '' }); // The ChevronRight button
    
    // We target the explicit jump buttons based on their Title attributes
    const jumpBottomBtn = screen.getByTitle('Jump to Bottom');
    fireEvent.click(jumpBottomBtn);
    
    await waitFor(() => {
      expect(screen.getByText('Page 5 of 5')).toBeDefined();
    });
  });

  it('Task 21.2: Renders bounding box highlights with tooltips', async () => {
    const highlights = [{
      id: 'hl-1', page: 1, value: '$50,000', isFocused: true,
      box: { Width: 0.1, Height: 0.05, Left: 0.5, Top: 0.5 }
    }];

    renderViewer({ documentId: 'doc-123', loanApplicationId: 'loan-1', fileType: 'application/pdf', highlights });
    
    await waitFor(() => {
      expect(screen.getByTestId('mock-pdf-document')).toBeDefined();
    });

    // Hover tooltip value
    const highlightBox = screen.getByTitle('$50,000');
    expect(highlightBox).toBeDefined();
    // Verify it applied the focused 'red' styling
    expect(highlightBox.className).toContain('border-red-500');
  });

  it('Task 21.3: Renders side-by-side comparison view', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <DocumentComparisonView 
          loanApplicationId="loan-1"
          leftDoc={{ id: 'W2-2023', type: 'application/pdf', page: 1 }}
          rightDoc={{ id: 'Paystub', type: 'image/jpeg', page: 1 }}
        />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Source 1: W2-2023')).toBeDefined();
      expect(screen.getByText('Source 2: Paystub')).toBeDefined();
    });
    
    // API should be called twice (once for each viewer)
    expect(api.fetchDocumentViewUrl).toHaveBeenCalledTimes(2);
  });
});
