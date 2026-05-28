"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  BookOpenCheck,
  ExternalLink,
  ArrowLeft,
  RefreshCw,
  Target,
  Clock,
  Layers3,
  CheckCircle2,
  Sparkles,
  Loader2,
  AlertCircle,
} from "lucide-react";
import clsx from "clsx";
import { twMerge } from "tailwind-merge";
import { AssessmentResults, LearningPathAgentOutput } from "../../types/assessment";

function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs));
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:3001/api";
const AI_BASE = process.env.NEXT_PUBLIC_AI_BASE_URL || "http://localhost:8000/api";

export default function LearningPathPage() {
  const router = useRouter();
  const [learningPath, setLearningPath] = useState<LearningPathAgentOutput | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [aiStatus, setAiStatus] = useState<"generating" | "done" | "fallback">("generating");

  useEffect(() => {
    const stored = sessionStorage.getItem("assessmentResults");
    if (!stored) { router.replace("/"); return; }

    const results: AssessmentResults = JSON.parse(stored);

    // If learning path already in session, use it
    const existing =
      results.learningPath ||
      (!Array.isArray(results.recommendations)
        ? (results.recommendations as any)?.learningPath
        : undefined);

    if (existing) {
      setLearningPath(existing);
      setAiStatus(existing.aiGenerated ? "done" : "fallback");
      setLoading(false);
      return;
    }

    // Build skill gap payload from assessment results
    const skillGapAnalysis =
      results.skillGapAnalysis ||
      (!Array.isArray(results.recommendations)
        ? (results.recommendations as any)?.skillGapAnalysis
        : undefined);

    if (!skillGapAnalysis) {
      setError("No skill gap data found. Please retake the assessment.");
      setLoading(false);
      return;
    }

    // Call the AI agent
    callLearningPathAgent(skillGapAnalysis);
  }, [router]);

  async function callLearningPathAgent(skillGapData: any) {
    setLoading(true);
    setAiStatus("generating");
    try {
      const payload = {
        assessmentDomain: skillGapData.assessmentDomain || "general",
        readinessScore: skillGapData.readinessScore || 0,
        missingSkills: skillGapData.missingSkills || [],
        roleGapSummary: skillGapData.roleGapSummary || [],
        overallGapPercentage: skillGapData.overallGapPercentage || 0,
      };

      const response = await fetch(`${AI_BASE}/learning-path-agent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error(`AI service returned ${response.status}`);

      const data: LearningPathAgentOutput = await response.json();
      setLearningPath(data);
      setAiStatus(data.aiGenerated ? "done" : "fallback");

      // Save to session
      const stored = sessionStorage.getItem("assessmentResults");
      if (stored) {
        const results = JSON.parse(stored);
        results.learningPath = data;
        sessionStorage.setItem("assessmentResults", JSON.stringify(results));
      }
    } catch (err: any) {
      setError(`Could not reach the AI service. Make sure the ai-service is running on port 8000.\n\nError: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  if (loading) return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 bg-slate-50">
      <div className="flex items-center justify-center w-20 h-20 rounded-full bg-emerald-50 border border-emerald-200">
        <Loader2 className="w-10 h-10 text-emerald-600 animate-spin" />
      </div>
      <div className="text-center">
        <p className="text-xl font-bold text-slate-900">AI is building your learning path...</p>
        <p className="text-slate-500 mt-2 flex items-center justify-center gap-2">
          <Sparkles className="w-4 h-4 text-emerald-500" />
          Ollama is analyzing your skill gaps and generating personalized modules
        </p>
      </div>
    </div>
  );

  if (error) return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-slate-50 px-4">
      <AlertCircle className="w-12 h-12 text-rose-500" />
      <p className="text-lg font-bold text-slate-900 text-center">Something went wrong</p>
      <pre className="text-sm text-slate-600 bg-white border border-slate-200 rounded-xl p-4 max-w-xl whitespace-pre-wrap">{error}</pre>
      <button onClick={() => router.push("/results")} className="px-6 py-3 bg-slate-900 text-white rounded-xl font-bold">
        Back to Results
      </button>
    </div>
  );

  if (!learningPath) return null;

  return (
    <div className="min-h-[calc(100vh-64px)] bg-slate-50 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">

        {/* ── HEADER ─────────────────────────────────────────────────── */}
        <div className="bg-white rounded-3xl p-8 sm:p-12 text-center shadow-sm border border-slate-200 relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-emerald-400 to-teal-600" />

          {/* AI badge */}
          {aiStatus === "done" && (
            <div className="inline-flex items-center gap-2 bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-bold px-3 py-1.5 rounded-full mb-4">
              <Sparkles className="w-3.5 h-3.5" /> AI-Generated by Ollama
            </div>
          )}
          {aiStatus === "fallback" && (
            <div className="inline-flex items-center gap-2 bg-amber-50 border border-amber-200 text-amber-700 text-xs font-bold px-3 py-1.5 rounded-full mb-4">
              <AlertCircle className="w-3.5 h-3.5" /> Smart fallback (Ollama unavailable)
            </div>
          )}

          <div className="inline-flex items-center justify-center p-4 bg-emerald-50 rounded-full mb-6">
            <BookOpenCheck className="w-12 h-12 text-emerald-600" />
          </div>
          <h1 className="text-3xl sm:text-5xl font-extrabold text-slate-900 mb-4 tracking-tight">
            Your Learning Path
          </h1>
          <p className="text-slate-600 text-lg max-w-2xl mx-auto">{learningPath.summary}</p>

          {/* Stats */}
          <div className="mt-8 grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { num: learningPath.totalModules, label: "Modules", color: "emerald" },
              { num: learningPath.estimatedWeeks, label: "Weeks", color: "teal" },
              { num: `${learningPath.estimatedTotalHours}h`, label: "Study Time", color: "blue" },
              { num: `${learningPath.readinessScore}%`, label: "Readiness", color: "slate" },
            ].map(({ num, label, color }) => (
              <div key={label} className={`rounded-2xl bg-${color}-50 border border-${color}-100 p-4`}>
                <div className={`text-3xl font-extrabold text-${color}-700`}>{num}</div>
                <div className={`text-xs font-bold uppercase text-${color}-600 mt-1`}>{label}</div>
              </div>
            ))}
          </div>

          <div className="mt-6 flex flex-wrap justify-center gap-3 text-sm">
            <span className="rounded-full bg-slate-100 px-4 py-1.5 font-semibold text-slate-700">
              Target: {learningPath.targetRole}
            </span>
            <span className="rounded-full bg-slate-100 px-4 py-1.5 font-semibold text-slate-700 capitalize">
              {(learningPath.assessmentDomain || "").replace(/_/g, " ")}
            </span>
          </div>
        </div>

        {/* ── MODULES ─────────────────────────────────────────────────── */}
        <div className="space-y-5">
          {learningPath.modules.map((module: any) => (
            <div key={`${module.week}-${module.skill}`}
              className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden hover:border-emerald-300 transition-colors">

              {/* Module header */}
              <div className="flex items-center gap-4 px-6 py-4 border-b border-slate-100 bg-slate-50">
                <div className="flex items-center justify-center w-10 h-10 rounded-full bg-emerald-100 text-emerald-700 font-extrabold text-sm shrink-0">
                  W{module.week}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-extrabold text-slate-900 capitalize">{module.skill}</h3>
                  <p className="text-sm text-slate-500 flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    {module.durationHours} hours · {module.currentScore}% → {module.targetScore}%
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {module.aiGenerated && (
                    <span className="rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 px-2 py-0.5 text-xs font-bold flex items-center gap-1">
                      <Sparkles className="w-3 h-3" /> AI
                    </span>
                  )}
                  <span className={cn(
                    "rounded-full px-3 py-1 text-xs font-bold uppercase",
                    module.priority === "critical" ? "bg-rose-100 text-rose-700"
                      : module.priority === "high" ? "bg-amber-100 text-amber-700"
                      : "bg-blue-100 text-blue-700"
                  )}>
                    {module.priority}
                  </span>
                </div>
              </div>

              {/* Module body */}
              <div className="px-6 py-5 space-y-4">
                {/* Resource link */}
                <a href={module.url} target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-xl bg-emerald-50 border border-emerald-200 px-4 py-2.5 text-sm font-bold text-emerald-800 hover:bg-emerald-100 transition-colors">
                  <BookOpenCheck className="w-4 h-4 shrink-0" />
                  {module.provider}: {module.title}
                  <ExternalLink className="w-3.5 h-3.5 shrink-0 ml-auto" />
                </a>

                {/* Topics */}
                <div className="flex flex-wrap gap-2">
                  <span className="rounded-full bg-teal-100 text-teal-800 px-3 py-1 text-xs font-bold">{module.type}</span>
                  <span className="rounded-full bg-slate-100 text-slate-600 px-3 py-1 text-xs font-semibold">{module.level}</span>
                  {module.topics?.map((t: string) => (
                    <span key={t} className="rounded-full bg-white border border-slate-200 px-3 py-1 text-xs font-semibold text-slate-700">{t}</span>
                  ))}
                </div>

                {/* Why important (AI only) */}
                {module.whyImportant && (
                  <div className="rounded-xl bg-indigo-50 border border-indigo-100 p-4">
                    <p className="text-sm text-slate-800">
                      <span className="font-bold text-indigo-700 flex items-center gap-1 mb-1">
                        <Sparkles className="w-4 h-4" /> Why this matters
                      </span>
                      {module.whyImportant}
                    </p>
                  </div>
                )}

                {/* Weekly goal (AI only) */}
                {module.weeklyGoal && (
                  <div className="rounded-xl bg-purple-50 border border-purple-100 p-4">
                    <p className="text-sm text-slate-800">
                      <span className="font-bold text-purple-700 flex items-center gap-1 mb-1">
                        🎯 Weekly Goal
                      </span>
                      {module.weeklyGoal}
                    </p>
                  </div>
                )}

                {/* Practice task */}
                <div className="rounded-xl bg-amber-50 border border-amber-100 p-4">
                  <p className="text-sm text-slate-800">
                    <span className="font-bold text-amber-700 flex items-center gap-1 mb-1">
                      <Target className="w-4 h-4" /> Practice Task
                    </span>
                    {module.practiceTask}
                  </p>
                </div>

                {/* Checkpoint */}
                <div className="rounded-xl bg-blue-50 border border-blue-100 p-4">
                  <p className="text-sm text-slate-800">
                    <span className="font-bold text-blue-700 flex items-center gap-1 mb-1">
                      <CheckCircle2 className="w-4 h-4" /> Checkpoint
                    </span>
                    {module.checkpoint}
                  </p>
                </div>

                {/* Source roles */}
                {module.sourceRoles?.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    <span className="text-xs font-bold uppercase text-slate-400 flex items-center gap-1">
                      <Layers3 className="w-3.5 h-3.5" /> Needed for:
                    </span>
                    {module.sourceRoles.slice(0, 3).map((role: string) => (
                      <span key={role} className="rounded-full bg-indigo-50 text-indigo-700 border border-indigo-100 px-3 py-0.5 text-xs font-semibold">
                        {role}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* ── FOOTER ──────────────────────────────────────────────────── */}
        <div className="pt-4 flex flex-col sm:flex-row justify-center gap-4">
          <button onClick={() => router.push("/results")}
            className="px-8 py-4 bg-slate-200 hover:bg-slate-300 text-slate-900 font-bold rounded-xl transition-all flex items-center justify-center gap-2">
            <ArrowLeft className="w-5 h-5" /> Back to Results
          </button>
          <button onClick={() => { sessionStorage.clear(); router.push("/assess?retake=1"); }}
            className="px-8 py-4 bg-slate-900 hover:bg-slate-800 text-white font-bold rounded-xl transition-all shadow-md flex items-center justify-center gap-2">
            <RefreshCw className="w-5 h-5" /> Retake Assessment
          </button>
        </div>
      </div>
    </div>
  );
}
