"use client";

import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ArrowUp, PlusCircle, Zap, PanelLeftClose, PanelLeftOpen,
  Play, Terminal, Search, PenTool, Activity, Trash2,
  MessageSquare, Sparkles, Cpu, ChevronRight, User, Bot, Command
} from "lucide-react";

// --- VERBESSERTE MARKDOWN FORMATIERUNG ---
const CustomMarkdown = {
  p: ({ ...props }) => <p className="mb-4 leading-relaxed text-zinc-300/95 last:mb-0" {...props} />,
  h1: ({ ...props }) => <h1 className="text-2xl font-bold text-white mb-4 mt-6 border-b border-white/10 pb-2" {...props} />,
  h2: ({ ...props }) => <h2 className="text-xl font-semibold text-zinc-100 mb-3 mt-5 flex items-center gap-2" {...props} />,
  h3: ({ ...props }) => <h3 className="text-lg font-medium text-zinc-200 mb-2 mt-4" {...props} />,
  ul: ({ ...props }) => <ul className="list-disc pl-6 mb-4 space-y-2 text-zinc-300" {...props} />,
  ol: ({ ...props }) => <ol className="list-decimal pl-6 mb-4 space-y-2 text-zinc-300" {...props} />,
  li: ({ ...props }) => <li className="marker:text-blue-400" {...props} />,
  strong: ({ ...props }) => <strong className="font-bold text-blue-400/90" {...props} />,
  blockquote: ({ ...props }) => (
    <blockquote className="border-l-4 border-blue-500/50 bg-blue-500/5 pl-4 py-2 italic my-4 rounded-r-lg" {...props} />
  ),
  code: ({ inline, ...props }: any) =>
    inline ? (
      <code className="bg-blue-500/20 text-blue-300 px-1.5 py-0.5 rounded text-[13px] font-mono border border-blue-500/20" {...props} />
    ) : (
      <div className="relative my-6 group">
        <div className="absolute -top-3 left-4 px-2 py-0.5 bg-[#0f0f0f] border border-white/10 rounded text-[10px] font-mono text-zinc-500 uppercase tracking-widest">Code</div>
        <code className="block bg-black/60 border border-white/10 text-emerald-400/90 p-5 rounded-xl text-[13px] font-mono overflow-x-auto whitespace-pre shadow-2xl" {...props} />
      </div>
    ),
};

