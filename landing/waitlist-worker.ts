/**
 * CausaGanha Waitlist Worker
 *
 * Deploy to Cloudflare Workers to collect waitlist emails.
 * Uses Cloudflare KV for storage.
 *
 * Setup:
 * 1. Create a KV namespace: wrangler kv:namespace create "WAITLIST"
 * 2. Update wrangler.toml with the namespace ID
 * 3. Deploy: wrangler deploy
 */

interface Env {
  WAITLIST: KVNamespace;
  ADMIN_TOKEN: string;
}

interface KVNamespace {
  get(key: string): Promise<string | null>;
  put(key: string, value: string): Promise<void>;
  list(options?: { cursor?: string | null }): Promise<{
    keys: { name: string }[];
    cursor?: string | null;
  }>;
}

interface SubscribeBody {
  email?: string;
  source?: string;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    // CORS headers
    const corsHeaders: Record<string, string> = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    };

    // Handle CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders });
    }

    const url = new URL(request.url);

    // POST /subscribe - Add email to waitlist
    if (request.method === 'POST' && url.pathname === '/subscribe') {
      try {
        const body: SubscribeBody = await request.json();
        const email = body.email?.toLowerCase().trim();

        // Validate email
        if (!email || !isValidEmail(email)) {
          return jsonResponse({ error: 'Invalid email' }, 400, corsHeaders);
        }

        // Check if already subscribed
        const existing = await env.WAITLIST.get(email);
        if (existing) {
          return jsonResponse({ message: 'Already subscribed', email }, 200, corsHeaders);
        }

        // Store subscription
        const subscription = {
          email,
          subscribedAt: new Date().toISOString(),
          source: body.source || 'landing',
          userAgent: request.headers.get('User-Agent'),
          country: (request as any).cf?.country || 'unknown',
        };

        await env.WAITLIST.put(email, JSON.stringify(subscription));

        // Increment counter
        const count = parseInt(await env.WAITLIST.get('__count__') || '0') + 1;
        await env.WAITLIST.put('__count__', count.toString());

        return jsonResponse({
          message: 'Subscribed successfully',
          email,
          position: count
        }, 201, corsHeaders);

      } catch {
        return jsonResponse({ error: 'Server error' }, 500, corsHeaders);
      }
    }

    // GET /stats - Get waitlist stats (protected)
    if (request.method === 'GET' && url.pathname === '/stats') {
      const authHeader = request.headers.get('Authorization');
      if (authHeader !== `Bearer ${env.ADMIN_TOKEN}`) {
        return jsonResponse({ error: 'Unauthorized' }, 401, corsHeaders);
      }

      const count = await env.WAITLIST.get('__count__') || '0';
      return jsonResponse({ count: parseInt(count) }, 200, corsHeaders);
    }

    // GET /export - Export all emails (protected)
    if (request.method === 'GET' && url.pathname === '/export') {
      const authHeader = request.headers.get('Authorization');
      if (authHeader !== `Bearer ${env.ADMIN_TOKEN}`) {
        return jsonResponse({ error: 'Unauthorized' }, 401, corsHeaders);
      }

      const emails: any[] = [];
      let cursor: string | null | undefined = null;

      do {
        const result = await env.WAITLIST.list({ cursor });
        for (const key of result.keys) {
          if (!key.name.startsWith('__')) {
            const data = await env.WAITLIST.get(key.name);
            if (data) {
              emails.push(JSON.parse(data));
            }
          }
        }
        cursor = result.cursor;
      } while (cursor);

      return jsonResponse({ emails, count: emails.length }, 200, corsHeaders);
    }

    return jsonResponse({ error: 'Not found' }, 404, corsHeaders);
  },
};

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function jsonResponse(data: Record<string, any>, status: number, headers: Record<string, string>): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  });
}
