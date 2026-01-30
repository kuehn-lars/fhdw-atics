"use client";

import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import {
  ArrowUp,
  PlusCircle,
  Zap,
  Bot,
  User,
  PanelLeftClose,
  PanelLeftOpen,
  Sparkles,
  LayoutGrid
} from "lucide-react";

export default function SimpleChat() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [useRag, setUseRag] = useState(true);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async () => {
    if (!input.trim() || isLoading) return;
    const userQuery = input;
    setInput("");
    setIsLoading(true);
    setMessages(prev => [...prev, { role: "user", content: userQuery }, { role: "assistant", content: "" }]);

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
        setMessages(prev => {
          const newMsgs = [...prev];
          if (newMsgs.length > 0) newMsgs[newMsgs.length - 1].content = acc;
          return newMsgs;
        });
      }
    } catch (e) { console.error(e); } finally { setIsLoading(false); }
  };

  return (
    <div className="flex h-screen w-full bg-[#0F1117] overflow-hidden">

      {/* SIDEBAR - Slimmed to 260px */}
      <aside
        style={{ width: isSidebarOpen ? '260px' : '0px' }}
        className="h-full bg-[#161922]/80 backdrop-blur-2xl border-r border-white/5 transition-all duration-500 ease-[cubic-bezier(0.4,0,0.2,1)] overflow-hidden shrink-0 z-30"
      >
        <div className="w-[260px] p-6 flex flex-col h-full">
          <div className="flex items-center gap-3 mb-10 px-2">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-purple-500 p-[1px]">
              <div className="w-full h-full rounded-[11px] bg-[#161922] flex items-center justify-center">
                <LayoutGrid size={16} className="text-white" />
              </div>
            </div>
            <span className="font-bold text-white tracking-tight text-md">Module</span>
          </div>

          <button
            onClick={() => setMessages([])}
            className="flex items-center justify-center gap-2 w-full bg-white/5 hover:bg-white/10 border border-white/10 py-3 rounded-xl text-sm font-medium text-white transition-all active:scale-[0.98] mb-8 group"
          >
            <PlusCircle size={16} className="text-zinc-400 group-hover:text-white transition-colors" />
            New Chat
          </button>

          <div className="flex-1 space-y-6">
            <div>
              <p className="text-[10px] font-black text-zinc-500 uppercase tracking-widest px-2 mb-4">Configuration</p>

              {/* Custom Checkbox for RAG */}
              <label className="flex items-center justify-between p-3 rounded-xl cursor-pointer hover:bg-white/5 transition-all group">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={useRag}
                    onChange={() => setUseRag(!useRag)}
                    className="custom-checkbox"
                  />
                  <span className={`text-sm font-medium transition-colors ${useRag ? 'text-zinc-200' : 'text-zinc-500'}`}>
                    Enable RAG
                  </span>
                </div>
                <Zap size={14} className={useRag ? 'text-purple-400' : 'text-zinc-600'} />
              </label>
            </div>
          </div>
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col min-w-0 h-full relative z-10">

        {/* HEADER */}
        <header className="h-20 flex items-center px-10 justify-between shrink-0 bg-transparent">
          <div className="flex items-center gap-6">
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-2.5 bg-white/5 hover:bg-white/10 rounded-xl transition-all text-zinc-400 hover:text-white border border-white/5 shadow-xl"
            >
              {isSidebarOpen ? <PanelLeftClose size={20} /> : <PanelLeftOpen size={20} />}
            </button>
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-bold tracking-tight text-gradient-premium">Chat</h2>
            </div>
          </div>
        </header>

        {/* CHAT VIEW */}
        <div className="flex-1 overflow-y-auto px-6 md:px-12 hide-scrollbar">
          <div className="max-w-4xl mx-auto w-full space-y-12 py-10">
            {messages.length === 0 ? (
              <div className="h-[50vh] flex flex-col items-center justify-center text-center opacity-40">
                <div className="p-6 rounded-[2rem] bg-white/5 border border-white/5 mb-6">
                  <Bot size={40} strokeWidth={1.5} className="text-zinc-400" />
                </div>
                <h1 className="text-lg font-medium text-white tracking-[0.2em] uppercase">Session Ready</h1>
              </div>
            ) : (
              messages.map((m, i) => (
                <div key={i} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'} w-full animate-message`}>
                  <div className="flex items-center gap-2 mb-3 px-2">
                    <span className={`text-[9px] font-black uppercase tracking-[0.2em] ${m.role === 'user' ? 'text-blue-400/70' : 'text-purple-400/70'}`}>
                      {m.role === 'user' ? 'User' : 'Assistant'}
                    </span>
                  </div>
                  <div className={`max-w-[85%] md:max-w-[75%] ${m.role === 'user' ? 'matte-user' : 'matte-ai'}`}>
                    <div className="prose prose-invert prose-sm max-w-none prose-p:text-zinc-200 prose-p:text-[15px] prose-p:leading-relaxed">
                      <ReactMarkdown>{m.content}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* INPUT AREA */}
        <div className="w-full flex justify-center p-6 pb-10 shrink-0">
          <div className="w-full max-w-2xl">
            <div className="relative flex items-end bg-[#1C212E]/60 backdrop-blur-3xl border border-white/10 rounded-[28px] p-2 input-glow group transition-all duration-300">

              <div className="mb-3.5 ml-4 text-zinc-500 group-focus-within:text-purple-400 transition-colors duration-500">
                <Sparkles size={18} />
              </div>

              <textarea
                rows={1}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit();
                  }
                }}
                placeholder="Send a message..."
                className="flex-1 bg-transparent border-none focus:ring-0 text-white px-4 py-3.5 resize-none max-h-48 outline-none text-[15px] leading-relaxed placeholder-zinc-600 input-scroll overflow-y-auto"
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = 'auto';
                  target.style.height = `${Math.min(target.scrollHeight, 192)}px`;
                }}
              />

              <button
                onClick={handleSubmit}
                disabled={!input.trim() || isLoading}
                className={`w-11 h-11 rounded-[22px] flex items-center justify-center transition-all duration-500 mb-0.5 mr-0.5 shrink-0 ${
                  input.trim()
                  ? 'btn-gradient text-white scale-100 shadow-lg'
                  : 'bg-white/5 text-zinc-700 scale-75 opacity-10'
                }`}
              >
                <ArrowUp size={22} strokeWidth={3} />
              </button>
            </div>

            <div className="flex justify-center mt-5 gap-8 select-none opacity-20 hover:opacity-40 transition-opacity">
                <span className="text-[9px] font-black text-zinc-400 uppercase tracking-[0.2em]">Secure Node</span>
                <span className="text-[9px] font-black text-zinc-400 uppercase tracking-[0.2em]">v4.0.0</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
