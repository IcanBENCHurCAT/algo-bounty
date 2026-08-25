import {
  base64ToBytes,
  bytesToBase64,
  microAlgoToAlgo,
  algoToMicroAlgo,
} from '../algorand';

describe('Algorand helper utilities in algorand.ts', () => {
  describe('base64ToBytes', () => {
    it('correctly converts a valid base64 string to a Uint8Array', () => {
      // "SGVsbG8=" is base64 for "Hello"
      const b64 = 'SGVsbG8=';
      const expected = new Uint8Array([72, 101, 108, 108, 111]);
      const result = base64ToBytes(b64);

      expect(result).toBeInstanceOf(Uint8Array);
      expect(result).toEqual(expected);
    });

    it('returns an empty Uint8Array when given an empty base64 string', () => {
      const result = base64ToBytes('');
      expect(result).toBeInstanceOf(Uint8Array);
      expect(result.length).toBe(0);
    });

    it('correctly converts binary data bytes', () => {
      const rawBytes = new Uint8Array([0, 255, 128, 64, 32, 16]);
      const b64 = Buffer.from(rawBytes).toString('base64');
      const result = base64ToBytes(b64);

      expect(result).toEqual(rawBytes);
    });

    it('performs round-trip conversion with bytesToBase64', () => {
      const originalBytes = new Uint8Array([1, 2, 3, 4, 5, 200, 250]);
      const b64 = bytesToBase64(originalBytes);
      const reconstructedBytes = base64ToBytes(b64);

      expect(reconstructedBytes).toEqual(originalBytes);
    });
  });

  describe('bytesToBase64', () => {
    it('correctly converts a Uint8Array to a base64 string', () => {
      const bytes = new Uint8Array([72, 101, 108, 108, 111]);
      expect(bytesToBase64(bytes)).toBe('SGVsbG8=');
    });

    it('returns an empty string when given an empty Uint8Array', () => {
      expect(bytesToBase64(new Uint8Array([]))).toBe('');
    });
  });

  describe('microAlgoToAlgo', () => {
    it('converts microALGO to ALGO string correctly', () => {
      expect(microAlgoToAlgo(1_000_000)).toBe('1');
      expect(microAlgoToAlgo(1_500_000)).toBe('1.5');
      expect(microAlgoToAlgo(123_456_789)).toBe('123.456789');
      expect(microAlgoToAlgo(0)).toBe('0');
    });
  });

  describe('algoToMicroAlgo', () => {
    it('converts ALGO to microALGO correctly', () => {
      expect(algoToMicroAlgo(1)).toBe(1_000_000);
      expect(algoToMicroAlgo(1.5)).toBe(1_500_000);
      expect(algoToMicroAlgo(0)).toBe(0);
      expect(algoToMicroAlgo(0.000001)).toBe(1);
    });
  });
});
