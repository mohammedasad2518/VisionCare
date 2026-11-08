import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  UploadCloud,
  ImageIcon,
  Trash2,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  ShieldCheck,
  Info,
  Activity,
  ArrowRight,
  Loader2,
  RotateCcw,
  AlertTriangle,
  Eye,
  SlidersHorizontal,
  Layers,
} from 'lucide-react';
import Button from '../components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import { checkHealth, predictImage, generateGradCAM, ApiError } from '../services/api';

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB
const ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png'];
const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png'];
const CATEGORY_ORDER = ['Cataract', 'Diabetic Retinopathy', 'Glaucoma', 'Normal'];

export default function Screening() {
  // Upload and file state
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [imageDimensions, setImageDimensions] = useState(null);
  const [validationError, setValidationError] = useState('');
  const [isDragging, setIsDragging] = useState(false);

  // Screening request state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [screeningResult, setScreeningResult] = useState(null);
  const [apiError, setApiError] = useState('');

  // Grad-CAM visualization state
  const [gradcamResult, setGradcamResult] = useState(null);
  const [isGeneratingGradcam, setIsGeneratingGradcam] = useState(false);
  const [gradcamError, setGradcamError] = useState('');
  const [visualViewMode, setVisualViewMode] = useState('overlay'); // 'overlay' | 'sideBySide' | 'heatmap' | 'original'
  const [overlayOpacity, setOverlayOpacity] = useState(85); // percentage for blended viewer

  // Service health state
  const [healthStatus, setHealthStatus] = useState('checking'); // 'checking' | 'available' | 'unavailable'
  const [healthInfo, setHealthInfo] = useState(null);

  const fileInputRef = useRef(null);

  // Format bytes into readable string
  const formatFileSize = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  // Format ISO timestamp into clean clinical presentation
  const formatDateTime = (isoString) => {
    if (!isoString) return 'Just now';
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

  // Clean up object URLs to avoid memory leaks
  const cleanupPreview = useCallback((url) => {
    if (url) {
      URL.revokeObjectURL(url);
    }
  }, []);

  // Check health on mount and provide manual refresh
  const verifyServiceHealth = useCallback(() => {
    setHealthStatus('checking');
    checkHealth()
      .then((data) => {
        setHealthInfo(data);
        setHealthStatus(data.available ? 'available' : 'unavailable');
      })
      .catch(() => {
        setHealthStatus('unavailable');
      });
  }, []);

  useEffect(() => {
    let isMounted = true;
    checkHealth()
      .then((data) => {
        if (!isMounted) return;
        setHealthInfo(data);
        setHealthStatus(data.available ? 'available' : 'unavailable');
      })
      .catch(() => {
        if (isMounted) {
          setHealthStatus('unavailable');
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // Cleanup preview URL on unmount
  useEffect(() => {
    return () => {
      cleanupPreview(previewUrl);
    };
  }, [previewUrl, cleanupPreview]);

  // Validate and process selected image file
  const processFile = (file) => {
    setValidationError('');
    setApiError('');
    setScreeningResult(null);
    setGradcamResult(null);
    setGradcamError('');

    if (!file) return;

    // Check empty file
    if (file.size === 0) {
      setValidationError('The selected file is empty (0 bytes). Please provide a valid retinal photograph.');
      return;
    }

    // Check file extension and MIME type
    const extension = file.name.split('.').pop()?.toLowerCase() || '';
    const hasValidExtension = ALLOWED_EXTENSIONS.includes(extension);
    const hasValidMime = ALLOWED_MIME_TYPES.includes(file.type);

    if (!hasValidExtension && !hasValidMime) {
      setValidationError(
        `Unsupported file format ".${extension}". Please upload a digital fundus photograph in JPG, JPEG, or PNG format.`
      );
      return;
    }

    // Check file size (<= 10MB)
    if (file.size > MAX_FILE_SIZE_BYTES) {
      setValidationError(
        `File size (${formatFileSize(file.size)}) exceeds the maximum limit of 10 MB. Please select a smaller image.`
      );
      return;
    }

    // Revoke previous URL if any
    cleanupPreview(previewUrl);

    // Create new preview URL and verify image readability
    const newUrl = URL.createObjectURL(file);
    const img = new Image();

    img.onload = () => {
      setSelectedFile(file);
      setPreviewUrl(newUrl);
      setImageDimensions({
        width: img.naturalWidth,
        height: img.naturalHeight,
      });
      setValidationError('');
    };

    img.onerror = () => {
      cleanupPreview(newUrl);
      setValidationError('The selected file is corrupted or could not be decoded as an image. Please choose a valid image file.');
      setSelectedFile(null);
      setPreviewUrl(null);
      setImageDimensions(null);
    };

    img.src = newUrl;
  };

  // Handle standard input change
  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      processFile(file);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Drag and Drop handlers
  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const file = e.dataTransfer.files?.[0];
    if (file) {
      processFile(file);
    }
  };

  // Trigger file browser
  const openFileBrowser = () => {
    fileInputRef.current?.click();
  };

  // Remove current image
  const handleRemoveImage = () => {
    cleanupPreview(previewUrl);
    setSelectedFile(null);
    setPreviewUrl(null);
    setImageDimensions(null);
    setValidationError('');
    setApiError('');
    setScreeningResult(null);
    setGradcamResult(null);
    setGradcamError('');
    setIsGeneratingGradcam(false);
    setVisualViewMode('overlay');
  };

  // Reset entire screening workflow to evaluate another image
  const handleResetScreening = () => {
    handleRemoveImage();
    verifyServiceHealth();
  };

  // Request Grad-CAM visualization safely without disturbing prediction
  const loadGradCAM = async (fileToProcess, targetClass = null) => {
    const file = fileToProcess || selectedFile;
    if (!file || isGeneratingGradcam) return;

    setIsGeneratingGradcam(true);
    setGradcamError('');

    try {
      let classIdx = null;
      if (targetClass) {
        const foundIdx = CATEGORY_ORDER.indexOf(targetClass);
        if (foundIdx !== -1) classIdx = foundIdx;
      }
      const data = await generateGradCAM(file, classIdx);
      setGradcamResult(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setGradcamError(err.message);
      } else {
        setGradcamError('Unable to generate visual explanation. The primary screening result remains valid.');
      }
    } finally {
      setIsGeneratingGradcam(false);
    }
  };

  // Execute genuine image screening via backend API
  const handleStartScreening = async () => {
    if (!selectedFile || isSubmitting) return;

    setApiError('');
    setIsSubmitting(true);
    setGradcamResult(null);
    setGradcamError('');

    try {
      const result = await predictImage(selectedFile);
      result.timestamp = new Date().toISOString();
      setScreeningResult(result);
      // Initiate Grad-CAM visual explanation generation after genuine prediction is set
      loadGradCAM(selectedFile, result.prediction);
    } catch (err) {
      if (err instanceof ApiError) {
        setApiError(err.message);
      } else {
        setApiError('An unexpected network error occurred while communicating with the screening service.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".jpg,.jpeg,.png,image/jpeg,image/png"
        className="hidden"
      />

      {/* Page Heading */}
      <div className="border-b border-slate-200/80 pb-5">
        <div className="flex items-center gap-2 mb-2">
          <Badge variant="emerald" size="sm" icon={Activity}>
            Screening Workspace
          </Badge>
          <span className="text-xs text-slate-400">•</span>
          <span className="text-xs text-slate-500 font-medium">Fundus Photography Protocol</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
          Eye Disease Screening
        </h1>
        <p className="text-sm sm:text-base text-slate-600 mt-1 max-w-3xl">
          Upload a digital retinal fundus photograph to initiate deep learning feature evaluation across four target eye health categories.
        </p>
      </div>

      {/* Validation Error Banner */}
      {validationError && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 flex items-start gap-3 text-sm text-rose-800">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-semibold block">Validation Error</span>
            <span className="text-xs sm:text-sm text-rose-700">{validationError}</span>
          </div>
          <button
            onClick={() => setValidationError('')}
            className="text-xs text-rose-600 hover:text-rose-800 font-semibold"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Backend API Error Banner */}
      {apiError && (
        <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 flex items-start gap-3 text-sm text-amber-900">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-semibold block">Screening Service Notice</span>
            <span className="text-xs sm:text-sm text-amber-800">{apiError}</span>
          </div>
          <button
            onClick={() => setApiError('')}
            className="text-xs text-amber-700 hover:text-amber-900 font-semibold"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Upload, Preview, or Results Card */}
        <div className="lg:col-span-2 space-y-6">
          {/* STATE 1: No file selected -> Upload Card */}
          {!selectedFile && (
            <Card>
              <CardHeader>
                <CardTitle as="h2">Upload Retinal Image</CardTitle>
                <CardDescription>
                  Supported formats: JPG, JPEG, PNG. Maximum file size: 10 MB.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div
                  onDragEnter={handleDragEnter}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={openFileBrowser}
                  className={`border-2 border-dashed rounded-xl p-8 sm:p-12 text-center cursor-pointer transition-all ${
                    isDragging
                      ? 'border-emerald-600 bg-emerald-50/50 scale-[0.99]'
                      : 'border-slate-300 hover:border-emerald-500 hover:bg-slate-50/70 bg-slate-50/30'
                  }`}
                >
                  <div className="flex flex-col items-center justify-center space-y-4">
                    <div className="w-14 h-14 rounded-full bg-emerald-50 border border-emerald-200/80 flex items-center justify-center text-emerald-600 shadow-sm">
                      <UploadCloud className="w-7 h-7" />
                    </div>

                    <div className="space-y-1">
                      <p className="text-sm sm:text-base font-semibold text-slate-800">
                        Drag and drop your retinal image here
                      </p>
                      <p className="text-xs sm:text-sm text-slate-500">
                        or click anywhere in this area to browse your files
                      </p>
                    </div>

                    <div className="pt-2">
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        icon={ImageIcon}
                        onClick={(e) => {
                          e.stopPropagation();
                          openFileBrowser();
                        }}
                      >
                        Choose File
                      </Button>
                    </div>

                    <div className="flex items-center gap-4 text-[11px] text-slate-400 pt-2 border-t border-slate-200/60">
                      <span>• JPG / JPEG / PNG</span>
                      <span>• Up to 10 MB</span>
                      <span>• Fundus photography</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* STATE 2: File selected, not yet submitted -> Staging / Inspection Card */}
          {selectedFile && !screeningResult && (
            <Card>
              <CardHeader className="border-b border-slate-100 pb-4">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle as="h2">Staged Retinal Photograph</CardTitle>
                    <CardDescription>
                      Review the image preview and metadata before starting evaluation.
                    </CardDescription>
                  </div>
                  <Badge variant="emerald" size="sm">
                    Ready for Screening
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-5 pt-5">
                {/* Image Preview Container */}
                <div className="relative rounded-xl border border-slate-200 bg-slate-900 overflow-hidden flex items-center justify-center min-h-[280px] max-h-[420px] p-2">
                  <img
                    src={previewUrl}
                    alt="Retinal photograph preview"
                    className="max-h-[380px] w-auto max-w-full object-contain rounded-lg"
                  />
                  {isSubmitting && (
                    <div className="absolute inset-0 bg-slate-900/75 backdrop-blur-sm flex flex-col items-center justify-center text-white space-y-3 p-4">
                      <Loader2 className="w-8 h-8 animate-spin text-emerald-400" />
                      <span className="text-sm font-semibold tracking-wide">
                        Evaluating Retinal Photography...
                      </span>
                      <span className="text-xs text-slate-300 text-center max-w-xs">
                        Extracting optic disc, vascular, and macular features using the VGG19 screening model.
                      </span>
                    </div>
                  )}
                </div>

                {/* File Metadata Details Bar */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-4 rounded-xl bg-slate-50 border border-slate-200/90 text-xs">
                  <div>
                    <span className="text-slate-400 block uppercase tracking-wider text-[10px] font-semibold">
                      Filename
                    </span>
                    <span className="font-semibold text-slate-800 truncate block mt-0.5" title={selectedFile.name}>
                      {selectedFile.name}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block uppercase tracking-wider text-[10px] font-semibold">
                      Dimensions
                    </span>
                    <span className="font-semibold text-slate-800 block mt-0.5">
                      {imageDimensions ? `${imageDimensions.width} × ${imageDimensions.height} px` : 'Calculating...'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block uppercase tracking-wider text-[10px] font-semibold">
                      File Size
                    </span>
                    <span className="font-semibold text-slate-800 block mt-0.5">
                      {formatFileSize(selectedFile.size)}
                    </span>
                  </div>
                </div>

                {/* Action Controls */}
                <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
                  <div className="flex items-center gap-2 w-full sm:w-auto">
                    <Button
                      type="button"
                      variant="secondary"
                      size="md"
                      icon={RefreshCw}
                      disabled={isSubmitting}
                      onClick={openFileBrowser}
                      className="flex-1 sm:flex-none"
                    >
                      Replace Image
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="md"
                      icon={Trash2}
                      disabled={isSubmitting}
                      onClick={handleRemoveImage}
                      className="text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                    >
                      Remove
                    </Button>
                  </div>

                  {/* Primary Start Screening Button */}
                  <Button
                    type="button"
                    variant="primary"
                    size="lg"
                    icon={isSubmitting ? Loader2 : ArrowRight}
                    iconPosition={isSubmitting ? 'left' : 'right'}
                    disabled={isSubmitting || healthStatus === 'unavailable'}
                    onClick={handleStartScreening}
                    className="w-full sm:w-auto"
                  >
                    {isSubmitting ? 'Processing Screening...' : 'Start Screening'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* STATE 3: Screening Complete -> Prediction Results Interface Card */}
          {screeningResult && (
            <Card className="border-emerald-200/90 shadow-md">
              <CardHeader className="border-b border-slate-100 pb-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <Badge
                        variant={screeningResult.prediction === 'Normal' ? 'emerald' : 'amber'}
                        size="sm"
                        icon={screeningResult.prediction === 'Normal' ? CheckCircle2 : AlertTriangle}
                      >
                        {screeningResult.prediction === 'Normal' ? 'Screening Negative' : 'Pathology Pattern Detected'}
                      </Badge>
                      <span className="text-xs text-slate-400">•</span>
                      <span className="text-xs text-slate-500 font-medium">Model Output Assessment</span>
                    </div>
                    <CardTitle as="h2" className="text-xl sm:text-2xl font-bold text-slate-900">
                      Screening Results
                    </CardTitle>
                    <CardDescription>
                      Automated classification based on VGG19 deep feature analysis.
                    </CardDescription>
                  </div>

                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    icon={RotateCcw}
                    onClick={handleResetScreening}
                  >
                    Screen Another Image
                  </Button>
                </div>
              </CardHeader>

              <CardContent className="space-y-6 pt-5">
                {/* Examination Metadata Bar */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 rounded-xl bg-slate-50 border border-slate-200/90 text-xs">
                  <div>
                    <span className="text-slate-400 block uppercase tracking-wider text-[10px] font-semibold">
                      Uploaded Filename
                    </span>
                    <span
                      className="font-semibold text-slate-800 truncate block mt-0.5"
                      title={screeningResult.image?.filename || selectedFile?.name}
                    >
                      {screeningResult.image?.filename || selectedFile?.name}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block uppercase tracking-wider text-[10px] font-semibold">
                      Screening Timestamp
                    </span>
                    <span className="font-semibold text-slate-800 block mt-0.5">
                      {formatDateTime(screeningResult.timestamp)}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block uppercase tracking-wider text-[10px] font-semibold">
                      Image Attributes
                    </span>
                    <span className="font-semibold text-slate-800 block mt-0.5">
                      {imageDimensions ? `${imageDimensions.width} × ${imageDimensions.height} px` : '224 × 224 px'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block uppercase tracking-wider text-[10px] font-semibold">
                      Archive Reference
                    </span>
                    <span className="font-semibold text-emerald-700 block mt-0.5">
                      {screeningResult.screeningId ? `Record #${screeningResult.screeningId}` : 'Persisted in History'}
                    </span>
                  </div>
                </div>

                {/* Result Overview Grid: Image Preview + Primary Prediction */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  {/* Left: Evaluated Image Thumbnail */}
                  <div className="rounded-xl border border-slate-200 bg-slate-900 p-2 flex items-center justify-center">
                    <img
                      src={previewUrl}
                      alt="Evaluated retinal photograph"
                      className="max-h-[260px] w-auto max-w-full object-contain rounded-lg"
                    />
                  </div>

                  {/* Right: Primary Outcome Banner */}
                  <div className="flex flex-col justify-between space-y-4 p-5 rounded-xl bg-slate-50/80 border border-slate-200">
                    <div>
                      <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 block mb-1">
                        Primary Classified Category
                      </span>
                      <h3 className="text-2xl font-bold text-slate-900 tracking-tight">
                        {screeningResult.prediction}
                      </h3>
                      <p className="text-xs text-slate-600 mt-1">
                        {screeningResult.prediction === 'Normal'
                          ? 'No definitive structural signs of cataract, diabetic retinopathy, or glaucoma were identified.'
                          : `Retinal patterns align predominantly with hallmarks of ${screeningResult.prediction.toLowerCase()}.`}
                      </p>
                    </div>

                    <div className="pt-3 border-t border-slate-200/80">
                      <div className="flex items-center justify-between text-xs mb-1.5">
                        <span className="text-slate-600 font-medium">Model Score</span>
                        <span className="font-bold text-slate-900">
                          {(screeningResult.confidence * 100).toFixed(2)}%
                        </span>
                      </div>
                      <div className="w-full bg-slate-200 rounded-full h-2.5 overflow-hidden">
                        <div
                          className={`h-2.5 rounded-full transition-all duration-500 ${
                            screeningResult.prediction === 'Normal' ? 'bg-emerald-600' : 'bg-emerald-500'
                          }`}
                          style={{ width: `${Math.min(100, Math.max(0, screeningResult.confidence * 100))}%` }}
                        />
                      </div>
                      <span className="text-[11px] text-slate-400 block mt-1.5 italic">
                        Raw output score from the final softmax layer.
                      </span>
                    </div>
                  </div>
                </div>

                {/* Four Category Output Scores Breakdown */}
                <div className="space-y-3 pt-2">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-slate-900 flex items-center gap-1.5">
                      <SlidersHorizontal className="w-4 h-4 text-emerald-600" />
                      Model Scores Distribution Across All Categories
                    </h4>
                    <span className="text-[11px] text-slate-400 font-medium">Ordered by Protocol</span>
                  </div>

                  <div className="space-y-2.5 p-4 rounded-xl bg-white border border-slate-200">
                    {CATEGORY_ORDER.map((category) => {
                      const score = screeningResult.scores?.[category] ?? screeningResult.probabilities?.[category] ?? 0;
                      const percentage = (score * 100).toFixed(2);
                      const isTop = category === screeningResult.prediction;

                      return (
                        <div key={category} className="space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className={`font-medium ${isTop ? 'text-slate-900 font-semibold' : 'text-slate-600'}`}>
                              {category}
                              {isTop && (
                                <span className="ml-2 text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                                  Top Match
                                </span>
                              )}
                            </span>
                            <span className={`font-mono text-xs ${isTop ? 'font-bold text-emerald-700' : 'text-slate-600'}`}>
                              {percentage}%
                            </span>
                          </div>
                          <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                            <div
                              className={`h-2 rounded-full transition-all duration-500 ${
                                isTop ? 'bg-emerald-600' : 'bg-slate-300'
                              }`}
                              style={{ width: `${Math.min(100, Math.max(0, parseFloat(percentage)))}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}

                    <p className="text-[11px] text-slate-500 pt-2 border-t border-slate-100 leading-relaxed">
                      <strong>Score Clarification:</strong> Output scores reflect relative feature similarity scores produced by the deep convolutional network across the 4 trained classes. They do not constitute calibrated clinical probabilities or epidemiological prevalence values.
                    </p>
                  </div>
                </div>

                {/* VISUAL EXPLANATION SECTION (Grad-CAM) */}
                <div className="space-y-4 pt-4 border-t border-slate-200/90">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="emerald" size="sm" icon={Layers}>
                          Interpretability Analysis
                        </Badge>
                        <span className="text-xs text-slate-400">•</span>
                        <span className="text-xs text-slate-500 font-medium">Layer: block5_conv4</span>
                      </div>
                      <h4 className="text-lg font-bold text-slate-900 tracking-tight">
                        Visual Explanation
                      </h4>
                    </div>

                    {/* View mode toggle buttons when Grad-CAM result is present */}
                    {gradcamResult && !isGeneratingGradcam && (
                      <div className="inline-flex items-center p-1 rounded-lg bg-slate-100 border border-slate-200/80 text-xs">
                        <button
                          type="button"
                          onClick={() => setVisualViewMode('overlay')}
                          className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                            visualViewMode === 'overlay'
                              ? 'bg-white text-emerald-700 shadow-sm font-semibold'
                              : 'text-slate-600 hover:text-slate-900'
                          }`}
                        >
                          Overlay
                        </button>
                        <button
                          type="button"
                          onClick={() => setVisualViewMode('sideBySide')}
                          className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                            visualViewMode === 'sideBySide'
                              ? 'bg-white text-emerald-700 shadow-sm font-semibold'
                              : 'text-slate-600 hover:text-slate-900'
                          }`}
                        >
                          Side-by-Side
                        </button>
                        <button
                          type="button"
                          onClick={() => setVisualViewMode('heatmap')}
                          className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                            visualViewMode === 'heatmap'
                              ? 'bg-white text-emerald-700 shadow-sm font-semibold'
                              : 'text-slate-600 hover:text-slate-900'
                          }`}
                        >
                          Heatmap
                        </button>
                        <button
                          type="button"
                          onClick={() => setVisualViewMode('original')}
                          className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                            visualViewMode === 'original'
                              ? 'bg-white text-emerald-700 shadow-sm font-semibold'
                              : 'text-slate-600 hover:text-slate-900'
                          }`}
                        >
                          Original Photo
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Mandatory Clinical & Interpretability Disclaimer */}
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/90 text-xs text-slate-700 flex items-start gap-2.5">
                    <Info className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    <p className="leading-relaxed">
                      The highlighted regions represent image areas that contributed to the model&apos;s classification. They are not a medical diagnosis or a confirmed disease location.
                    </p>
                  </div>

                  {/* Loading State for Grad-CAM */}
                  {isGeneratingGradcam && (
                    <div className="p-8 rounded-xl border border-dashed border-emerald-300 bg-emerald-50/40 flex flex-col items-center justify-center text-center space-y-3">
                      <Loader2 className="w-7 h-7 text-emerald-600 animate-spin" />
                      <div>
                        <span className="text-sm font-semibold text-slate-800 block">
                          Generating Visual Explanation...
                        </span>
                        <span className="text-xs text-slate-500 max-w-md block mt-1">
                          Computing gradient-weighted class activation map (Grad-CAM) from layer block5_conv4 for category {screeningResult.prediction}.
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Error State for Grad-CAM (Preserves Screening Prediction) */}
                  {gradcamError && !isGeneratingGradcam && (
                    <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs text-amber-900">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                        <div>
                          <span className="font-semibold block">Visualization Unavailable</span>
                          <span className="text-amber-800">{gradcamError}</span>
                          <span className="text-slate-500 block mt-0.5 italic">
                            Your primary screening classification remains valid.
                          </span>
                        </div>
                      </div>
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        icon={RefreshCw}
                        onClick={() => loadGradCAM(selectedFile, screeningResult.prediction)}
                      >
                        Retry Visualization
                      </Button>
                    </div>
                  )}

                  {/* On-demand Trigger if Visualization was not yet initiated */}
                  {!gradcamResult && !isGeneratingGradcam && !gradcamError && (
                    <div className="p-6 rounded-xl border border-slate-200 bg-slate-50/70 text-center space-y-3">
                      <p className="text-xs text-slate-600 max-w-md mx-auto">
                        Explore gradient-weighted feature maps to inspect which fundus regions influenced the VGG19 classification for this image.
                      </p>
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        icon={Layers}
                        onClick={() => loadGradCAM(selectedFile, screeningResult.prediction)}
                      >
                        Load Visual Explanation
                      </Button>
                    </div>
                  )}

                  {/* Grad-CAM Results Visual Viewer */}
                  {gradcamResult && !isGeneratingGradcam && (
                    <div className="space-y-4">
                      {/* Viewer Display Container */}
                      <div className="rounded-xl border border-slate-200 bg-slate-900 p-3 flex flex-col items-center justify-center min-h-[300px]">
                        {/* 1. OVERLAY MODE */}
                        {visualViewMode === 'overlay' && (
                          <div className="relative flex flex-col items-center max-w-full">
                            <div className="relative inline-block overflow-hidden rounded-lg">
                              <img
                                src={gradcamResult.overlayDataUrl}
                                alt="Grad-CAM overlay on retinal fundus photograph"
                                className="max-h-[380px] w-auto max-w-full object-contain"
                                style={{ opacity: overlayOpacity / 100 }}
                              />
                            </div>
                            <span className="text-[11px] text-slate-400 mt-2 block">
                              Salience Overlay on Retinal Fundus Image
                            </span>
                          </div>
                        )}

                        {/* 2. SIDE-BY-SIDE MODE */}
                        {visualViewMode === 'sideBySide' && (
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full p-2">
                            <div className="flex flex-col items-center">
                              <div className="rounded-lg overflow-hidden border border-slate-800 bg-black flex items-center justify-center">
                                <img
                                  src={previewUrl}
                                  alt="Original retinal fundus photograph"
                                  className="max-h-[280px] w-auto object-contain"
                                />
                              </div>
                              <span className="text-[11px] text-slate-300 font-medium mt-2">
                                1. Original Photograph
                              </span>
                            </div>
                            <div className="flex flex-col items-center">
                              <div className="rounded-lg overflow-hidden border border-slate-800 bg-black flex items-center justify-center">
                                <img
                                  src={gradcamResult.overlayDataUrl}
                                  alt="Grad-CAM overlay"
                                  className="max-h-[280px] w-auto object-contain"
                                />
                              </div>
                              <span className="text-[11px] text-slate-300 font-medium mt-2">
                                2. Heatmap Overlay
                              </span>
                            </div>
                          </div>
                        )}

                        {/* 3. HEATMAP MODE */}
                        {visualViewMode === 'heatmap' && (
                          <div className="flex flex-col items-center max-w-full">
                            <div className="rounded-lg overflow-hidden border border-slate-800 bg-black flex items-center justify-center">
                              <img
                                src={gradcamResult.heatmapDataUrl}
                                alt="Pure Grad-CAM class activation heatmap"
                                className="max-h-[380px] w-auto max-w-full object-contain"
                              />
                            </div>
                            <span className="text-[11px] text-slate-400 mt-2 block">
                              Pure Activation Heatmap (Jet Colormap)
                            </span>
                          </div>
                        )}

                        {/* 4. ORIGINAL MODE */}
                        {visualViewMode === 'original' && (
                          <div className="flex flex-col items-center max-w-full">
                            <div className="rounded-lg overflow-hidden border border-slate-800 bg-black flex items-center justify-center">
                              <img
                                src={previewUrl}
                                alt="Original retinal fundus photograph"
                                className="max-h-[380px] w-auto max-w-full object-contain"
                              />
                            </div>
                            <span className="text-[11px] text-slate-400 mt-2 block">
                              Original Digital Fundus Photograph
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Interactive Opacity Control (When in Overlay mode) */}
                      {visualViewMode === 'overlay' && (
                        <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
                          <div className="flex items-center gap-2">
                            <SlidersHorizontal className="w-4 h-4 text-emerald-600" />
                            <span className="font-semibold text-slate-800">
                              Overlay Opacity:
                            </span>
                            <span className="font-mono text-emerald-700 font-bold">
                              {overlayOpacity}%
                            </span>
                          </div>
                          <div className="flex items-center gap-3 w-full sm:w-64">
                            <span className="text-[10px] text-slate-400">Soft</span>
                            <input
                              type="range"
                              min="20"
                              max="100"
                              value={overlayOpacity}
                              onChange={(e) => setOverlayOpacity(Number(e.target.value))}
                              className="w-full accent-emerald-600 h-1.5 bg-slate-200 rounded-lg cursor-pointer"
                            />
                            <span className="text-[10px] text-slate-400">Vivid</span>
                          </div>
                        </div>
                      )}

                      {/* Salience Colorbar & Legend */}
                      <div className="p-3 rounded-xl bg-white border border-slate-200 space-y-2">
                        <div className="flex items-center justify-between text-xs text-slate-600">
                          <span className="font-semibold flex items-center gap-1.5">
                            <Activity className="w-3.5 h-3.5 text-emerald-600" />
                            Activation Salience Scale
                          </span>
                          <span className="text-[11px] text-slate-400 font-mono">
                            Range: 0.0 – 1.0 (Normalized)
                          </span>
                        </div>

                        {/* Continuous Jet Colorbar */}
                        <div
                          className="w-full h-3 rounded-md shadow-inner border border-slate-200"
                          style={{
                            background: 'linear-gradient(to right, #000080, #0000ff, #00ffff, #00ff00, #ffff00, #ff0000, #800000)'
                          }}
                        />

                        <div className="flex items-center justify-between text-[10px] text-slate-500 font-medium">
                          <span>Low Feature Salience</span>
                          <span>Moderate Salience</span>
                          <span>Peak Model Focus</span>
                        </div>
                      </div>

                      {/* Technical Parameter Details */}
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                        <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80">
                          <span className="text-[10px] uppercase font-semibold text-slate-400 block">Target Layer</span>
                          <span className="font-semibold text-slate-800 truncate block mt-0.5">
                            {gradcamResult.targetLayer}
                          </span>
                        </div>
                        <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80">
                          <span className="text-[10px] uppercase font-semibold text-slate-400 block">Evaluated Class</span>
                          <span className="font-semibold text-slate-800 truncate block mt-0.5">
                            {gradcamResult.prediction}
                          </span>
                        </div>
                        <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80">
                          <span className="text-[10px] uppercase font-semibold text-slate-400 block">Resolution</span>
                          <span className="font-semibold text-slate-800 truncate block mt-0.5">
                            {gradcamResult.originalDimensions ? `${gradcamResult.originalDimensions[0]} × ${gradcamResult.originalDimensions[1]} px` : 'N/A'}
                          </span>
                        </div>
                        <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/80">
                          <span className="text-[10px] uppercase font-semibold text-slate-400 block">Interpolation</span>
                          <span className="font-semibold text-slate-800 truncate block mt-0.5">
                            Bicubic Resampling
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Educational Prototype & Clinical Disclaimer */}
                <div className="p-4 rounded-xl bg-amber-50/70 border border-amber-200/90 text-xs text-amber-900 space-y-2">
                  <div className="flex items-start gap-2.5">
                    <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold block text-amber-950">Educational Screening Notice</span>
                      <p className="text-amber-800 text-[11px] leading-relaxed mt-0.5">
                        This evaluation is provided by an educational screening prototype. This automated system does not confirm the presence of any eye condition nor does it rule out pathology.
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-2.5 pt-2 border-t border-amber-200/60">
                    <Eye className="w-4 h-4 text-emerald-700 shrink-0 mt-0.5" />
                    <p className="text-slate-700 text-[11px] leading-relaxed">
                      <strong>Recommendation:</strong> A comprehensive dilated examination by a certified ophthalmologist or optometrist remains the definitive standard for evaluating eye health, optic nerve structure, and retinal vascular condition.
                    </p>
                  </div>
                </div>

                {/* Reset Action */}
                <div className="pt-2 flex justify-end">
                  <Button
                    type="button"
                    variant="primary"
                    size="md"
                    icon={RotateCcw}
                    onClick={handleResetScreening}
                  >
                    Screen Another Retinal Image
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Column: Protocols, Guidelines & Model Specs */}
        <div className="space-y-6">
          {/* Service & Model Status Card */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle as="h3" className="text-base">
                  Service Readiness
                </CardTitle>
                <Badge
                  variant={
                    healthStatus === 'available'
                      ? 'emerald'
                      : healthStatus === 'checking'
                      ? 'gray'
                      : 'amber'
                  }
                  size="sm"
                >
                  {healthStatus === 'available'
                    ? 'Online'
                    : healthStatus === 'checking'
                    ? 'Checking...'
                    : 'Offline'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="flex items-center justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Service API</span>
                <span className="font-semibold text-slate-800">
                  {healthInfo?.appName || 'VisionCare API'}
                </span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Screening Architecture</span>
                <span className="font-semibold text-slate-800">
                  {healthInfo?.architecture || 'VGG19 (Transfer Learning)'}
                </span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-slate-100">
                <span className="text-slate-500">Model Weights</span>
                <span className={`font-semibold ${healthStatus === 'available' ? 'text-emerald-700' : 'text-amber-700'}`}>
                  {healthStatus === 'available' ? 'Verified & Loaded' : 'Unavailable'}
                </span>
              </div>
              <div className="flex items-center justify-between py-1">
                <span className="text-slate-500">Input Size</span>
                <span className="font-semibold text-slate-800 font-mono">224 × 224 × 3 RGB</span>
              </div>

              {healthStatus === 'unavailable' && (
                <div className="p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 mt-2">
                  <span className="font-semibold block mb-0.5">Notice:</span>
                  <span className="text-[11px] leading-relaxed block">
                    FastAPI backend or model weights are currently unavailable. Screening requests cannot proceed.
                  </span>
                  <button
                    onClick={verifyServiceHealth}
                    className="mt-2 text-xs font-semibold text-amber-700 hover:text-amber-900 flex items-center gap-1"
                  >
                    <RefreshCw className="w-3 h-3" /> Retry Connection
                  </button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Photography Protocol Guidelines */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle as="h3" className="text-base flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
                Photography Protocol
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-xs text-slate-600">
              <div className="space-y-1">
                <span className="font-semibold text-slate-800 block">1. Field of View</span>
                <p className="leading-relaxed">
                  Center the optic disc and macula within a standard 45° to 50° fundus photographic field.
                </p>
              </div>
              <div className="space-y-1 pt-1 border-t border-slate-100">
                <span className="font-semibold text-slate-800 block">2. Illumination & Focus</span>
                <p className="leading-relaxed">
                  Avoid uneven flash reflection, anterior segment flare, or severe motion artifacts.
                </p>
              </div>
              <div className="space-y-1 pt-1 border-t border-slate-100">
                <span className="font-semibold text-slate-800 block">3. Target Categories</span>
                <div className="grid grid-cols-2 gap-1.5 pt-1">
                  <div className="p-1.5 rounded bg-slate-50 border border-slate-200/70 font-medium text-slate-700">
                    Cataract
                  </div>
                  <div className="p-1.5 rounded bg-slate-50 border border-slate-200/70 font-medium text-slate-700">
                    Diabetic Retinopathy
                  </div>
                  <div className="p-1.5 rounded bg-slate-50 border border-slate-200/70 font-medium text-slate-700">
                    Glaucoma
                  </div>
                  <div className="p-1.5 rounded bg-slate-50 border border-slate-200/70 font-medium text-slate-700">
                    Normal
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
