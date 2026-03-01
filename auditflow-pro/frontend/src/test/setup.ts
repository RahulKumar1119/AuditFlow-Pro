// Test setup file for vitest
import { expect, afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock ResizeObserver for jsdom
global.ResizeObserver = class ResizeObserver {
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
if (!global.crypto) {
  global.crypto = {} as Crypto;
}

if (!global.crypto.subtle) {
  global.crypto.subtle = {
    digest: async (algorithm: string, data: BufferSource) => {
      // Handle different input types
      let buffer: ArrayBuffer;
      
      if (data instanceof ArrayBuffer) {
        buffer = data;
      } else if (ArrayBuffer.isView(data)) {
        buffer = data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength);
      } else {
        // Fallback for other types
        buffer = new ArrayBuffer(32);
      }
      
      // Return a fake hash
      const hashBuffer = new ArrayBuffer(32);
      const view = new Uint8Array(hashBuffer);
      for (let i = 0; i < 32; i++) {
        view[i] = i;
      }
      return hashBuffer;
    },
  } as SubtleCrypto;
}

// Cleanup after each test
afterEach(() => {
  cleanup();
});
