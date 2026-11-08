import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  History as HistoryIcon,
  Search,
  RefreshCw,
  Trash2,
  ArrowRight,
  Eye,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  SlidersHorizontal,
  X,
  Clock,
  Database
} from 'lucide-react';
import { Card, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import {
  fetchHistory,
  fetchHistoryRecord,
  deleteHistoryRecord,
  clearAllHistory,
  ApiError
} from '../services/api';

const CATEGORIES = ['All', 'Cataract', 'Diabetic Retinopathy', 'Glaucoma', 'Normal'];
const CATEGORY_ORDER = ['Cataract', 'Diabetic Retinopathy', 'Glaucoma', 'Normal'];

export default function History() {
  const [records, setRecords] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filter & Search State
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');

  // Inspection Modal State
  const [inspectRecord, setInspectRecord] = useState(null);

  // Delete Action State
  const [deletingId, setDeletingId] = useState(null);
  const [showClearModal, setShowClearModal] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [actionNotice, setActionNotice] = useState(null);

  // Format file size
  const formatFileSize = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  // Format ISO timestamp
  const formatDateTime = (isoString) => {
    if (!isoString) return 'N/A';
    try {
      const d = new Date(isoString);
      return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }).format(d);
    } catch {
      return isoString;
    }
  };

  // Fetch history from backend
  const loadHistory = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchHistory({
        skip: 0,
        limit: 100,
        category: selectedCategory !== 'All' ? selectedCategory : null,
      });
      setRecords(data.records);
      setTotalCount(data.totalCount);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError('Unable to retrieve screening records. Please check that the VisionCare backend server is running.');
      }
    } finally {
      setIsLoading(false);
    }
  }, [selectedCategory]);

  useEffect(() => {
    let ignore = false;
    async function startFetch() {
      try {
        const data = await fetchHistory({
          skip: 0,
          limit: 100,
          category: selectedCategory !== 'All' ? selectedCategory : null,
        });
        if (!ignore) {
          setRecords(data.records);
          setTotalCount(data.totalCount);
          setError(null);
        }
      } catch (err) {
        if (!ignore) {
          if (err instanceof ApiError) {
            setError(err.message);
          } else {
            setError('Unable to retrieve screening records. Please check that the VisionCare backend server is running.');
          }
        }
      } finally {
        if (!ignore) {
          setIsLoading(false);
        }
      }
    }
    startFetch();
    return () => {
      ignore = true;
    };
  }, [selectedCategory]);

  // Handle single record deletion
  const handleDeleteRecord = async (recordId, e) => {
    e.stopPropagation();
    setDeletingId(recordId);
    setActionNotice(null);
    try {
      await deleteHistoryRecord(recordId);
      setRecords((prev) => prev.filter((r) => r.id !== recordId));
      setTotalCount((prev) => Math.max(0, prev - 1));
      setActionNotice({ type: 'success', text: `Screening record #${recordId} was deleted successfully.` });
      if (inspectRecord?.id === recordId) {
        setInspectRecord(null);
      }
    } catch (err) {
      setActionNotice({
        type: 'error',
        text: err instanceof ApiError ? err.message : 'Failed to delete record. Please try again.',
      });
    } finally {
      setDeletingId(null);
    }
  };

  // Handle clear-all confirmation
  const handleClearAll = async () => {
    setIsClearing(true);
    setActionNotice(null);
    try {
      const result = await clearAllHistory();
      setRecords([]);
      setTotalCount(0);
      setShowClearModal(false);
      setInspectRecord(null);
      setActionNotice({
        type: 'success',
        text: `Cleared ${result.deletedCount || 'all'} screening history records from local database.`,
      });
    } catch (err) {
      setActionNotice({
        type: 'error',
        text: err instanceof ApiError ? err.message : 'Failed to clear history records.',
      });
    } finally {
      setIsClearing(false);
    }
  };

  // Open inspection drawer / modal
  const handleInspect = async (record) => {
    setInspectRecord(record);
    try {
      const fullRecord = await fetchHistoryRecord(record.id);
      setInspectRecord(fullRecord);
    } catch {
      // Fallback to record already present in list
    }
  };

  // Filter records based on search query
  const filteredRecords = useMemo(() => {
    if (!searchQuery.trim()) return records;
    const q = searchQuery.toLowerCase();
    return records.filter(
      (r) =>
        r.filename.toLowerCase().includes(q) ||
        r.predicted_category.toLowerCase().includes(q) ||
        String(r.id).includes(q)
    );
  }, [records, searchQuery]);

  // Aggregate distribution metrics
  const stats = useMemo(() => {
    const normalCount = records.filter((r) => r.predicted_category === 'Normal').length;
    const pathologyCount = records.length - normalCount;
    return {
      total: totalCount,
      normal: normalCount,
      pathology: pathologyCount,
      lastScreening: records[0]?.created_at || null,
    };
  }, [records, totalCount]);

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Badge variant="emerald" size="sm" icon={Database}>
              Records Archive
            </Badge>
            <span className="text-xs text-slate-400">•</span>
            <span className="text-xs text-slate-500 font-medium">Local SQLite Database</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
            Screening History
          </h1>
          <p className="text-sm sm:text-base text-slate-600 mt-1 max-w-2xl">
            Review past retinal evaluations, view model confidence scores across all four target categories, and manage examination logs.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="secondary"
            size="md"
            icon={RefreshCw}
            disabled={isLoading}
            onClick={loadHistory}
            className={isLoading ? 'animate-spin' : ''}
          >
            Refresh
          </Button>
          <Button to="/screening" variant="primary" size="md">
            New Screening
          </Button>
        </div>
      </div>

      {/* Action Notification Alert */}
      {actionNotice && (
        <div
          className={`p-3.5 rounded-xl border flex items-center justify-between text-xs ${
            actionNotice.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
              : 'bg-rose-50 border-rose-200 text-rose-900'
          }`}
        >
          <div className="flex items-center gap-2">
            {actionNotice.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            )}
            <span className="font-medium">{actionNotice.text}</span>
          </div>
          <button
            onClick={() => setActionNotice(null)}
            className="text-slate-400 hover:text-slate-700 ml-3"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Summary Metrics Cards (when records exist) */}
      {!isLoading && !error && records.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
              Total Archived
            </span>
            <span className="text-2xl font-bold text-slate-900 block mt-1">
              {stats.total}
            </span>
            <span className="text-[11px] text-slate-500 block mt-0.5">Examinations logged</span>
          </div>

          <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
            <span className="text-[10px] uppercase font-bold text-emerald-600 block tracking-wider">
              Screening Negative
            </span>
            <span className="text-2xl font-bold text-emerald-700 block mt-1">
              {stats.normal}
            </span>
            <span className="text-[11px] text-slate-500 block mt-0.5">Normal retina pattern</span>
          </div>

          <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
            <span className="text-[10px] uppercase font-bold text-amber-600 block tracking-wider">
              Pathology Flags
            </span>
            <span className="text-2xl font-bold text-amber-700 block mt-1">
              {stats.pathology}
            </span>
            <span className="text-[11px] text-slate-500 block mt-0.5">Target features flagged</span>
          </div>

          <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
            <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
              Latest Screening
            </span>
            <span className="text-xs font-semibold text-slate-800 block mt-2 truncate">
              {stats.lastScreening ? formatDateTime(stats.lastScreening) : 'None'}
            </span>
            <span className="text-[11px] text-slate-400 block mt-0.5">Most recent activity</span>
          </div>
        </div>
      )}

      {/* Control Bar: Search & Category Filter Pills */}
      <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        {/* Search Input */}
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by filename or ID..."
            className="w-full pl-9 pr-4 py-2 text-sm bg-white border border-slate-200 rounded-xl text-slate-800 placeholder-slate-400 focus:outline-none focus:border-emerald-500 shadow-xs"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Category Pills & Clear Action */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="inline-flex items-center p-1 rounded-xl bg-slate-100 border border-slate-200/80 text-xs">
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setSelectedCategory(cat)}
                className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
                  selectedCategory === cat
                    ? 'bg-white text-emerald-700 shadow-xs font-semibold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          {records.length > 0 && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              icon={Trash2}
              onClick={() => setShowClearModal(true)}
              className="text-rose-600 hover:text-rose-700 hover:bg-rose-50 ml-auto md:ml-0"
            >
              Clear All
            </Button>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      {/* 1. LOADING STATE */}
      {isLoading && (
        <Card>
          <CardContent className="py-16 text-center space-y-3">
            <RefreshCw className="w-8 h-8 text-emerald-600 animate-spin mx-auto" />
            <h3 className="text-base font-semibold text-slate-800">
              Loading Screening Records...
            </h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Connecting to local SQLite database and fetching archived examinations.
            </p>
          </CardContent>
        </Card>
      )}

      {/* 2. ERROR STATE */}
      {error && !isLoading && (
        <Card className="border-amber-200 bg-amber-50/40">
          <CardContent className="py-12 text-center space-y-4">
            <div className="w-12 h-12 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center mx-auto">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-base font-bold text-amber-950">
                Unable to Load Screening History
              </h3>
              <p className="text-xs text-amber-800 mt-1 max-w-md mx-auto">
                {error}
              </p>
            </div>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              icon={RefreshCw}
              onClick={loadHistory}
            >
              Retry Database Connection
            </Button>
          </CardContent>
        </Card>
      )}

      {/* 3. EMPTY STATE (when database has 0 records) */}
      {!isLoading && !error && records.length === 0 && (
        <Card>
          <CardContent className="py-14 sm:py-16 text-center">
            <div className="w-14 h-14 rounded-2xl bg-emerald-50 border border-emerald-200/80 text-emerald-600 flex items-center justify-center mx-auto mb-4 shadow-xs">
              <HistoryIcon className="w-7 h-7" />
            </div>
            <CardTitle as="h3" className="text-lg font-bold text-slate-800">
              No Screening Records in Archive
            </CardTitle>
            <CardDescription className="max-w-md mx-auto mt-1.5 text-xs sm:text-sm">
              Each time you evaluate a retinal fundus photograph on the Screening page, the examination metadata and model scores will be saved automatically to this local database.
            </CardDescription>
            <div className="mt-6">
              <Button
                to="/screening"
                variant="primary"
                size="md"
                icon={ArrowRight}
                iconPosition="right"
              >
                Start Your First Screening
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 4. SEARCH ZERO-MATCH STATE */}
      {!isLoading && !error && records.length > 0 && filteredRecords.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center space-y-3">
            <Search className="w-8 h-8 text-slate-400 mx-auto" />
            <h3 className="text-base font-semibold text-slate-800">
              No Matching Records
            </h3>
            <p className="text-xs text-slate-500">
              No evaluations found matching &quot;{searchQuery}&quot;. Try a different search term or clear the filter.
            </p>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => {
                setSearchQuery('');
                setSelectedCategory('All');
              }}
            >
              Reset Filters
            </Button>
          </CardContent>
        </Card>
      )}

      {/* 5. RECORDS TABLE */}
      {!isLoading && !error && filteredRecords.length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50/80 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
                  <th className="py-3 px-4">ID</th>
                  <th className="py-3 px-4">Screening Date</th>
                  <th className="py-3 px-4">Filename & Format</th>
                  <th className="py-3 px-4">Classified Outcome</th>
                  <th className="py-3 px-4">Model Score</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredRecords.map((record) => {
                  const isNormal = record.predicted_category === 'Normal';
                  const isDeleting = deletingId === record.id;

                  return (
                    <tr
                      key={record.id}
                      onClick={() => handleInspect(record)}
                      className="hover:bg-slate-50/70 cursor-pointer transition-colors"
                    >
                      {/* ID */}
                      <td className="py-3.5 px-4 font-mono font-semibold text-slate-500">
                        #{record.id}
                      </td>

                      {/* Date & Time */}
                      <td className="py-3.5 px-4">
                        <span className="font-medium text-slate-800 block">
                          {formatDateTime(record.created_at)}
                        </span>
                        <span className="text-[10px] text-slate-400 block mt-0.5 flex items-center gap-1">
                          <Clock className="w-2.5 h-2.5" /> UTC Timestamp
                        </span>
                      </td>

                      {/* Filename & Dimensions */}
                      <td className="py-3.5 px-4 max-w-[200px]">
                        <span className="font-semibold text-slate-900 truncate block" title={record.filename}>
                          {record.filename}
                        </span>
                        <span className="text-[10px] text-slate-400 block mt-0.5">
                          {record.dimensions} px • {record.image_format} • {formatFileSize(record.file_size_bytes)}
                        </span>
                      </td>

                      {/* Classified Condition */}
                      <td className="py-3.5 px-4">
                        <Badge
                          variant={isNormal ? 'emerald' : 'amber'}
                          size="sm"
                          icon={isNormal ? CheckCircle2 : AlertTriangle}
                        >
                          {record.predicted_category}
                        </Badge>
                      </td>

                      {/* Model Score */}
                      <td className="py-3.5 px-4 min-w-[130px]">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-mono font-bold text-slate-800">
                            {(record.confidence_score * 100).toFixed(2)}%
                          </span>
                        </div>
                        <div className="w-24 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-1.5 rounded-full ${
                              isNormal ? 'bg-emerald-600' : 'bg-emerald-500'
                            }`}
                            style={{ width: `${Math.min(100, record.confidence_score * 100)}%` }}
                          />
                        </div>
                      </td>

                      {/* Actions */}
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleInspect(record);
                            }}
                            className="p-1.5 text-slate-500 hover:text-emerald-700 hover:bg-emerald-50 rounded-lg transition-colors"
                            title="Inspect Score Distribution"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            type="button"
                            disabled={isDeleting}
                            onClick={(e) => handleDeleteRecord(record.id, e)}
                            className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors disabled:opacity-50"
                            title="Delete Record"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Educational & Local Storage Notice */}
      <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 space-y-2">
        <div className="flex items-start gap-2.5">
          <Database className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            <strong>Local Storage Privacy:</strong> All screening records are persisted locally inside the project&apos;s SQLite database (<code>backend/data/visioncare.db</code>). For strict privacy and minimal storage usage, raw fundus image files are analyzed in-memory and are never stored on disk or embedded as database blobs.
          </p>
        </div>
        <div className="flex items-start gap-2.5 pt-2 border-t border-slate-200/70">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <p className="leading-relaxed text-slate-500">
            <strong>Clinical Disclaimer:</strong> Model scores reflect deep convolutional feature similarities across the four trained categories. They do not constitute calibrated clinical probabilities or certified medical diagnoses.
          </p>
        </div>
      </div>

      {/* INSPECT RECORD MODAL */}
      {inspectRecord && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full border border-slate-200 shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-5 border-b border-slate-100 bg-slate-50/60">
              <div className="flex items-center gap-2">
                <Badge variant="emerald" size="sm">
                  Record #{inspectRecord.id}
                </Badge>
                <span className="text-xs text-slate-400">•</span>
                <span className="text-xs text-slate-500 font-medium">Archived Evaluation</span>
              </div>
              <button
                type="button"
                onClick={() => setInspectRecord(null)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 space-y-5">
              {/* Primary Classified Banner */}
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/90 flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                    Classified Condition
                  </span>
                  <h3 className="text-xl font-bold text-slate-900 mt-0.5">
                    {inspectRecord.predicted_category}
                  </h3>
                </div>
                <div className="text-right">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                    Model Score
                  </span>
                  <span className="text-xl font-mono font-bold text-emerald-700 mt-0.5 block">
                    {(inspectRecord.confidence_score * 100).toFixed(2)}%
                  </span>
                </div>
              </div>

              {/* Four Category Score Distribution Breakdown */}
              <div className="space-y-2.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-800 flex items-center gap-1.5">
                    <SlidersHorizontal className="w-3.5 h-3.5 text-emerald-600" />
                    Four-Category Feature Score Distribution
                  </span>
                  <span className="text-[10px] text-slate-400">Canonical Order</span>
                </div>

                <div className="space-y-2 p-3.5 rounded-xl bg-white border border-slate-200">
                  {CATEGORY_ORDER.map((category) => {
                    const score = inspectRecord.scores?.[category] ?? 0;
                    const percentage = (score * 100).toFixed(2);
                    const isTop = category === inspectRecord.predicted_category;

                    return (
                      <div key={category} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className={`font-medium ${isTop ? 'text-slate-900 font-bold' : 'text-slate-600'}`}>
                            {category}
                            {isTop && (
                              <span className="ml-1.5 text-[9px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                                Primary Match
                              </span>
                            )}
                          </span>
                          <span className={`font-mono text-xs ${isTop ? 'font-bold text-emerald-700' : 'text-slate-600'}`}>
                            {percentage}%
                          </span>
                        </div>
                        <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-1.5 rounded-full transition-all duration-300 ${
                              isTop ? 'bg-emerald-600' : 'bg-slate-300'
                            }`}
                            style={{ width: `${Math.min(100, Math.max(0, parseFloat(percentage)))}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Image Metadata Details */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80">
                  <span className="text-[10px] uppercase font-semibold text-slate-400 block">Filename</span>
                  <span className="font-semibold text-slate-800 truncate block mt-0.5" title={inspectRecord.filename}>
                    {inspectRecord.filename}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80">
                  <span className="text-[10px] uppercase font-semibold text-slate-400 block">Resolution</span>
                  <span className="font-semibold text-slate-800 truncate block mt-0.5">
                    {inspectRecord.dimensions} px
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80">
                  <span className="text-[10px] uppercase font-semibold text-slate-400 block">Format & Size</span>
                  <span className="font-semibold text-slate-800 truncate block mt-0.5">
                    {inspectRecord.image_format} • {formatFileSize(inspectRecord.file_size_bytes)}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80">
                  <span className="text-[10px] uppercase font-semibold text-slate-400 block">Screening Timestamp</span>
                  <span className="font-semibold text-slate-800 truncate block mt-0.5">
                    {formatDateTime(inspectRecord.created_at)}
                  </span>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-100 bg-slate-50/60 flex items-center justify-between">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                icon={Trash2}
                onClick={(e) => handleDeleteRecord(inspectRecord.id, e)}
                className="text-rose-600 hover:text-rose-700 hover:bg-rose-50"
              >
                Delete Record
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => setInspectRecord(null)}
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* CLEAR ALL CONFIRMATION DIALOG */}
      {showClearModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full border border-slate-200 shadow-xl p-6 space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="w-12 h-12 rounded-full bg-rose-50 text-rose-600 flex items-center justify-center mx-auto">
              <AlertTriangle className="w-6 h-6" />
            </div>

            <div className="text-center space-y-1">
              <h3 className="text-lg font-bold text-slate-900">
                Clear All Screening History?
              </h3>
              <p className="text-xs text-slate-600 max-w-xs mx-auto">
                Are you sure you want to permanently delete all {totalCount} archived records from the local SQLite database? This action cannot be undone.
              </p>
            </div>

            <div className="flex items-center justify-center gap-3 pt-2">
              <Button
                type="button"
                variant="secondary"
                size="md"
                disabled={isClearing}
                onClick={() => setShowClearModal(false)}
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="primary"
                size="md"
                icon={Trash2}
                disabled={isClearing}
                onClick={handleClearAll}
                className="bg-rose-600 hover:bg-rose-700 text-white"
              >
                {isClearing ? 'Clearing Records...' : 'Yes, Clear All History'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
