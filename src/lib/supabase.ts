// Supabase-compatible client using local JSON DB
import { db } from "./db-api";

export type VideoRecord = { id: string; title: string; url: string; created_at: string };
export type ProjectRecord = { id: string; name: string; data: any; created_at: string };

export const supabase = {
  from(table: string) {
    return {
      select: async () => ({ data: (await db.get(table))[table] || [], error: null }),
      insert: async (records: any[]) => {
        const all = await db.get(table);
        all[table] = [...(all[table] || []), ...records];
        await db.set(table, all);
        return { data: records, error: null };
      },
      delete: async () => ({ data: null, error: null }),
      eq: () => ({
        single: async () => ({ data: null, error: null }),
      }),
    };
  },
  auth: {
    getSession: async () => ({ data: { session: null }, error: null }),
    signInWithPassword: async () => ({ data: null, error: null }),
    signUp: async () => ({ data: null, error: null }),
  },
};
