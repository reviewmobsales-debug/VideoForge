export interface Database {
  public: {
    Tables: {
      videos: { Row: VideoRecord };
      projects: { Row: ProjectRecord };
      template_usage: { Row: TemplateUsageRecord };
    };
  };
}

export interface VideoRecord {
  id: string;
  title: string;
  url: string;
  created_at: string;
  duration?: number;
  status?: "processing" | "ready" | "error";
}

export interface ProjectRecord {
  id: string;
  name: string;
  data: any;
  created_at: string;
  updated_at?: string;
}

export interface TemplateUsageRecord {
  id: string;
  template_id: string;
  video_id: string;
  applied_at: string;
  settings?: Record<string, any>;
}

export type Tables = Database["public"]["Tables"];
