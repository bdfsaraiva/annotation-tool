// Vitest-compatible setup (also works with Jest)
import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock axios globally so axios.create() returns a usable object
vi.mock('axios', () => {
  const mockInstance = {
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  };
  return {
    default: {
      create: vi.fn(() => mockInstance),
      post: vi.fn(),
    },
  };
});

const originalError = console.error;
console.error = (...args) => {
  const message = args[0];
  if (typeof message === 'string' && message.includes('ReactDOMTestUtils.act')) return;
  originalError(...args);
};

const originalWarn = console.warn;
console.warn = (...args) => {
  const message = args[0];
  if (typeof message === 'string' && message.includes('React Router Future Flag Warning')) return;
  originalWarn(...args);
};
