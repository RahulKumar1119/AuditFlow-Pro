// frontend/src/components/upload/UploadZone.tsx

import React, { useState, useCallback, useRef } from 'react';
import { requestUploadUrl } from '../../services/api';
import { UploadCloud, File as FileIcon, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react';

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB limit
const ALLOWED_TYPES = ['application/pdf', 'image/jpeg', 'image/png', 'image/tiff'];

interface UploadableFile {
  id: string;
  file: File;
  progress: number;
  status: 'PENDING' | 'UPLOADING' | 'SUCCESS' | 'ERROR';
  error?: string;
}

// Task 17.3: Calculate SHA-256 checksum natively in the browser for S3 integrity
const calculateChecksum = async (file: File): Promise<string> => {
  const arrayBuffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return btoa(String.fromCharCode.apply(null, hashArray)); // Convert to Base64 for AWS
};

const UploadZone: React.FC<{ loanApplicationId?: string }> = ({ loanApplicationId }) => {
  const [uploads, setUploads] = useState<UploadableFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    if (!ALLOWED_TYPES.includes(file.type)) return 'Invalid file format. (PDF, JPEG, PNG, TIFF only)';
    if (file.size > MAX_FILE_SIZE) return 'File exceeds 50MB limit.';
    return null;
  };

  const handleFiles = (newFiles: FileList | File[]) => {
    const newUploads: UploadableFile[] = Array.from(newFiles).map(file => {
      const error = validateFile(file);
      return {
        id: crypto.randomUUID(),
        file,
        progress: 0,
        status: error ? 'ERROR' : 'PENDING',
        error: error || undefined
      };
    });

    setUploads(prev => [...prev, ...newUploads]);
    
    // Automatically start valid uploads
    newUploads.filter(u => u.status === 'PENDING').forEach(u => uploadFile(u));
  };

  const uploadFile = async (uploadRecord: UploadableFile) => {
    // Reset status to uploading and clear any previous errors
    setUploads(prev => prev.map(u => u.id === uploadRecord.id ? { ...u, status: 'UPLOADING', progress: 0, error: undefined } : u));

    try {
      // Task 17.3: Calculate the file checksum before sending
      const checksum = await calculateChecksum(uploadRecord.file);

      // Task 17.3: Get Pre-signed URL from API Gateway, passing the checksum
      const { upload_url_data } = await requestUploadUrl(
        uploadRecord.file.name, 
        uploadRecord.file.type, 
        loanApplicationId,
        checksum 
      );

      // Task 17.3: Prepare FormData for S3 Direct Post
      const formData = new FormData();
      Object.entries(upload_url_data.fields).forEach(([key, value]) => {
        formData.append(key, value as string);
      });
      
      // Task 17.3: Append checksum to payload for AWS S3 to verify
      formData.append('x-amz-checksum-sha256', checksum);
      formData.append('file', uploadRecord.file);

      // Task 17.3: Upload directly to S3 with Progress Tracking
      await new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', upload_url_data.url, true);

        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percentComplete = Math.round((event.loaded / event.total) * 100);
            setUploads(prev => prev.map(u => 
              u.id === uploadRecord.id ? { ...u, progress: percentComplete } : u
            ));
          }
        };

        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(xhr.response);
          } else {
            // Task 17.3: Handle S3 specific rejection (e.g., mismatched checksums or expired URLs)
            reject(new Error(`S3 Upload Rejected: Status ${xhr.status}`));
          }
        };
        
        xhr.onerror = () => reject(new Error('Network error during file upload'));
        xhr.send(formData);
      });

      // Mark success
      setUploads(prev => prev.map(u => u.id === uploadRecord.id ? { ...u, status: 'SUCCESS', progress: 100 } : u));

    } catch (error: any) {
      // Task 17.3: Handle upload errors with descriptive messages in the UI
      setUploads(prev => prev.map(u => u.id === uploadRecord.id ? { 
        ...u, 
        status: 'ERROR', 
        error: error.message || 'An unexpected error occurred during upload.' 
      } : u));
    }
  };

  // Drag and drop event handlers
  const onDragOver = useCallback((e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); }, []);
  const onDragLeave = useCallback((e: React.DragEvent) => { e.preventDefault(); setIsDragging(false); }, []);
  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) handleFiles(e.dataTransfer.files);
  }, []);

  return (
    <div className="w-full max-w-3xl mx-auto space-y-6">
      {/* Dropzone Area */}
      <div 
        onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors
          ${isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400 bg-gray-50'}`}
      >
        <input 
          type="file" multiple ref={fileInputRef} className="hidden" 
          accept=".pdf,.jpg,.jpeg,.png,.tiff" 
          onChange={(e) => { 
            if (e.target.files) handleFiles(e.target.files);
            // Reset input so the same file can be selected again if needed
            if (fileInputRef.current) fileInputRef.current.value = ''; 
          }}
        />
        <UploadCloud className="mx-auto h-12 w-12 text-gray-400 mb-4" />
        <p className="text-gray-700 font-medium">Click or drag files here to upload</p>
        <p className="text-sm text-gray-500 mt-2">Support for PDF, JPEG, PNG, TIFF (Max 50MB)</p>
      </div>

      {/* Upload List */}
      <div className="space-y-3">
        {uploads.map((upload) => (
          <div key={upload.id} className="bg-white border rounded p-4 shadow-sm flex items-center justify-between">
            <div className="flex items-center space-x-4 flex-1">
              <FileIcon className="text-blue-500 h-8 w-8" />
              <div className="flex-1">
                <div className="flex justify-between">
                  <span className="font-medium text-sm truncate w-64">{upload.file.name}</span>
                  <span className="text-sm text-gray-500">{(upload.file.size / 1024 / 1024).toFixed(2)} MB</span>
                </div>
                
                {/* Progress Bar */}
                <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                  <div 
                    className={`h-2 rounded-full transition-all duration-300 ${upload.status === 'ERROR' ? 'bg-red-500' : upload.status === 'SUCCESS' ? 'bg-green-500' : 'bg-blue-500'}`} 
                    style={{ width: `${upload.progress}%` }}
                  ></div>
                </div>
                {/* Descriptive Error Message display */}
                {upload.error && <p className="text-xs text-red-500 mt-1 font-medium">{upload.error}</p>}
              </div>
            </div>

            {/* Status Icons & Retry Button */}
            <div className="ml-4 flex items-center space-x-2">
              {upload.status === 'SUCCESS' && <CheckCircle className="text-green-500 h-5 w-5" />}
              {upload.status === 'ERROR' && (
                <>
                  <AlertCircle className="text-red-500 h-5 w-5" />
                  <button 
                    onClick={(e) => { e.stopPropagation(); uploadFile(upload); }} 
                    title="Retry Upload" 
                    className="text-gray-400 hover:text-blue-500 transition-colors"
                  >
                    <RefreshCw className="h-5 w-5" />
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default UploadZone;
