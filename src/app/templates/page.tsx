// VideoForge — TikTok + Brainrot Template Gallery
"use client";

import { templates } from "@/lib/templates";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Clock, Layers, Sparkles, Wand2 } from "lucide-react";
import Link from "next/link";

export default function TemplatesPage() {
  const tiktokTemplates = templates.filter((t) => t.category === "tiktok");
  const brainrotTemplates = templates.filter((t) => t.category === "brainrot");

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <Layers className="h-6 w-6 text-primary" />
            <h1 className="text-xl font-bold tracking-tight">VideoForge Templates</h1>
          </div>
          <nav className="flex items-center gap-4 text-sm text-muted-foreground">
            <Link href="/" className="hover:text-foreground transition-colors">Home</Link>
            <Link href="/editor" className="hover:text-foreground transition-colors">Editor</Link>
            <Link href="/templates" className="text-foreground font-medium">Templates</Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        {/* Hero */}
        <div className="mb-8">
          <h2 className="text-3xl font-bold tracking-tight">Choose a Template</h2>
          <p className="mt-2 text-muted-foreground max-w-xl">
            Pick a TikTok-style or brainrot template. Upload your video, let the beat detection sync the cuts, and export in seconds.
          </p>
        </div>

        <Tabs defaultValue="tiktok" className="w-full">
          <TabsList className="mb-6">
            <TabsTrigger value="tiktok" className="gap-1.5">
              <Sparkles className="h-4 w-4" /> TikTok Style
            </TabsTrigger>
            <TabsTrigger value="brainrot" className="gap-1.5">
              <Wand2 className="h-4 w-4" /> Brainrot
            </TabsTrigger>
          </TabsList>

          <TabsContent value="tiktok">
            <TemplateGrid templates={tiktokTemplates} />
          </TabsContent>
          <TabsContent value="brainrot">
            <TemplateGrid templates={brainrotTemplates} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}

function TemplateGrid({ templates }: { templates: typeof import("@/lib/templates").templates }) {
  return (
    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {templates.map((t) => (
        <Card key={t.id} className="group overflow-hidden border-border bg-card transition hover:shadow-md">
          <div className="relative aspect-[9/16] overflow-hidden bg-muted">
            {/* Placeholder thumbnail generated with CSS patterns */}
            <div
              className="h-full w-full"
              style={{
                background:
                  t.category === "brainrot"
                    ? `repeating-linear-gradient(45deg, #111, #111 10px, #222 10px, #222 20px)`
                    : `linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)`,
              }}
            />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-4xl font-black text-white/20 uppercase tracking-widest">
                {t.name.split(" ")[0]}
              </span>
            </div>
            <div className="absolute bottom-0 left-0 right-0 bg-black/60 p-3 opacity-0 transition-opacity group-hover:opacity-100">
              <Link href={`/editor?template=${t.id}`}>
                <Button size="sm" className="w-full gap-1">
                  <Wand2 className="h-3.5 w-3.5" /> Use Template
                </Button>
              </Link>
            </div>
          </div>
          <CardHeader className="pb-2">
            <h3 className="font-semibold">{t.name}</h3>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground line-clamp-2">{t.description}</p>
            <div className="flex flex-wrap gap-1.5">
              {t.tags.slice(0, 3).map((tag) => (
                <Badge key={tag} variant="secondary" className="text-[10px]">
                  {tag}
                </Badge>
              ))}
            </div>
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              <Clock className="h-3 w-3" />
              {t.duration}s · {t.aspectRatio}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
