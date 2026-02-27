// frontend/src/components/upload/UploadZone.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import UploadZone from './UploadZone';
import * as api from '../../services/api';

// Mock the API call
vi.mock('../../services/api', () => ({
  requestUploadUrl: vi.fn()
}));

describe('UploadZone Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders dropzone correctly', () => {
    render(<UploadZone />);
    expect(screen.getByText(/Click or drag files here to upload/i)).toBeDefined();
    expect(screen.getByText(/Support for PDF, JPEG, PNG, TIFF/i)).toBeDefined();
  });

  it('rejects files larger than 50MB', async () => {
    render(<UploadZone />);
    
    // Create a fake file that is 51MB
    const largeFile = new File(['x'.repeat(51 * 1024 * 1024)], 'huge.pdf', { type: 'application/pdf' });
    
    // Simulate drop
    const dropzone = screen.getByText(/Click or drag files here to upload/i).parentElement!;
    fireEvent.drop(dropzone, { dataTransfer: { files: [largeFile] } });

    await waitFor(() => {
      expect(screen.getByText(/File exceeds 50MB limit/i)).toBeDefined();
    });
    // Ensure API was not called
    expect(api.requestUploadUrl).not.toHaveBeenCalled();
  });

  it('rejects unsupported file formats', async () => {
    render(<UploadZone />);
    
    const badFile = new File(['mock content'], 'virus.exe', { type: 'application/x-msdownload' });
    
    const dropzone = screen.getByText(/Click or drag files here to upload/i).parentElement!;
    fireEvent.drop(dropzone, { dataTransfer: { files: [badFile] } });

    await waitFor(() => {
      expect(screen.getByText(/Invalid file format/i)).toBeDefined();
    });
  });

  it('attempts upload for valid files', async () => {
    // Mock successful API response
    vi.spyOn(api, 'requestUploadUrl').mockResolvedValueOnce({
      upload_url_data: { url: 'http://mock-s3.com', fields: {} }
    });

    render(<UploadZone />);
    const goodFile = new File(['mock content'], 'w2_form.pdf', { type: 'application/pdf' });
    
    const dropzone = screen.getByText(/Click or drag files here to upload/i).parentElement!;
    fireEvent.drop(dropzone, { dataTransfer: { files: [goodFile] } });

    await waitFor(() => {
      expect(screen.getByText('w2_form.pdf')).toBeDefined();
      expect(api.requestUploadUrl).toHaveBeenCalled();
    });
  });
});
