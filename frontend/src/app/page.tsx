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
  const [sessions, setSessions] = useState<{id: string, title: string, messages: any[]}[]>([
    { id: "default", title: "Neue Unterhaltung", messages: [] }
  ]);
  const [currentSessionId, setCurrentSessionId] = useState("default");
  const [input, setInput] = useState("");
  const [useRag, setUseRag] = useState(true);
  const [selectedChallenge, setSelectedChallenge] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Challenge States
  const [challengeStatus, setChallengeStatus] = useState<string[]>([]);
  const [researcherMsgs, setResearcherMsgs] = useState<string[]>([]);
  const [writerMsgs, setWriterMsgs] = useState<string[]>([]);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const isAutoScrollRef = useRef(true);

  const activeSession = sessions.find(s => s.id === currentSessionId) || sessions[0];

  const formatResponse = (text: string) => text.replaceAll('\\n', '\n');

  const handleSelectChallenge = (id: number) => {
    if (selectedChallenge !== id) {
      setChallengeStatus([]);
      setResearcherMsgs([]);
      setWriterMsgs([]);
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

  const runChallenge = async () => {
    if (!selectedChallenge) return;
    setIsLoading(true);
    setChallengeStatus(["Initializing neural agents..."]);
    setResearcherMsgs([]);
    setWriterMsgs([]);

    try {
      const resp = await fetch(`http://127.0.0.1:8000/agents/challenge${selectedChallenge}`, { method: "POST" });
      if (!resp.body) return;
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

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
            const content = formatResponse(obj.message || obj.text || obj.answer || "");
            if (obj.type === 'status') setChallengeStatus(p => [...p, content]);
            else if (obj.type === 'log') {
              if (content.toLowerCase().includes('research')) setResearcherMsgs(p => [...p, content]);
              else if (content.toLowerCase().includes('writer')) setWriterMsgs(p => [...p, content]);
              else setChallengeStatus(p => [...p, content]);
            } else if (obj.type === 'result') {
                setWriterMsgs(p => [...p, content]);
                setChallengeStatus(p => [...p, "Workflow completed successfully."]);
            }
          } catch(e) {}
        }
      }
    } catch (e) { setChallengeStatus(p => [...p, "System error occurred..."]); } finally { setIsLoading(false); }
  };

  return (
    <div className="flex h-screen w-full relative overflow-hidden bg-[#050505] text-zinc-200 font-sans">
      {/* Dynamic Background */}
      <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] bg-blue-600/10 rounded-full blur-[140px] animate-pulse pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[60%] h-[60%] bg-emerald-600/10 rounded-full blur-[140px] animate-pulse pointer-events-none" style={{animationDelay: '2s'}} />

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
                {[1, 2, 3].map((id) => (
                  <button key={id} onClick={() => handleSelectChallenge(id)} className={`flex items-center gap-3 w-full px-3 py-3 rounded-xl transition-all ${viewMode === 'challenge' && selectedChallenge === id ? 'bg-blue-500/20 text-blue-400 border border-blue-500/20' : 'text-zinc-500 hover:bg-white/5'}`}>
                    <Cpu size={16} />
                    <span className="text-xs font-semibold uppercase tracking-wider">Challenge 0{id}</span>
                  </button>
                ))}
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
                                 <span className="w-1 h-1 rounded-full bg-blue-500 animate-bounce" style={{animationDelay: '0ms'}} />
                                 <span className="w-1 h-1 rounded-full bg-blue-500 animate-bounce" style={{animationDelay: '150ms'}} />
                                 <span className="w-1 h-1 rounded-full bg-blue-500 animate-bounce" style={{animationDelay: '300ms'}} />
                               </div>
                             )}
                          </div>
                        )}

                        <div className={`relative p-6 md:p-8 rounded-[2rem] transition-all duration-300 ${
                          m.role === 'user'
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
          <div className="flex-1 flex flex-col p-8 overflow-hidden space-y-8 animate-in fade-in duration-700">
            <div className="relative group overflow-hidden glass-card rounded-[2.5rem] p-10 flex justify-between items-center ring-1 ring-white/10 bg-gradient-to-br from-white/5 to-transparent shadow-2xl">
              <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/5 blur-[80px] -mr-32 -mt-32" />
              <div className="relative z-10">
                <div className="flex items-center gap-3 mb-4">
                  <span className="px-4 py-1.5 rounded-full bg-blue-500/10 text-blue-400 text-[10px] font-black uppercase tracking-[0.3em] border border-blue-500/20">Active Operation</span>
                </div>
                <h1 className="text-5xl font-black text-white mb-2 tracking-tighter">Challenge <span className="text-blue-500">0{selectedChallenge}</span></h1>
                <p className="text-zinc-500 font-mono text-xs uppercase tracking-[0.4em]">Multi-Agent Orchestration Engine</p>
              </div>
              <button
                onClick={runChallenge}
                disabled={isLoading}
                className="relative z-10 group flex items-center gap-5 px-10 py-6 rounded-[2rem] bg-blue-600 text-white font-black hover:bg-blue-500 transition-all shadow-[0_20px_50px_rgba(37,99,235,0.3)] disabled:opacity-50 active:scale-95"
              >
                {isLoading ? <Activity size={24} className="animate-spin" /> : <Play size={24} fill="white" />}
                <span className="uppercase tracking-[0.2em] text-sm">{isLoading ? 'Processing...' : 'Execute Workflow'}</span>
              </button>
            </div>

            <div className="flex-1 grid grid-cols-12 gap-8 min-h-0">
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
                      <span className="text-blue-500/50 font-bold shrink-0">[{new Date().toLocaleTimeString([], {hour12:false, second: '2-digit'})}]</span>
                      <span className="break-words font-medium">{s}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* AGENT OUTPUTS */}
              <div className="col-span-8 space-y-8 overflow-y-auto hide-scrollbar pb-10">
                {/* Researcher Card */}
                <div className="glass-card rounded-[2.5rem] p-10 border-l-8 border-l-blue-500 shadow-2xl animate-in slide-in-from-right-4 duration-500 relative overflow-hidden group">
                   <div className="absolute top-0 right-0 p-10 opacity-[0.03] group-hover:scale-110 transition-transform duration-700"><Search size={120} /></div>
                   <div className="flex items-center gap-5 mb-10">
                      <div className="p-4 rounded-[1.5rem] bg-blue-500/20 text-blue-400 shadow-xl border border-blue-500/20">
                        <Search size={28} strokeWidth={2.5} />
                      </div>
                      <div>
                        <h3 className="text-[11px] font-black uppercase tracking-[0.4em] text-blue-400 mb-1">Agent Interface</h3>
                        <p className="text-xl font-bold text-white tracking-tight">Deep Researcher</p>
                      </div>
                   </div>
                   <div className="space-y-6">
                      {researcherMsgs.length > 0 ? (
                        researcherMsgs.map((m, i) => (
                          <div key={i} className="bg-white/5 p-8 rounded-[2rem] border border-white/5 backdrop-blur-sm">
                            <ReactMarkdown components={CustomMarkdown}>{m}</ReactMarkdown>
                          </div>
                        ))
                      ) : (
                        <div className="h-40 flex items-center justify-center border-2 border-dashed border-white/5 rounded-[2rem] text-zinc-600 font-bold uppercase tracking-widest text-[10px]">Awaiting Agent Data...</div>
                      )}
                   </div>
                </div>

                {/* Writer Card */}
                <div className="glass-card rounded-[2.5rem] p-10 border-l-8 border-l-emerald-500 shadow-2xl animate-in slide-in-from-right-4 duration-700 relative overflow-hidden group">
                   <div className="absolute top-0 right-0 p-10 opacity-[0.03] group-hover:scale-110 transition-transform duration-700"><PenTool size={120} /></div>
                   <div className="flex items-center gap-5 mb-10">
                      <div className="p-4 rounded-[1.5rem] bg-emerald-500/20 text-emerald-400 shadow-xl border border-emerald-500/20">
                        <PenTool size={28} strokeWidth={2.5} />
                      </div>
                      <div>
                        <h3 className="text-[11px] font-black uppercase tracking-[0.4em] text-emerald-400 mb-1">Executive Interface</h3>
                        <p className="text-xl font-bold text-white tracking-tight">Strategic Writer</p>
                      </div>
                   </div>
                   <div className="space-y-6">
                      {writerMsgs.length > 0 ? (
                        writerMsgs.map((m, i) => (
                          <div key={i} className="bg-emerald-500/5 p-8 rounded-[2rem] border border-emerald-500/10 shadow-inner leading-relaxed">
                            <ReactMarkdown components={CustomMarkdown}>{m}</ReactMarkdown>
                          </div>
                        ))
                      ) : (
                        <div className="h-40 flex items-center justify-center border-2 border-dashed border-white/5 rounded-[2rem] text-zinc-600 font-bold uppercase tracking-widest text-[10px]">Awaiting Finalization...</div>
                      )}
                   </div>
                </div>
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
