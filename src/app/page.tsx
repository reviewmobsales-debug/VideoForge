import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Layers, Wand2, Zap, Music, Video, ArrowRight, GitBranch } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Navbar */}
      <header className="border-b border-border bg-card/50 backdrop-blur sticky top-0 z-50">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <Layers className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold tracking-tight">VideoForge</span>
          </div>
          <nav className="flex items-center gap-6 text-sm">
            <Link href="/templates" className="text-muted-foreground hover:text-foreground transition-colors">Templates</Link>
            <Link href="/editor" className="text-muted-foreground hover:text-foreground transition-colors">Editor</Link>
            <a href="https://github.com/reviewmob/videoforge" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1">
              <GitBranch className="h-4 w-4" /> GitHub
            </a>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="flex-1 flex items-center justify-center px-6 py-20">
        <div className="max-w-3xl text-center space-y-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-border bg-muted px-4 py-1.5 text-xs font-medium text-muted-foreground">
            <Zap className="h-3 w-3" /> Made by ReviewMob.ai
          </div>
          <h1 className="text-5xl sm:text-7xl font-bold tracking-tight leading-[1.1]">
            Auto-Edit Videos
            <br />
            <span className="text-primary">With Beat Sync</span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-xl mx-auto leading-relaxed">
            Upload your clips, pick a TikTok or brainrot template, and let VideoForge auto-detect beats, sync cuts, add effects, and export — all in your browser.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <a href="/templates">
            <Button size="lg" className="gap-2 cursor-pointer">
              <Wand2 className="h-4 w-4" /> Pick a Template
            </Button>
          </a>
          <a href="/editor">
            <Button variant="outline" size="lg" className="gap-2 cursor-pointer">
              <Video className="h-4 w-4" /> Open Editor
            </Button>
          </a>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="border-t border-border bg-muted/30">
        <div className="mx-auto max-w-7xl px-6 py-20">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <FeatureCard icon={<Music className="h-6 w-6" />} title="Beat Detection" desc="Auto-detect BPM and drop markers from audio. Cut precisely on every beat." />
            <FeatureCard icon={<Layers className="h-6 w-6" />} title="TikTok Templates" desc="Ready-made templates: 3D zoom, GRWM, storytime, ASMR, transitions." />
            <FeatureCard icon={<Zap className="h-6 w-6" />} title="Brainrot Effects" desc="Sigma grindset, gyatt detectors, RGB glitch, zoom shake — pure chaos." />
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border py-16 text-center px-6">
        <h2 className="text-2xl font-bold mb-4">Start editing now</h2>
        <p className="text-muted-foreground mb-6">No signup. Works in the browser. Powered by Web Audio + Canvas + FFmpeg.wasm.</p>
          <a href="/editor">
            <Button size="lg" className="gap-2 cursor-pointer">
              Launch Editor <ArrowRight className="h-4 w-4" />
            </Button>
          </a>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-6 text-center text-xs text-muted-foreground">
        VideoForge by ReviewMob.ai · Next.js 16 + Tailwind v4 + shadcn/ui
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, desc }: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <div className="rounded-xl border border-border bg-card p-6 space-y-3 transition hover:shadow-md">
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
        {icon}
      </div>
      <h3 className="font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground leading-relaxed">{desc}</p>
    </div>
  );
}
