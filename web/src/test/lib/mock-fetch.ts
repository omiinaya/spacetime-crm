/**
 * Mock `window.fetch` and return typed helpers.
 * Uses a response queue — push responses in order, each fetch() deques one.
 */

export interface FetchMock {
  /** Push the next response (will be JSON 200).  Call in fetch order. */
  push: (body: unknown) => void;
  /** Push an error response. */
  pushFail: (status: number, body?: string) => void;
  /** Assert exactly N fetch calls and return their (url, init) pairs. */
  calls: () => { url: string; init: RequestInit | undefined }[];
  /** Clear queue and recorded calls. */
  reset: () => void;
  /** Restore original fetch. */
  restore: () => void;
}

/** Install a mock that returns JSON 200 by default.  Returns control helpers. */
export function mockFetch(): FetchMock {
  const calls: { url: string; init: RequestInit | undefined }[] = [];
  const queue: (() => Response)[] = [];
  const original = window.fetch;

  const mock = vi.fn(
    (url: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
      calls.push({ url: String(url), init });
      const factory = queue.shift();
      if (factory) return Promise.resolve(factory());
      return Promise.resolve(
        new Response("{}", {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      );
    },
  );

  window.fetch = mock as typeof window.fetch;

  return {
    push(body: unknown) {
      queue.push(() => new Response(JSON.stringify(body), {
        status: 200,
        headers: { "content-type": "application/json" },
      }));
    },
    pushFail(status: number, body?: string) {
      queue.push(() => new Response(body ?? "{}", {
        status,
        statusText: "Error",
        headers: { "content-type": "application/json" },
      }));
    },
    calls: () => [...calls],
    reset: () => {
      calls.length = 0;
      queue.length = 0;
    },
    restore: () => {
      window.fetch = original;
    },
  };
}

/** Wait for all pending microtasks / state updates */
export function flushMicrotasks() {
  return new Promise((r) => setTimeout(r, 0));
}
