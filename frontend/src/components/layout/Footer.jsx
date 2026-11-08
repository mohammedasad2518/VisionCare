import React from 'react';
import { Link } from 'react-router-dom';
import { Eye, ShieldCheck } from 'lucide-react';

export default function Footer() {
  const currentYear = 2026;

  return (
    <footer className="bg-white border-t border-slate-200 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          {/* Brand & Overview */}
          <div className="md:col-span-2 space-y-3">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center text-white">
                <Eye className="w-4 h-4" />
              </div>
              <span className="text-lg font-bold tracking-tight text-slate-900">
                VisionCare
              </span>
            </div>
            <p className="text-sm text-slate-600 max-w-md leading-relaxed">
              Standardized digital screening platform for ocular health assessment. Evaluates digital retinal fundus photography to detect indications of common ocular pathologies.
            </p>
            <div className="flex items-center gap-2 text-xs text-slate-500 pt-1">
              <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>Designed according to clinical screening reference workflows</span>
            </div>
          </div>

          {/* Quick Navigation */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-900 mb-3">
              Navigation
            </h4>
            <ul className="space-y-2 text-sm">
              <li>
                <Link to="/" className="text-slate-600 hover:text-emerald-700 transition-colors">
                  Home Overview
                </Link>
              </li>
              <li>
                <Link to="/screening" className="text-slate-600 hover:text-emerald-700 transition-colors">
                  Retinal Screening
                </Link>
              </li>
              <li>
                <Link to="/history" className="text-slate-600 hover:text-emerald-700 transition-colors">
                  Screening Records
                </Link>
              </li>
            </ul>
          </div>

          {/* Pathology Categories */}
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-900 mb-3">
              Screening Targets
            </h4>
            <ul className="space-y-2 text-sm text-slate-600">
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                <span>Normal Retinal Pattern</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                <span>Cataract Opacity</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                <span>Diabetic Retinopathy</span>
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                <span>Glaucomatous Changes</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Medical Disclaimer & Copyright */}
        <div className="pt-8 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <p className="max-w-2xl text-center sm:text-left leading-relaxed">
            <span className="font-semibold text-slate-700">Clinical Disclaimer:</span> VisionCare is an investigational screening and triage assistance platform. Results should be interpreted by licensed eye care professionals alongside comprehensive examinations.
          </p>
          <p className="shrink-0">
            &copy; {currentYear} VisionCare. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
