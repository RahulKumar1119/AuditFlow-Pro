// Test setup file for vitest
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
import '@testing-library/jest-dom';

// Declare global types for test environment
declare global {
  interface Window {
    ResizeObserver: typeof ResizeObserver;
  }
}

// Mock ResizeObserver for jsdom
globalThis.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock File.prototype.arrayBuffer for tests
File.prototype.arrayBuffer = async function() {
  // Create a simple ArrayBuffer from the file content
  const text = this.name + this.type + this.size; // Use file metadata as content
  const encoder = new TextEncoder();
  const uint8Array = encoder.encode(text);
  return uint8Array.buffer;
};

// Mock crypto.subtle for tests
if (!globalThis.crypto) {
  Object.defineProperty(globalThis, 'crypto', {
    value: {} as Crypto,
    writable: true,
    configurable: true
  });
}

if (!globalThis.crypto.subtle) {
  Object.defineProperty(globalThis.crypto, 'subtle', {
    value: {
      digest: async (_algorithm: string, data: BufferSource) => {
        // Handle different input types - just return a fake hash
        // We don't actually use the buffer in tests
        if (data instanceof ArrayBuffer || ArrayBuffer.isView(data)) {
          // Valid input, proceed
        }
        
        // Return a fake hash
        const hashBuffer = new ArrayBuffer(32);
        const view = new Uint8Array(hashBuffer);
        for (let i = 0; i < 32; i++) {
          view[i] = i;
        }
        return hashBuffer;
      },
    } as SubtleCrypto,
    writable: true,
    configurable: true
  });
}

// Cleanup after each test
afterEach(() => {
  cleanup();
});
