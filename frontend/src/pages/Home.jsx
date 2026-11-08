import React from 'react';
import { ArrowRight, Eye, CheckCircle2, ShieldAlert, UploadCloud, Activity, FileCheck2 } from 'lucide-react';
import Button from '../components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import Badge from '../components/ui/Badge';

export default function Home() {
  const targetConditions = [
    {
      title: 'Cataract',
      description: 'Detection of lens opacification and progressive clouding affecting fundus visibility.',
      badge: 'Pathology',
    },
    {
      title: 'Diabetic Retinopathy',
      description: 'Identification of microaneurysms, retinal hemorrhages, and vascular lesions.',
      badge: 'Pathology',
    },
    {
      title: 'Glaucoma',
      description: 'Assessment of optic nerve head cupping and neuroretinal rim changes.',
      badge: 'Pathology',
    },
    {
      title: 'Normal',
      description: 'Clear optic disc margins, healthy macula, and typical vascular architecture.',
      badge: 'Baseline',
    },
  ];

  const workflowSteps = [
    {
      step: '1',
      title: 'Upload retinal image',
      desc: 'Select or drag a digital color fundus photograph (JPG or PNG format, up to 10 MB).',
      icon: UploadCloud,
    },
    {
      step: '2',
      title: 'Complete image screening',
      desc: 'Preprocessed through standardized convolutional neural feature analysis.',
      icon: Activity,
    },
    {
      step: '3',
      title: 'Review screening results',
      desc: 'Access categorized classification indicators and comprehensive visual summary.',
      icon: FileCheck2,
    },
  ];

  return (
    <div className="space-y-14 sm:space-y-18">
      {/* Hero Section */}
      <section className="text-center max-w-3xl mx-auto pt-6 sm:pt-10 space-y-6">
        <div className="inline-flex items-center gap-2">
          <Badge variant="emerald" size="md" icon={Eye}>
            Digital Ophthalmic Screening
          </Badge>
        </div>

        <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 tracking-tight leading-tight">
          Your Eye Health Matters
        </h1>

        <p className="text-base sm:text-lg text-slate-600 leading-relaxed max-w-2xl mx-auto">
          A simple way to screen retinal images and explore preliminary eye health results.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
          <Button
            to="/screening"
            size="lg"
            variant="primary"
            icon={ArrowRight}
            iconPosition="right"
            className="w-full sm:w-auto"
          >
            Start Screening
          </Button>
          <Button
            to="/history"
            size="lg"
            variant="secondary"
            className="w-full sm:w-auto"
          >
            Screening History
          </Button>
        </div>
      </section>

      {/* Target Categories Section */}
      <section className="space-y-6 max-w-5xl mx-auto">
        <div className="text-center space-y-2">
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Supported Screening Categories
          </h2>
          <p className="text-sm text-slate-500 max-w-xl mx-auto">
            VisionCare evaluates digital fundus photography for key diagnostic indicators across four categories.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
          {targetConditions.map((condition) => (
            <Card key={condition.title} className="flex flex-col justify-between">
              <CardHeader>
                <div className="flex items-center justify-between mb-2">
                  <Badge
                    variant={condition.badge === 'Baseline' ? 'emerald' : 'slate'}
                    size="sm"
                  >
                    {condition.badge}
                  </Badge>
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                </div>
                <CardTitle as="h3">{condition.title}</CardTitle>
                <CardDescription>{condition.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-xs text-slate-400 border-t border-slate-100 pt-3">
                  Categorized evaluation
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Three-step Explanation Section */}
      <section className="space-y-6 max-w-5xl mx-auto">
        <div className="text-center space-y-2">
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            How VisionCare Works
          </h2>
          <p className="text-sm text-slate-500 max-w-xl mx-auto">
            Three simple steps for digital retinal screening and assessment.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {workflowSteps.map((item) => {
            const Icon = item.icon;
            return (
              <Card key={item.step} className="relative overflow-hidden">
                <CardHeader>
                  <div className="flex items-center justify-between mb-4">
                    <span className="w-8 h-8 rounded-full bg-emerald-50 text-emerald-700 font-bold text-sm flex items-center justify-center border border-emerald-200/80">
                      {item.step}
                    </span>
                    <div className="w-9 h-9 rounded-xl bg-slate-50 text-slate-700 flex items-center justify-center border border-slate-200/70">
                      <Icon className="w-4 h-4" />
                    </div>
                  </div>
                  <CardTitle as="h3">{item.title}</CardTitle>
                  <CardDescription className="pt-1">{item.desc}</CardDescription>
                </CardHeader>
              </Card>
            );
          })}
        </div>
      </section>

      {/* Medical Disclaimer Banner */}
      <section className="max-w-4xl mx-auto">
        <Card className="bg-slate-50/80 border-slate-200">
          <CardContent className="py-4 sm:py-5 flex items-start gap-3.5">
            <ShieldAlert className="w-5 h-5 text-emerald-700 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-900">
                Medical Disclaimer
              </h4>
              <p className="text-xs text-slate-600 leading-relaxed">
                VisionCare is designed for educational screening and decision-support purposes only. Automated preliminary results are not a substitute for professional medical diagnosis, comprehensive dilated eye examinations, or physician judgment. Always consult a licensed optometrist or ophthalmologist for clinical evaluation.
              </p>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
