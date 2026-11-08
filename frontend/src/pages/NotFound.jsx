import React from 'react';
import { EyeOff, ArrowLeft } from 'lucide-react';
import Button from '../components/ui/Button';

export default function NotFound() {
  return (
    <div className="py-16 text-center max-w-md mx-auto space-y-5">
      <div className="w-14 h-14 rounded-2xl bg-slate-100 text-slate-500 flex items-center justify-center mx-auto">
        <EyeOff className="w-7 h-7" />
      </div>
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Page Not Found</h1>
        <p className="text-sm text-slate-600 mt-1">
          The requested clinical screening page does not exist or has been relocated.
        </p>
      </div>
      <div>
        <Button to="/" variant="secondary" icon={ArrowLeft}>
          Return to Overview
        </Button>
      </div>
    </div>
  );
}