export default function CleanChatApp() {
  const [viewMode, setViewMode] = useState<'chat' | 'challenge'>('chat');
  const [sessions, setSessions] = useState<{ id: string, title: string, messages: any[] }[]>([
    { id: "default", title: "Neue Unterhaltung", messages: [] }
  ]);
  const [currentSessionId, setCurrentSessionId] = useState("default");
  const [input, setInput] = useState("");
  const [useRag, setUseRag] = useState(true);
  const [selectedChallenge, setSelectedChallenge] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Challenge 1 form fields
  const [c1Thema, setC1Thema] = useState("Wasserstoff");
  const [c1Kapital, setC1Kapital] = useState("2000");
  const [c1Risiko, setC1Risiko] = useState("Low Risk");
  const [c1Horizont, setC1Horizont] = useState("10 Jahre");

  // Challenge States
  //  Each agent gets an entry: name (display), taskName, logs (raw Rich panel strings), completed flag
  type AgentEntry = { name: string; taskName?: string; logs: string[]; completed: boolean };
  const [challengeStatus, setChallengeStatus] = useState<string[]>([]);
  const [agentList, setAgentList] = useState<AgentEntry[]>([]);
  const [finalResult, setFinalResult] = useState<string | null>(null);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const isAutoScrollRef = useRef(true);

  const activeSession = sessions.find(s => s.id === currentSessionId) || sessions[0];

  const formatResponse = (text: string) => text.replaceAll('\\n', '\n');

  const handleSelectChallenge = (id: number) => {
    if (selectedChallenge !== id) {
      setChallengeStatus([]);
      setAgentList([]);
      setFinalResult(null);
    }
    setSelectedChallenge(id);
    setViewMode('challenge');
  };

  const handleScroll = () => {
    if (!scrollContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    isAutoScrollRef.current = scrollHeight - scrollTop - clientHeight < 100;
  };

  useEffect(() => {
    if (scrollContainerRef.current && isAutoScrollRef.current) {
      scrollContainerRef.current.scrollTo({
        top: scrollContainerRef.current.scrollHeight,
        behavior: isLoading ? "auto" : "smooth",
      });
    }
  }, [sessions, isLoading, viewMode]);

  const handleNewChat = () => {
    const newId = Date.now().toString();
    setSessions(prev => [{ id: newId, title: "Neue Unterhaltung", messages: [] }, ...prev]);
    setCurrentSessionId(newId);
    setViewMode('chat');
    isAutoScrollRef.current = true;
  };

  const handleDeleteChat = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setSessions(prev => {
      const filtered = prev.filter(s => s.id !== id);
      return filtered.length ? filtered : [{ id: "default", title: "Neue Unterhaltung", messages: [] }];
    });
    if (currentSessionId === id) setCurrentSessionId("default");
  };

  const handleChatSubmit = async () => {
    if (!input.trim() || isLoading) return;
    const userQuery = input;
    setInput("");
    setIsLoading(true);
    isAutoScrollRef.current = true;

    setSessions(prev => prev.map(s =>
      s.id === currentSessionId
        ? {
          ...s,
          messages: [...s.messages, { role: "user", content: userQuery }, { role: "assistant", content: "" }],
          title: s.messages.length === 0 ? (userQuery.substring(0, 24) + "...") : s.title
        }
        : s
    ));

    try {
      const response = await fetch("http://127.0.0.1:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: userQuery, use_rag: useRag, stream: true }),
      });
      if (!response.body) return;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let acc = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        acc += decoder.decode(value, { stream: true });
        const cleanedAcc = formatResponse(acc);
        setSessions(prev => prev.map(s => {
          if (s.id === currentSessionId) {
            const msgs = [...s.messages];
            msgs[msgs.length - 1].content = cleanedAcc;
            return { ...s, messages: msgs };
          }
          return s;
        }));
      }
    } catch (e) { console.error(e); } finally { setIsLoading(false); }
  };

  // ─── CrewAI 1.x Rich-panel log parsing ────────────────────────────────────
  // Each panel arrives as ONE string with embedded \n, e.g.:
  //   "╭─── Agent Started ───╮\n│  Agent: Analyst  │\n│  Task: ...  │\n╰──────╯"
  // We match "│  Agent: <name>  │" with a lazy pattern that stops before trailing
  // spaces + closing box char on the same line.
  const extractAgentDisplayName = (text: string): string | null => {
    const m = text.match(/│\s+Agent:\s+(.+?)\s+│/m);
    if (m) return m[1].trim();
    // plain fallback (no box chars)
    const m2 = text.match(/(?:^|\n)Agent:\s+(.+?)(?:\s*$|\s+│)/m);
    if (m2) return m2[1].trim();
    return null;
  };

  const extractTaskDisplayName = (text: string): string | null => {
    // "│  Task: <desc>  │" or "│  Name: <desc>  │" (from Task Started panel)
    const m = text.match(/│\s+(?:Task|Name):\s+(.+?)\s+│/m);
    if (m) return m[1].trim();
    const m2 = text.match(/(?:^|\n)(?:Task|Name):\s+(.+?)(?:\s*$|\s+│)/m);
    if (m2) return m2[1].trim();
    return null;
  };

  const runChallenge = async () => {
    if (!selectedChallenge) return;
    setIsLoading(true);
    setChallengeStatus([]);
    setAgentList([]);
    setFinalResult(null);

    const body = { THEMA: c1Thema, KAPITAL_EUR: parseFloat(c1Kapital) || 2000, RISIKO_PROFIL: c1Risiko, ANLAGE_HORIZONT: c1Horizont };

    try {
      const resp = await fetch(`http://127.0.0.1:8000/agents/challenge1`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!resp.body) return;
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      // Closure index: which agent in agentList is currently active (-1 = none)
      let currentAgentIndex = -1;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() || "";
        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const obj = JSON.parse(line);
            // Keep actual \n chars; only unescape literal backslash-n sequences
            const content: string = (obj.message || obj.text || obj.answer || "").replaceAll('\\n', '\n');

            if (obj.type === 'status') {
              // First status line = starting message
              setChallengeStatus(p => [...p, content]);

            } else if (obj.type === 'log') {
              // ── "🤖 Agent Started" panel: create a new agent card ──────────
              if (/Agent Started/.test(content)) {
                const agentName = extractAgentDisplayName(content) || `Agent ${currentAgentIndex + 2}`;
                const taskName = extractTaskDisplayName(content) || undefined;
                currentAgentIndex++;
                setAgentList(prev => [...prev, { name: agentName, taskName, logs: [content], completed: false }]);

              // ── "✅ Agent Final Answer" panel: mark agent done ─────────────
              } else if (/Agent Final Answer/.test(content)) {
                if (currentAgentIndex >= 0) {
                  const idx = currentAgentIndex;
                  setAgentList(prev => {
                    if (idx >= prev.length) return prev;
                    const next = [...prev];
                    next[idx] = { ...next[idx], logs: [...next[idx].logs, content], completed: true };
                    return next;
                  });
                } else {
                  setChallengeStatus(p => [...p, content]);
                }

              // ── "📋 Task Started" / "📋 Task Completion" panels ───────────
              } else if (/Task Started|Task Completion|Task Failure/.test(content)) {
                if (currentAgentIndex >= 0) {
                  const idx = currentAgentIndex;
                  const newTask = extractTaskDisplayName(content);
                  setAgentList(prev => {
                    if (idx >= prev.length) return prev;
                    const next = [...prev];
                    next[idx] = {
                      ...next[idx],
                      taskName: newTask || next[idx].taskName,
                      logs: [...next[idx].logs, content],
                    };
                    return next;
                  });
                } else {
                  setChallengeStatus(p => [...p, content]);
                }

              // ── Any other log: route to active agent or system log ────────
              } else if (currentAgentIndex >= 0) {
                const idx = currentAgentIndex;
                setAgentList(prev => {
                  if (idx >= prev.length) return prev;
                  const next = [...prev];
                  next[idx] = { ...next[idx], logs: [...next[idx].logs, content] };
                  return next;
                });
              } else {
                setChallengeStatus(p => [...p, content]);
              }

            } else if (obj.type === 'result') {
              setFinalResult(content);
              setChallengeStatus(p => [...p, '✅ Workflow completed successfully.']);
            } else if (obj.type === 'error') {
              setChallengeStatus(p => [...p, `❌ Error: ${content}`]);
            }
          } catch (_) { }
        }
      }
    } catch (_) {
      setChallengeStatus(p => [...p, '⚠️ Connection error. Is the backend running?']);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen w-full relative overflow-hidden bg-[#050505] text-zinc-200 font-sans">
      {/* Dynamic Background */}
      <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] bg-blue-600/10 rounded-full blur-[140px] animate-pulse pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[60%] h-[60%] bg-emerald-600/10 rounded-full blur-[140px] animate-pulse pointer-events-none" style={{ animationDelay: '2s' }} />

      {/* SIDEBAR */}
      <aside className={`z-50 flex flex-col transition-all duration-500 ease-[cubic-bezier(0.2,0.8,0.2,1)] border-r border-white/5 bg-black/20 backdrop-blur-xl ${isSidebarOpen ? 'w-72' : 'w-0 overflow-hidden'}`}>
        <div className="w-72 p-6 flex flex-col h-full shrink-0">
          <button onClick={handleNewChat} className="group flex items-center justify-center gap-2 w-full py-4 rounded-2xl bg-white text-black font-black hover:bg-zinc-200 transition-all shadow-[0_0_30px_rgba(255,255,255,0.1)] active:scale-95 mb-10">
            <PlusCircle size={18} strokeWidth={3} /> NEW SESSION
          </button>

          <div className="flex-1 overflow-y-auto hide-scrollbar space-y-8">
            <div>
              <label className="text-[10px] uppercase tracking-[0.3em] text-zinc-500 font-bold px-2 mb-4 block">History</label>
              <div className="space-y-1">
                {sessions.map((s) => (
                  <button key={s.id} onClick={() => { setViewMode('chat'); setCurrentSessionId(s.id); isAutoScrollRef.current = true; }} className={`group flex items-center justify-between w-full px-3 py-3 rounded-xl transition-all ${currentSessionId === s.id && viewMode === 'chat' ? 'bg-white/10 text-white shadow-inner' : 'text-zinc-500 hover:bg-white/5 hover:text-zinc-300'}`}>
                    <div className="flex items-center gap-3 truncate">
                      <MessageSquare size={16} className={currentSessionId === s.id ? "text-blue-400" : "text-zinc-600"} />
                      <span className="truncate text-xs font-semibold">{s.title}</span>
                    </div>
                    <Trash2 size={14} onClick={(e) => handleDeleteChat(e, s.id)} className="opacity-0 group-hover:opacity-100 hover:text-red-400 transition-all" />
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-[10px] uppercase tracking-[0.3em] text-zinc-500 font-bold px-2 mb-4 block">Agent Challenges</label>
              <div className="space-y-1">
                <button onClick={() => handleSelectChallenge(1)} className={`flex items-center gap-3 w-full px-3 py-3 rounded-xl transition-all ${viewMode === 'challenge' && selectedChallenge === 1 ? 'bg-blue-500/20 text-blue-400 border border-blue-500/20' : 'text-zinc-500 hover:bg-white/5'}`}>
                  <Cpu size={16} />
                  <div className="flex flex-col items-start">
                    <span className="text-xs font-semibold uppercase tracking-wider">Challenge 01</span>
                    <span className="text-[9px] text-zinc-600 font-mono">Investment Audit</span>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* MAIN */}
      <main className="flex-1 flex flex-col relative min-w-0 overflow-hidden bg-black/40 backdrop-blur-sm">
        <header className="h-20 flex items-center px-8 border-b border-white/5 z-30 justify-between">
          <div className="flex items-center gap-6">
            <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="p-2.5 hover:bg-white/5 rounded-xl text-zinc-400 transition-all border border-transparent hover:border-white/10">
              {isSidebarOpen ? <PanelLeftClose size={20} /> : <PanelLeftOpen size={20} />}
            </button>
            <div className="h-6 w-px bg-white/10" />
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-[10px] font-black tracking-[0.4em] text-zinc-500 uppercase">
                  {viewMode === 'chat' ? 'LLM Chat Mode' : 'Agent Challenge Environment'}
                </span>
              </div>
              <span className="text-sm font-bold text-white tracking-tight">{viewMode === 'chat' ? activeSession.title : `Agent Challenge 0${selectedChallenge}`}</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden md:flex flex-col items-end mr-4">
              <span className="text-[9px] text-zinc-500 font-bold uppercase tracking-widest">System Status</span>
              <span className="text-[11px] text-emerald-400 font-mono">Running</span>
            </div>
            <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 text-zinc-400">
              <Command size={18} />
            </div>
          </div>
        </header>

        {viewMode === 'chat' ? (
          <div className="flex-1 flex flex-col overflow-hidden relative">
            <div ref={scrollContainerRef} onScroll={handleScroll} className="flex-1 overflow-y-auto px-6 py-10 hide-scrollbar scroll-smooth">
              <div className="max-w-4xl mx-auto space-y-12">
                {activeSession.messages.length === 0 ? (
                  <div className="h-[65vh] flex flex-col items-center justify-center text-center">
                    <div className="relative mb-10">
                      <div className="absolute inset-0 bg-blue-500/20 blur-[40px] animate-pulse rounded-full" />
                      <div className="relative w-24 h-24 rounded-[2rem] bg-gradient-to-br from-white/10 to-transparent flex items-center justify-center border border-white/20 shadow-2xl">
                        <Sparkles className="text-blue-400" size={44} strokeWidth={1.5} />
                      </div>
                    </div>
                    <h2 className="text-5xl font-black text-white mb-4 tracking-tighter">Atics <span className="text-blue-500">Intelligence</span></h2>
                    <p className="text-zinc-500 text-sm max-w-sm leading-relaxed font-medium uppercase tracking-[0.1em]">
                      Neural-Engine bereit. Fragen Sie nach Analysen, Code oder komplexen Workflows.
                    </p>
                  </div>
                ) : (
                  activeSession.messages.map((m, i) => (
                    <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-4 duration-500`}>
                      <div className={`group relative max-w-[90%] md:max-w-[80%] ${m.role === 'user' ? 'ml-12' : 'mr-12 w-full'}`}>

                        {/* Avatar/Label for Assistant */}
                        {m.role === 'assistant' && (
                          <div className="flex items-center gap-3 mb-3 ml-1">
                            <div className="p-1.5 rounded-lg bg-blue-500/20 text-blue-400 border border-blue-500/20">
                              <Bot size={14} strokeWidth={2.5} />
                            </div>
                            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-blue-400/80">Atics Antwort</span>
                            {isLoading && i === activeSession.messages.length - 1 && (
                              <div className="flex gap-1 ml-2">
                                <span className="w-1 h-1 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                                <span className="w-1 h-1 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                                <span className="w-1 h-1 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                              </div>
                            )}
                          </div>
                        )}

                        <div className={`relative p-6 md:p-8 rounded-[2rem] transition-all duration-300 ${m.role === 'user'
                            ? 'bg-white text-black font-semibold shadow-[0_20px_40px_rgba(255,255,255,0.05)] border-t border-white/20'
                            : 'bg-white/5 border border-white/10 backdrop-blur-md shadow-2xl border-l-4 border-l-blue-500'
                          }`}>
                          {m.role === 'user' ? (
                            <div className="flex items-start gap-4">
                              <p className="flex-1 leading-relaxed">{m.content}</p>
                              <User size={18} className="mt-1 opacity-40" />
                            </div>
                          ) : (
                            <div className="prose prose-invert prose-sm max-w-none">
                              <ReactMarkdown components={CustomMarkdown} remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                            </div>
                          )}
                        </div>

                        {/* Decoration for AI cards to match Challenge Mode */}
                        {m.role === 'assistant' && (
                          <div className="absolute top-4 right-6 opacity-[0.03] pointer-events-none">
                            <Zap size={60} />
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
                <div className="h-20" />
              </div>
            </div>

            {/* INPUT AREA */}
            <div className="p-10 pt-2 bg-gradient-to-t from-[#050505] via-[#050505]/95 to-transparent relative z-40">
              <div className="max-w-3xl mx-auto">
                <div className="glass-panel rounded-[2rem] p-3 flex items-end gap-3 transition-all duration-500 shadow-2xl border border-white/5 focus-within:border-blue-500/40 focus-within:shadow-[0_0_50px_rgba(59,130,246,0.15)] focus-within:ring-1 focus-within:ring-blue-500/20 bg-zinc-900/50">
                  <button
                    onClick={() => setUseRag(!useRag)}
                    className={`p-4 rounded-2xl transition-all duration-300 flex flex-col items-center gap-1 ${useRag ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/20' : 'bg-white/5 text-zinc-500 hover:text-zinc-300'}`}
                  >
                    <Zap size={20} fill={useRag ? "currentColor" : "none"} />
                    <span className="text-[8px] font-black uppercase tracking-tighter">RAG</span>
                  </button>

                  <textarea
                    rows={1}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleChatSubmit())}
                    placeholder="Frage eingeben oder Anweisungen geben..."
                    className="flex-1 bg-transparent border-none focus:ring-0 outline-none text-white py-4 px-3 resize-none max-h-48 hide-scrollbar text-[15px] placeholder:text-zinc-600 font-medium"
                    onInput={(e: any) => { e.target.style.height = 'auto'; e.target.style.height = e.target.scrollHeight + 'px'; }}
                  />

                  <button
                    disabled={!input.trim() || isLoading}
                    onClick={handleChatSubmit}
                    className="p-4 rounded-2xl bg-white text-black hover:bg-zinc-200 disabled:opacity-10 transition-all active:scale-90 shadow-xl group"
                  >
                    <ArrowUp size={20} strokeWidth={3} className="group-hover:-translate-y-0.5 transition-transform" />
                  </button>
                </div>
                <p className="text-center mt-4 text-[9px] text-zinc-600 font-bold uppercase tracking-[0.2em]">
                  FHDW ATICS
                </p>
              </div>
            </div>
          </div>
        ) : (
          /* CHALLENGE DASHBOARD (Beibehalten und optimiert) */
          <div className="flex-1 flex flex-col p-8 overflow-auto hide-scrollbar space-y-8 animate-in fade-in duration-700">
            <div className="relative group overflow-hidden glass-card rounded-[2.5rem] p-10 flex flex-col gap-8 ring-1 ring-white/10 bg-gradient-to-br from-white/5 to-transparent shadow-2xl">
              <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/5 blur-[80px] -mr-32 -mt-32" />
              <div className="relative z-10">
                <div className="flex items-center gap-3 mb-4">
                  <span className="px-4 py-1.5 rounded-full bg-blue-500/10 text-blue-400 text-[10px] font-black uppercase tracking-[0.3em] border border-blue-500/20">Active Operation</span>
                </div>
                <h1 className="text-5xl font-black text-white mb-2 tracking-tighter">Challenge <span className="text-blue-500">01</span></h1>
                <p className="text-zinc-500 font-mono text-xs uppercase tracking-[0.4em]">Investment Portfolio Audit · Multi-Agent</p>
              </div>
              {/* Challenge 1 Input Form */}
              <div className="relative z-10 grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="flex flex-col gap-1">
                  <label className="text-[9px] font-black uppercase tracking-[0.3em] text-zinc-500">Thema / Ticker</label>
                  <input
                    value={c1Thema}
                    onChange={e => setC1Thema(e.target.value)}
                    disabled={isLoading}
                    className="bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-white text-sm font-mono focus:outline-none focus:border-blue-500/60 disabled:opacity-40 placeholder:text-zinc-600"
                    placeholder="z.B. Artificial Intelligence"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-[9px] font-black uppercase tracking-[0.3em] text-zinc-500">Kapital (EUR)</label>
                  <input
                    type="number"
                    value={c1Kapital}
                    onChange={e => setC1Kapital(e.target.value)}
                    disabled={isLoading}
                    className="bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-white text-sm font-mono focus:outline-none focus:border-blue-500/60 disabled:opacity-40"
                    placeholder="2000"
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-[9px] font-black uppercase tracking-[0.3em] text-zinc-500">Risikoprofil</label>
                  <select
                    value={c1Risiko}
                    onChange={e => setC1Risiko(e.target.value)}
                    disabled={isLoading}
                    className="bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-white text-sm font-mono focus:outline-none focus:border-blue-500/60 disabled:opacity-40 appearance-none"
                  >
                    <option value="Low Risk">Low Risk</option>
                    <option value="Medium Risk">Medium Risk</option>
                    <option value="High Risk">High Risk</option>
                  </select>
                </div>
                <div className="flex flex-col gap-1">
                  <label className="text-[9px] font-black uppercase tracking-[0.3em] text-zinc-500">Anlagehorizont</label>
                  <input
                    value={c1Horizont}
                    onChange={e => setC1Horizont(e.target.value)}
                    disabled={isLoading}
                    className="bg-black/40 border border-white/10 rounded-xl px-4 py-2.5 text-white text-sm font-mono focus:outline-none focus:border-blue-500/60 disabled:opacity-40"
                    placeholder="10 Jahre"
                  />
                </div>
              </div>

              <div className="relative z-10 flex justify-end">
                <button
                  onClick={runChallenge}
                  disabled={isLoading}
                  className="group flex items-center gap-5 px-10 py-6 rounded-[2rem] bg-blue-600 text-white font-black hover:bg-blue-500 transition-all shadow-[0_20px_50px_rgba(37,99,235,0.3)] disabled:opacity-50 active:scale-95"
                >
                  {isLoading ? <Activity size={24} className="animate-spin" /> : <Play size={24} fill="white" />}
                  <span className="uppercase tracking-[0.2em] text-sm">{isLoading ? 'Processing...' : 'Execute Workflow'}</span>
                </button>
              </div>
            </div>

            <div className="grid grid-cols-12 gap-8">
              {/* LOGS */}
              <div className="col-span-4 glass-panel rounded-[2.5rem] overflow-hidden flex flex-col border border-white/5 shadow-2xl">
                <div className="p-6 border-b border-white/5 bg-white/5 flex items-center justify-between">
                  <div className="flex items-center gap-3 text-zinc-400">
                    <Terminal size={18} className="text-blue-400" />
                    <span className="text-[10px] font-black uppercase tracking-[0.3em]">System Logs</span>
                  </div>
                </div>
                <div className="p-6 font-mono text-[11px] space-y-4 overflow-y-auto flex-1 hide-scrollbar bg-black/40">
                  {challengeStatus.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center text-zinc-700 italic gap-2">
                      <div className="w-12 h-1 bg-white/5 rounded-full" />
                      Ready for deployment
                    </div>
                  )}
                  {challengeStatus.map((s, i) => (
                    <div key={i} className="text-zinc-400 flex gap-3 leading-relaxed animate-in slide-in-from-left-2 duration-300">
                      <span className="text-blue-500/50 font-bold shrink-0">[{new Date().toLocaleTimeString([], { hour12: false, second: '2-digit' })}]</span>
                      <span className="break-words font-medium">{s}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* AGENT CARDS */}
              <div className="col-span-8 space-y-8 pb-10">
                {agentList.map((agent, agentIdx) => {
                  const palette = [
                    { border: 'border-l-blue-500',   text: 'text-blue-400',   bg: 'bg-blue-500/20',   ring: 'border-blue-500/20'   },
                    { border: 'border-l-emerald-500', text: 'text-emerald-400', bg: 'bg-emerald-500/20', ring: 'border-emerald-500/20' },
                    { border: 'border-l-amber-500',   text: 'text-amber-400',   bg: 'bg-amber-500/20',   ring: 'border-amber-500/20'   },
                    { border: 'border-l-rose-500',    text: 'text-rose-400',    bg: 'bg-rose-500/20',    ring: 'border-rose-500/20'    },
                    { border: 'border-l-violet-500',  text: 'text-violet-400',  bg: 'bg-violet-500/20',  ring: 'border-violet-500/20'  },
                    { border: 'border-l-cyan-500',    text: 'text-cyan-400',    bg: 'bg-cyan-500/20',    ring: 'border-cyan-500/20'    },
                  ];
                  const c = palette[agentIdx % palette.length];
                  const isWriter = /cio|portfolio|report|writer/i.test(agent.name);
                  return (
                    <div key={agentIdx} className={`glass-card rounded-[2.5rem] p-10 border-l-8 ${c.border} shadow-2xl animate-in slide-in-from-right-4 duration-500 relative overflow-hidden group`}>
                      <div className="absolute top-0 right-0 p-10 opacity-[0.03] group-hover:scale-110 transition-transform duration-700">
                        {isWriter ? <PenTool size={120} /> : <Search size={120} />}
                      </div>

                      {/* Agent header */}
                      <div className="flex items-start gap-5 mb-8">
                        <div className={`relative p-4 rounded-[1.5rem] shadow-xl border flex-shrink-0 ${c.bg} ${c.text} ${c.ring}`}>
                          {isWriter ? <PenTool size={28} strokeWidth={2.5} /> : <Search size={28} strokeWidth={2.5} />}
                          {agent.completed && (
                            <div className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center shadow-lg text-white text-[10px] font-black">✓</div>
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex flex-wrap items-center gap-2 mb-1">
                            <h3 className={`text-[11px] font-black uppercase tracking-[0.4em] ${c.text}`}>Agent Interface</h3>
                            {agent.completed ? (
                              <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-[9px] font-black uppercase tracking-wider border border-emerald-500/20">✓ Done</span>
                            ) : isLoading ? (
                              <span className={`px-2 py-0.5 rounded-full ${c.bg} ${c.text} text-[9px] font-black uppercase tracking-wider border ${c.ring} animate-pulse`}>Working…</span>
                            ) : null}
                          </div>
                          <p className="text-xl font-bold text-white tracking-tight">{agent.name}</p>
                          {agent.taskName && (
                            <p className="mt-1 text-[11px] text-zinc-500 font-mono truncate">→ {agent.taskName}</p>
                          )}
                        </div>
                      </div>

                      {/* Terminal log – each entry is a full Rich panel with \n chars */}
                      <div className={`bg-black/50 rounded-2xl border border-white/5 p-4 font-mono text-[11px] max-h-80 overflow-y-auto hide-scrollbar ${c.text}`}>
                        {agent.logs.length === 0 ? (
                          <span className="text-zinc-700 italic">Awaiting output…</span>
                        ) : (
                          agent.logs.map((entry, li) => (
                            <pre key={li} className="whitespace-pre-wrap break-words leading-relaxed mb-3 last:mb-0 opacity-80">{entry}</pre>
                          ))
                        )}
                      </div>
                    </div>
                  );
                })}

                {/* Final Result Card */}
                {finalResult && (
                  <div className="glass-card rounded-[2.5rem] p-10 border-l-8 border-l-purple-500 shadow-2xl animate-in slide-in-from-right-4 duration-700 relative overflow-hidden group bg-purple-500/5">
                    <div className="absolute top-0 right-0 p-10 opacity-[0.03] group-hover:scale-110 transition-transform duration-700"><Activity size={120} /></div>
                    <div className="flex items-center gap-5 mb-10">
                      <div className="p-4 rounded-[1.5rem] bg-purple-500/20 text-purple-400 shadow-xl border border-purple-500/20">
                        <Zap size={28} strokeWidth={2.5} />
                      </div>
                      <div>
                        <h3 className="text-[11px] font-black uppercase tracking-[0.4em] text-purple-400 mb-1">Mission Outcome</h3>
                        <p className="text-xl font-bold text-white tracking-tight">Final Result</p>
                      </div>
                    </div>
                    <div className="bg-black/40 p-8 rounded-[2rem] border border-white/10 shadow-inner leading-relaxed overflow-x-auto">
                      <ReactMarkdown components={CustomMarkdown}>{finalResult}</ReactMarkdown>
                    </div>
                  </div>
                )}

                {agentList.length === 0 && !finalResult && (
                  <div className="h-40 flex items-center justify-center border-2 border-dashed border-white/5 rounded-[2rem] text-zinc-600 font-bold uppercase tracking-widest text-[10px]">Awaiting Agent Data...</div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      <style jsx global>{`
        @keyframes reveal {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-reveal {
          animation: reveal 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
        }
        .glass-panel {
          background: rgba(255, 255, 255, 0.03);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
        }
        .glass-card {
          background: rgba(255, 255, 255, 0.02);
          backdrop-filter: blur(40px);
          -webkit-backdrop-filter: blur(40px);
        }
        .hide-scrollbar::-webkit-scrollbar {
          display: none;
        }
        .hide-scrollbar {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
      `}</style>
    </div>
  );
}
