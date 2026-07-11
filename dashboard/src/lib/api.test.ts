import { describe, it, expect, beforeEach, vi } from 'vitest';
import { getStoredToken, storeToken, clearToken } from './api';

describe('Token helpers', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  describe('getStoredToken', () => {
    it('returns null if token is not set', () => {
      expect(getStoredToken()).toBeNull();
    });

    it('returns the token if it is set in localStorage', () => {
      localStorage.setItem('algobounty_jwt', 'test-jwt-token');
      expect(getStoredToken()).toBe('test-jwt-token');
    });

    it('returns null if window is undefined', () => {
      const originalWindow = global.window;
      // @ts-ignore
      delete global.window;

      expect(getStoredToken()).toBeNull();

      global.window = originalWindow;
    });
  });

  describe('storeToken', () => {
    it('stores the token in localStorage', () => {
      storeToken('new-test-token');
      expect(localStorage.getItem('algobounty_jwt')).toBe('new-test-token');
    });
  });

  describe('clearToken', () => {
    it('removes the token from localStorage', () => {
      localStorage.setItem('algobounty_jwt', 'test-token-to-clear');
      clearToken();
      expect(localStorage.getItem('algobounty_jwt')).toBeNull();
    });
  });
});
