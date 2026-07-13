import { getStoredToken, storeToken, clearToken } from '../api';

const JWT_KEY = 'algobounty_jwt';

describe('Token helpers in api.ts', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    jest.restoreAllMocks();
  });

  describe('getStoredToken', () => {
    it('returns null if no token is stored', () => {
      expect(getStoredToken()).toBeNull();
    });

    it('returns the stored token', () => {
      localStorage.setItem(JWT_KEY, 'test-token');
      expect(getStoredToken()).toBe('test-token');
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
    it('should save the provided token to localStorage when window is defined', () => {
      storeToken('test-jwt-token-123');
      expect(localStorage.getItem(JWT_KEY)).toBe('test-jwt-token-123');
    });

    it('should safely do nothing if window is undefined', () => {
      const originalWindow = global.window;
      const setItemSpy = jest.spyOn(global.localStorage, 'setItem');

      // @ts-ignore
      delete global.window;

      storeToken('another-token');

      expect(setItemSpy).not.toHaveBeenCalled();

      // Restore window
      global.window = originalWindow;
      setItemSpy.mockRestore();
    });
  });

  describe('clearToken', () => {
    it('removes the token from localStorage', () => {
      localStorage.setItem(JWT_KEY, 'token-to-be-cleared');
      expect(localStorage.getItem(JWT_KEY)).toBe('token-to-be-cleared');

      clearToken();

      expect(localStorage.getItem(JWT_KEY)).toBeNull();
    });

    it('does nothing if window is undefined', () => {
      const originalWindow = global.window;
      const removeItemSpy = jest.spyOn(global.localStorage, 'removeItem');

      // @ts-ignore
      delete global.window;

      clearToken();

      expect(removeItemSpy).not.toHaveBeenCalled();

      global.window = originalWindow;
      removeItemSpy.mockRestore();
    });
  });
});
