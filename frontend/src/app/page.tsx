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
    <div className="flex h-screen w-full bg-black text-[#ededed] font-sans selection:bg-zinc-800">

      {/* SIDEBAR */}
      <aside
        style={{ width: isSidebarOpen ? '260px' : '0px' }}
        className="h-full bg-black border-r border-[#222] transition-all duration-300 overflow-hidden shrink-0 z-30"
      >
        <div className="w-[260px] p-4 flex flex-col h-full">
          <button
            onClick={() => setMessages([])}
            className="flex items-center justify-center gap-2 w-full bg-white text-black hover:bg-zinc-200 py-2 rounded-md text-sm font-medium transition-all mb-6 mt-2 shadow-lg shadow-white/5"
          >
            <PlusCircle size={14} />
            New Chat
          </button>

          <div className="flex-1">
            <label className="flex items-center justify-between w-full px-3 py-2 rounded-md text-sm cursor-pointer hover:bg-[#111] transition-colors group">
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={useRag}
                  onChange={() => setUseRag(!useRag)}
                  className="custom-checkbox"
                />
                <span className={useRag ? 'text-white' : 'text-zinc-500 font-medium'}>Retrieval-Augmented Generation (RAG)</span>
              </div>
              <Zap size={14} className={useRag ? 'text-blue-500' : 'text-zinc-800'} />
            </label>
          </div>
        </div>
      </aside>

      {/* MAIN CONTENT */}
      <div className="flex-1 flex flex-col min-w-0 h-full bg-black">

        {/* HEADER */}
        <header className="h-14 flex items-center px-6 shrink-0 vercel-glass z-20">
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="p-1.5 hover:bg-[#111] rounded-md transition-colors text-zinc-500 hover:text-white"
          >
            {isSidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
          </button>
        </header>

        {/* CHAT VIEW */}
        <div className="flex-1 overflow-y-auto px-6 hide-scrollbar">
          <div className="max-w-3xl mx-auto w-full flex flex-col space-y-8 py-12">
            {messages.length === 0 ? (
              <div className="h-[40vh] flex flex-col items-center justify-center text-center opacity-20">
                <Bot size={48} strokeWidth={1} className="text-white mb-4" />
                <p className="text-sm tracking-widest uppercase">How can I help you today?</p>
              </div>
            ) : (
              messages.map((m, i) => (
                <div
                  key={i}
                  className={`flex w-full ${m.role === 'user' ? 'justify-end' : 'justify-start'} animate-in fade-in slide-in-from-bottom-2`}
                >
                  <div className={`flex flex-col max-w-[80%] ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                    <div className={m.role === 'user' ? 'bubble-user glow-user' : 'bubble-ai glow-ai'}>
                      <div className={`prose prose-sm max-w-none ${m.role === 'user' ? 'prose-invert text-black' : 'prose-invert text-zinc-300'}`}>
                        <ReactMarkdown>{m.content}</ReactMarkdown>
                      </div>
                    </div>
                    <span className="text-[9px] mt-1.5 px-1 font-mono uppercase text-zinc-600 tracking-tighter">
                      {m.role === 'user' ? 'User' : 'LLM'}
                    </span>
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* INPUT AREA */}
        <div className="w-full flex justify-center p-6 pb-10 shrink-0 bg-black">
          <div className="w-full max-w-2xl">
            <div className="relative flex items-end bg-[#0a0a0a] border border-[#222] rounded-xl focus-within:border-zinc-500 transition-all duration-300 shadow-2xl">
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
                className="flex-1 bg-transparent border-none focus:ring-0 text-[15px] text-white px-4 py-4 resize-none max-h-60 outline-none placeholder-zinc-800"
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = 'auto';
                  target.style.height = `${target.scrollHeight}px`;
                }}
              />

              <div className="p-2">
                <button
                  onClick={handleSubmit}
                  disabled={!input.trim() || isLoading}
                  className={`w-9 h-9 rounded-lg flex items-center justify-center transition-all ${
                    input.trim()
                    ? 'bg-white text-black hover:scale-105 active:scale-95'
                    : 'bg-[#111] text-zinc-800'
                  }`}
                >
                  <ArrowUp size={18} strokeWidth={2.5} />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
