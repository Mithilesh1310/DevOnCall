'use client';

import React, { useEffect, useState } from 'react';
import { Activity, Database, Server, RefreshCw } from 'lucide-react';

export function Header() {
  const [apiStatus, setApiStatus] = useState<'checking' | 'connected' | 'error'>('checking');
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const checkStatus = async () => {
    setApiStatus('checking');
    try {
      const res = await fetch(`${apiUrl}/health`, { cache: 'no-store' });
      if (res.ok) {
        setApiStatus('connected');
      } else {
        setApiStatus('error');
      }
    } catch {
      setApiStatus('error');
    }
  };

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-16 border-b border-[#1e2438] bg-[#0d101a] px-6 flex items-center justify-between sticky top-0 z-10">
      <div className="flex items-center space-x-4">
        <span className="text-sm font-semibold text-slate-200">System Dashboard</span>
        <span className="px-2.5 py-0.5 text-xs font-mono rounded-full bg-slate-800 text-slate-400 border border-slate-700">
          Local Sandbox
        </span>
      </div>

      <div className="flex items-center space-x-4">
        {/* Backend API status indicator */}
        <div className="flex items-center space-x-2 text-xs font-mono px-3 py-1.5 rounded-md bg-[#121624] border border-[#1e2438]">
          <Server className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400">API:</span>
          {apiStatus === 'checking' && (
            <span className="text-amber-400 flex items-center">
              <RefreshCw className="w-3 h-3 animate-spin mr-1" /> Checking
            </span>
          )}
          {apiStatus === 'connected' && (
            <span className="text-emerald-400 flex items-center">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1.5 animate-ping"></span>
              Online
            </span>
          )}
          {apiStatus === 'error' && (
            <span className="text-rose-400 flex items-center">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-500 mr-1.5"></span>
              Offline
            </span>
          )}
        </div>

        <button 
          onClick={checkStatus}
          className="p-1.5 text-slate-400 hover:text-white rounded-md hover:bg-[#1e2438] transition-colors"
          title="Refresh connection status"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
