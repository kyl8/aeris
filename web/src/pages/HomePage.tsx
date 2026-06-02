import { useCallback, useMemo, useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  AlertTriangle,
  BarChart3,
  BrainCircuit,
  Camera,
  CheckCircle2,
  Database,
  Download,
  FileText,
  Gauge,
  Image as ImageIcon,
  Layers3,
  LineChart,
  Pause,
  Play,
  RefreshCw,
  Satellite,
  ScanLine,
  Settings2,
  TableProperties,
  ThermometerSun,
} from 'lucide-react'

import { PageShell } from '../components/layout/PageShell'
import { LanguageSwitcher } from '../components/layout/LanguageSwitcher'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs'
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '../components/ui/table'
import { Badge } from '../components/ui/badge'
import { useHealth } from '../hooks/useHealth'
import { useHistory } from '../hooks/useHistory'
import { usePrediction } from '../hooks/usePrediction'
import { useResearch } from '../hooks/useResearch'
import {
  buildDistributionData,
  buildTimelineData,
  capitalizeLabel,
  formatConfidence,
  formatDateTime,
  summarizeHistory,
} from '../lib/dashboard'
import { docsUrls, detectClimate, predictClimate } from '../lib/api'

const CHART_COLORS = ['#8b5cf6', '#38bdf8', '#f97316', '#22c55e', '#ec4899', '#eab308']

function StatCard({ label, value, hint, tone = 'default' }) {
  return (
    <Card className="p-5 flex flex-col justify-between">
      <div>
        <p className="text-xs uppercase tracking-wider text-zinc-500 font-medium mb-1">{label}</p>
        <p className="text-3xl font-semibold tracking-tight text-zinc-50">{value}</p>
      </div>
      <div className="mt-4">
        <Badge variant={tone}>{hint}</Badge>
      </div>
    </Card>
  )
}

function EmptyState({ title, description, action }) {
  return (
    <div className="flex min-h-[200px] flex-col items-center justify-center rounded-xl border border-dashed border-zinc-800 bg-zinc-900/20 p-8 text-center">
      <h3 className="text-base font-medium text-zinc-200">{title}</h3>
      <p className="mt-2 mb-4 text-sm text-zinc-500 max-w-sm">{description}</p>
      {action}
    </div>
  )
}

function DistributionChart({ data, t }) {
  if (!data.length) return null

  const total = data.reduce((acc, item) => acc + item.value, 0) || 1
  const ringStops = data
    .reduce(
      (acc, entry, index) => {
        const slicePercent = (entry.value / total) * 100
        const start = acc.currentPercent
        const end = start + slicePercent
        return {
          currentPercent: end,
          stops: [...acc.stops, `${CHART_COLORS[index % CHART_COLORS.length]} ${start}% ${end}%`],
        }
      },
      { currentPercent: 0, stops: [] },
    )
    .stops.join(', ')

  return (
    <div className="flex flex-col md:flex-row items-center gap-12 py-4">
      <div
        className="relative flex h-64 w-64 items-center justify-center rounded-full"
        style={{ background: `conic-gradient(${ringStops})` }}
      >
        <div className="flex h-48 w-48 flex-col items-center justify-center rounded-full bg-zinc-950 text-center">
          <p className="text-xs uppercase tracking-wider text-zinc-500">{t('dashboard.distribution.total')}</p>
          <p className="text-4xl font-semibold text-zinc-100">{total}</p>
        </div>
      </div>

      <div className="flex-1 w-full space-y-4">
        {data.map((entry, index) => {
          const percent = ((entry.value / total) * 100).toFixed(0)
          return (
            <div key={entry.rawName} className="flex items-center gap-4">
              <div
                className="h-3 w-3 rounded-full shrink-0"
                style={{ backgroundColor: CHART_COLORS[index % CHART_COLORS.length] }}
              />
              <div className="flex-1">
                <div className="flex justify-between text-sm mb-1.5">
                  <span className="font-medium text-zinc-200">{entry.name}</span>
                  <span className="text-zinc-500">{entry.value} ({percent}%)</span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-zinc-900">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${percent}%`,
                      backgroundColor: CHART_COLORS[index % CHART_COLORS.length],
                    }}
                  />
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function buildLinePath(data, width = 800, height = 240) {
  if (!data.length) return { linePath: '', areaPath: '', points: [], gridLines: [] }

  const padding = 20
  const innerWidth = width - padding * 2
  const innerHeight = height - padding * 2
  const maxValue = Math.max(...data.map((item) => item.count), 1)
  const step = data.length === 1 ? 0 : innerWidth / (data.length - 1)
  const points = data.map((item, index) => {
    const x = padding + index * step
    const y = height - padding - (item.count / maxValue) * innerHeight
    return { ...item, x, y }
  })

  const linePath = points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ')
  const areaPath = `${linePath} L ${points.at(-1)?.x ?? padding} ${height - padding} L ${points[0]?.x ?? padding} ${height - padding} Z`

  const gridLines = Array.from({ length: 4 }, (_, index) => padding + (innerHeight / 3) * index)
  return { linePath, areaPath, points, gridLines }
}

function TimelineChart({ data, t }) {
  if (!data.length) return null
  const { linePath, areaPath, points, gridLines } = buildLinePath(data)

  return (
    <div className="w-full">
      <div className="w-full overflow-x-auto pb-4">
        <svg viewBox="0 0 800 240" className="h-64 w-full min-w-[600px]" preserveAspectRatio="none">
          <defs>
            <linearGradient id="timelineStroke" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#8b5cf6" />
              <stop offset="100%" stopColor="#38bdf8" />
            </linearGradient>
            <linearGradient id="timelineFill" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="rgba(139, 92, 246, 0.2)" />
              <stop offset="100%" stopColor="rgba(139, 92, 246, 0)" />
            </linearGradient>
          </defs>

          {gridLines.map((y, index) => (
            <line key={index} x1="20" x2="780" y1={y} y2={y} stroke="rgba(255,255,255,0.05)" strokeDasharray="4 4" />
          ))}

          <path d={areaPath} fill="url(#timelineFill)" />
          <path d={linePath} fill="none" stroke="url(#timelineStroke)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />

          {points.map((point, index) => (
            <g key={point.date}>
              <circle cx={point.x} cy={point.y} r="4" fill="#18181b" stroke="#8b5cf6" strokeWidth="2" />
              <text x={point.x} y="235" textAnchor="middle" fill="#71717a" fontSize="10">
                {point.label}
              </text>
            </g>
          ))}
        </svg>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6">
        {data.map((entry) => (
          <div key={entry.date} className="flex flex-col">
            <span className="text-xs uppercase tracking-wider text-zinc-500 mb-1">{entry.label}</span>
            <span className="text-lg font-medium text-zinc-200">{entry.count} {t('dashboard.activity.predictions')}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

const PROFILE_METRICS = [
  { key: 'brightness', label: 'Brightness' },
  { key: 'contrast', label: 'Contrast' },
  { key: 'saturation', label: 'Saturation' },
  { key: 'edge_strength', label: 'Texture' },
]

function confidenceToPercent(value) {
  const numericValue = Number(value)
  return Number.isFinite(numericValue) ? Math.max(0, Math.min(100, Math.round(numericValue * 100))) : 0
}

function profileToPercent(value) {
  const numericValue = Number(value)
  return Number.isFinite(numericValue) ? Math.max(0, Math.min(100, Math.round((numericValue / 255) * 100))) : 0
}

function PredictionInsightPanel({ prediction, compact = false }) {
  const { t } = useTranslation()

  if (!prediction) {
    return null
  }

  const topPredictions = prediction.top_predictions ?? []
  const imageProfile = prediction.image_profile ?? {}
  const explanation = prediction.explanation ?? []
  const riskFlags = prediction.risk_flags ?? []
  const heatmapSource = prediction.heatmap ? `data:image/svg+xml;base64,${prediction.heatmap}` : ''

  return (
    <div className={`grid gap-4 ${compact ? '' : 'lg:grid-cols-[0.95fr_1.05fr]'}`}>
      <div className="rounded-lg border border-zinc-800 bg-zinc-950/40 p-4">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-zinc-100">{t('dashboard.ai.topPredictions')}</p>
            <p className="text-xs text-zinc-500">{prediction.source} · {prediction.inference_ms}ms</p>
          </div>
          <BrainCircuit className="h-4 w-4 text-sky-300" aria-hidden="true" />
        </div>

        <div className="space-y-3">
          {topPredictions.length ? topPredictions.slice(0, 5).map((entry) => {
            const percent = confidenceToPercent(entry.confidence)
            return (
              <div key={entry.label} className="space-y-1.5">
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="truncate text-zinc-300">{capitalizeLabel(entry.label)}</span>
                  <span className="text-zinc-500">{percent}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-zinc-900">
                  <div className="h-full rounded-full bg-sky-300" style={{ width: `${percent}%` }} />
                </div>
              </div>
            )
          }) : (
            <p className="text-sm text-zinc-600">{t('dashboard.ai.noRanking')}</p>
          )}
        </div>
      </div>

      <div className="rounded-lg border border-zinc-800 bg-zinc-950/40 p-4">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-medium text-zinc-100">{t('dashboard.ai.visualProfile')}</p>
            <p className="text-xs text-zinc-500">{t('dashboard.ai.visualProfileHint')}</p>
          </div>
          <ScanLine className="h-4 w-4 text-sky-300" aria-hidden="true" />
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          {PROFILE_METRICS.map((metric) => {
            const percent = profileToPercent(imageProfile[metric.key])
            return (
              <div key={metric.key} className="space-y-1.5">
                <div className="flex items-center justify-between gap-3 text-xs uppercase tracking-[0.12em] text-zinc-500">
                  <span>{metric.label}</span>
                  <span>{percent}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-zinc-900">
                  <div className="h-full rounded-full bg-emerald-300" style={{ width: `${percent}%` }} />
                </div>
              </div>
            )
          })}
        </div>

        {explanation.length || riskFlags.length ? (
          <div className="mt-5 space-y-2">
            {explanation.slice(0, 3).map((item) => (
              <p key={item} className="text-sm leading-5 text-zinc-400">{item}</p>
            ))}
            {riskFlags.map((item) => (
              <div key={item} className="rounded-md border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-xs text-amber-100">
                {item}
              </div>
            ))}
          </div>
        ) : null}
      </div>

      {heatmapSource ? (
        <div className={`${compact ? '' : 'lg:col-span-2'} rounded-lg border border-zinc-800 bg-zinc-950/40 p-4`}>
          <p className="mb-3 text-sm font-medium text-zinc-100">{t('dashboard.ai.heatmap')}</p>
          <img src={heatmapSource} alt={t('dashboard.ai.heatmapAlt')} className="max-h-72 w-full rounded-md object-contain" />
        </div>
      ) : null}
    </div>
  )
}

function DashboardSection({ history, historyError, isLoading, filters, setFilter, health }) {
  const { t } = useTranslation()
  const summary = useMemo(() => summarizeHistory(history), [history])
  const distribution = useMemo(() => buildDistributionData(history), [history])
  const timeline = useMemo(() => buildTimelineData(history), [history])
  const availableClasses = useMemo(
    () => [...new Set(history.map((item) => item.class).filter(Boolean))].sort(),
    [history],
  )

  return (
    <div className="space-y-12">
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div className="space-y-2">
            <h2 className="text-3xl font-semibold tracking-tight text-zinc-100">{t('dashboard.overview.title')}</h2>
            <p className="text-zinc-400 max-w-xl">
              {t('dashboard.overview.description')}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label={t('dashboard.overview.stats.totalPredictions')} value={summary.total} hint={t('dashboard.overview.stats.totalPredictionsHint')} tone="accent" />
          <StatCard label={t('dashboard.overview.stats.confidence')} value={formatConfidence(summary.averageConfidence)} hint={t('dashboard.overview.stats.confidenceHint')} tone="success" />
          <StatCard label={t('dashboard.overview.stats.topClass')} value={capitalizeLabel(summary.topClass)} hint={t('dashboard.overview.stats.topClassHint')} tone="warning" />
          <StatCard
            label={t('dashboard.overview.stats.lastInference')}
            value={summary.latestItem ? formatDateTime(summary.latestItem.created_at).split(' ')[0] : '-'}
            hint={summary.latestItem ? capitalizeLabel(summary.latestItem.class) : t('dashboard.overview.stats.lastInferenceNone')}
            tone="outline"
          />
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('dashboard.distribution.title')}</CardTitle>
          <CardDescription>{t('dashboard.distribution.description')}</CardDescription>
        </CardHeader>
        <CardContent>
          {distribution.length ? <DistributionChart data={distribution} t={t} /> : <EmptyState title={t('dashboard.distribution.emptyTitle')} description={t('dashboard.distribution.emptyDescription')} />}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('dashboard.activity.title')}</CardTitle>
          <CardDescription>{t('dashboard.activity.description')}</CardDescription>
        </CardHeader>
        <CardContent>
          {timeline.length ? <TimelineChart data={timeline} t={t} /> : <EmptyState title={t('dashboard.activity.emptyTitle')} description={t('dashboard.activity.emptyDescription')} />}
        </CardContent>
      </Card>

      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <h3 className="text-xl font-medium text-zinc-100">{t('dashboard.history.title')}</h3>
          <div className="flex items-center gap-3">
            <input
              type="date"
              value={filters.date}
              onChange={(e) => setFilter('date', e.target.value)}
              className="h-9 rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm text-zinc-300 focus:outline-none focus:ring-1 focus:ring-zinc-700"
            />
            <select
              value={filters.climateClass}
              onChange={(e) => setFilter('climateClass', e.target.value)}
              className="h-9 rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm text-zinc-300 focus:outline-none focus:ring-1 focus:ring-zinc-700"
            >
              <option value="">{t('dashboard.history.allClasses')}</option>
              {availableClasses.map((c) => (
                <option key={c} value={c}>{capitalizeLabel(c)}</option>
              ))}
            </select>
          </div>
        </div>

        {historyError ? (
          <EmptyState title={t('dashboard.history.error')} description={historyError} />
        ) : isLoading ? (
          <div className="space-y-2">
             <div className="h-12 bg-zinc-900/50 rounded-md animate-pulse" />
             <div className="h-12 bg-zinc-900/50 rounded-md animate-pulse" />
             <div className="h-12 bg-zinc-900/50 rounded-md animate-pulse" />
          </div>
        ) : history.length ? (
          <Card className="overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('dashboard.history.table.class')}</TableHead>
                  <TableHead>{t('dashboard.history.table.confidence')}</TableHead>
                  <TableHead>{t('dashboard.history.table.model')}</TableHead>
                  <TableHead className="text-right">{t('dashboard.history.table.timestamp')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {history.slice(0, 10).map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-medium text-zinc-200">
                      <div className="flex items-center gap-2">
                        {capitalizeLabel(item.class)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs font-normal">
                        {formatConfidence(item.confidence)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-zinc-400">{item.model_name}</TableCell>
                    <TableCell className="text-right text-zinc-500">{formatDateTime(item.created_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        ) : (
          <EmptyState title={t('dashboard.history.emptyTitle')} description={t('dashboard.history.emptyDescription')} />
        )}
      </div>
    </div>
  )
}

function InferenceSection({ prediction, mode, setMode, selectedFile, setSelectedFile, base64Input, setBase64Input, previewUrl, error, isSubmitting, submit, reset }) {
  const { t } = useTranslation()
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h2 className="text-3xl font-semibold tracking-tight text-zinc-100">{t('dashboard.inference.title')}</h2>
        <p className="text-zinc-400 max-w-xl">
          {t('dashboard.inference.description')}
        </p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>{t('dashboard.inference.input.title')}</CardTitle>
            <Tabs value={mode} onValueChange={setMode} className="w-[200px]">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="upload">{t('dashboard.inference.tabs.upload')}</TabsTrigger>
                <TabsTrigger value="base64">{t('dashboard.inference.tabs.base64')}</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-6">
            {mode === 'upload' ? (
              <label className="flex flex-col items-center justify-center w-full h-48 border-2 border-dashed border-zinc-800 rounded-xl bg-zinc-900/20 hover:bg-zinc-900/40 hover:border-zinc-700 transition-colors cursor-pointer group">
                <div className="flex flex-col items-center justify-center pt-5 pb-6">
                  <svg className="w-8 h-8 mb-4 text-zinc-500 group-hover:text-zinc-400 transition-colors" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 20 16">
                    <path stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 13h3a3 3 0 0 0 0-6h-.025A5.56 5.56 0 0 0 16 6.5 5.5 5.5 0 0 0 5.207 5.021C5.137 5.017 5.071 5 5 5a4 4 0 0 0 0 8h2.167M10 15V6m0 0L8 8m2-2 2 2"/>
                  </svg>
                  <p className="mb-2 text-sm text-zinc-400"><span className="font-semibold text-zinc-200">{t('dashboard.inference.input.clickUpload')}</span> {t('dashboard.inference.input.dragDrop')}</p>
                  <p className="text-xs text-zinc-500">{selectedFile ? selectedFile.name : t('dashboard.inference.input.supportedFiles')}</p>
                </div>
                <input type="file" className="hidden" accept="image/*" onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)} />
              </label>
            ) : (
              <textarea
                value={base64Input}
                onChange={(e) => setBase64Input(e.target.value)}
                rows={6}
                placeholder={t('dashboard.inference.input.pasteBase64')}
                className="w-full rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 text-sm text-zinc-200 focus:outline-none focus:ring-1 focus:ring-zinc-700"
              />
            )}

            {error && (
              <div className="p-3 rounded-lg bg-red-950/50 border border-red-900/50 text-sm text-red-200">
                {error}
              </div>
            )}

            <div className="flex items-center gap-3">
              <button
                type="submit"
                disabled={isSubmitting}
                className="rounded-lg bg-sky-300 px-4 py-2 text-sm font-medium text-zinc-950 transition-colors hover:bg-sky-200 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isSubmitting ? t('dashboard.inference.input.processing') : t('dashboard.inference.input.submit')}
              </button>
              <button
                type="button"
                onClick={reset}
                className="px-4 py-2 bg-transparent text-zinc-300 text-sm font-medium rounded-lg border border-zinc-800 hover:bg-zinc-900 transition-colors"
              >
                {t('dashboard.inference.input.clear')}
              </button>
            </div>
          </form>
        </CardContent>
      </Card>

      {previewUrl && (
        <Card>
          <CardHeader>
            <CardTitle>{t('dashboard.inference.results.title')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="w-full max-w-md overflow-hidden rounded-xl border border-zinc-800">
              <img src={previewUrl} alt="Preview" className="w-full h-auto object-cover" />
            </div>

            {prediction ? (
              <div className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="rounded-lg border border-zinc-800 bg-zinc-950/40 p-4">
                    <p className="mb-1 text-xs text-zinc-500">{t('dashboard.inference.results.detectedClass')}</p>
                    <p className="flex items-center gap-2 text-lg font-medium text-zinc-100">
                      {capitalizeLabel(prediction.class)}
                      <Badge variant="success" className="py-0 text-[10px]">{formatConfidence(prediction.confidence)}</Badge>
                    </p>
                  </div>
                  <div className="rounded-lg border border-zinc-800 bg-zinc-950/40 p-4">
                    <p className="mb-1 text-xs text-zinc-500">{t('dashboard.inference.results.modelInfo')}</p>
                    <p className="text-sm text-zinc-300">{prediction.model_name}</p>
                    <p className="mt-1 text-xs text-zinc-500">{prediction.inference_ms}{t('dashboard.inference.results.latency')}</p>
                  </div>
                </div>
                <PredictionInsightPanel prediction={prediction} />
              </div>
            ) : (
              <EmptyState title={t('dashboard.inference.results.waitingTitle')} description={t('dashboard.inference.results.waitingDescription')} />
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function RealtimeSection({ onSaved }) {
  const { t } = useTranslation()
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const inFlightRef = useRef(false)
  const timerRef = useRef<number | null>(null)
  const detectInFlightRef = useRef(false)
  const detectTimerRef = useRef<number | null>(null)
  const [isActive, setIsActive] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [intervalMs, setIntervalMs] = useState(2000)
  const [latestPrediction, setLatestPrediction] = useState<Record<string, any> | null>(null)
  const [detections, setDetections] = useState<Array<Record<string, any>>>([])
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [framesProcessed, setFramesProcessed] = useState(0)
  const [failures, setFailures] = useState(0)
  const [averageLatency, setAverageLatency] = useState(0)
  const [lastFrameAt, setLastFrameAt] = useState('')

  const stopCamera = useCallback(() => {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current)
      timerRef.current = null
    }

    if (detectTimerRef.current) {
      window.clearTimeout(detectTimerRef.current)
      detectTimerRef.current = null
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null
    }

    setDetections([])
  }, [])

  const captureFrame = useCallback(async ({ persist = false } = {}) => {
    const video = videoRef.current
    const canvas = canvasRef.current

    if (!video || !canvas || video.readyState < 2) {
      return null
    }

    if (inFlightRef.current) {
      return null
    }

    const width = video.videoWidth || 640
    const height = video.videoHeight || 360
    const context = canvas.getContext('2d')

    if (!context) {
      setError(t('dashboard.realtime.error.canvas'))
      return null
    }

    inFlightRef.current = true
    setIsAnalyzing(true)
    setError(null)

    try {
      canvas.width = width
      canvas.height = height
      context.drawImage(video, 0, 0, width, height)

      const blob = await new Promise<Blob | null>((resolve) => {
        canvas.toBlob(resolve, 'image/jpeg', 0.78)
      })

      if (!blob) {
        throw new Error(t('dashboard.realtime.error.frame'))
      }

      const file = new File([blob], `aeris-live-${Date.now()}.jpg`, { type: 'image/jpeg' })
      const data = await predictClimate({ file, persist })
      setLatestPrediction(data)
      setLastFrameAt(new Date().toISOString())

      setFramesProcessed((currentCount) => {
        const nextCount = currentCount + 1
        const latency = Number(data.inference_ms ?? 0)
        setAverageLatency((currentAverage) => Math.round(((currentAverage * currentCount) + latency) / nextCount))
        return nextCount
      })

      if (persist && typeof onSaved === 'function') {
        onSaved(data)
      }

      return data
    } catch (requestError) {
      setFailures((currentValue) => currentValue + 1)
      setError(requestError instanceof Error ? requestError.message : t('dashboard.realtime.error.inference'))
      return null
    } finally {
      inFlightRef.current = false
      setIsAnalyzing(false)
    }
  }, [onSaved, t])

  const runDetection = useCallback(async () => {
    const video = videoRef.current
    const canvas = canvasRef.current

    if (!video || !canvas || video.readyState < 2 || detectInFlightRef.current) {
      return
    }

    const width = video.videoWidth || 640
    const height = video.videoHeight || 360
    const context = canvas.getContext('2d')

    if (!context) {
      return
    }

    detectInFlightRef.current = true

    try {
      canvas.width = width
      canvas.height = height
      context.drawImage(video, 0, 0, width, height)

      const blob = await new Promise<Blob | null>((resolve) => {
        canvas.toBlob(resolve, 'image/jpeg', 0.7)
      })

      if (!blob) {
        return
      }

      const file = new File([blob], `aeris-detect-${Date.now()}.jpg`, { type: 'image/jpeg' })
      const result = await detectClimate({ file })
      setDetections(Array.isArray(result?.detections) ? result.detections : [])
    } catch {
      // detecção é best-effort; não interrompe o stream
    } finally {
      detectInFlightRef.current = false
    }
  }, [])

  useEffect(() => {
    if (!isActive) {
      stopCamera()
      return undefined
    }

    let wasCancelled = false

    async function startCamera() {
      if (!navigator.mediaDevices?.getUserMedia) {
        setError(t('dashboard.realtime.error.unsupported'))
        setIsActive(false)
        return
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: 'environment',
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
          audio: false,
        })

        if (wasCancelled) {
          stream.getTracks().forEach((track) => track.stop())
          return
        }

        streamRef.current = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
        }
        setError(null)
      } catch {
        setError(t('dashboard.realtime.error.cameraAccess'))
        setIsActive(false)
      }
    }

    startCamera()

    return () => {
      wasCancelled = true
      stopCamera()
    }
  }, [isActive, stopCamera, t])

  useEffect(() => {
    if (!isActive || error) {
      return undefined
    }

    let wasCancelled = false

    function scheduleNextCapture(delay: number) {
      timerRef.current = window.setTimeout(async () => {
        await captureFrame({ persist: false })
        if (!wasCancelled) {
          scheduleNextCapture(intervalMs)
        }
      }, delay)
    }

    scheduleNextCapture(900)

    return () => {
      wasCancelled = true
      if (timerRef.current) {
        window.clearTimeout(timerRef.current)
        timerRef.current = null
      }
    }
  }, [captureFrame, error, intervalMs, isActive])

  useEffect(() => {
    if (!isActive || error) {
      return undefined
    }

    let wasCancelled = false
    const detectIntervalMs = Math.max(intervalMs, 1500)

    function scheduleNextDetection(delay: number) {
      detectTimerRef.current = window.setTimeout(async () => {
        await runDetection()
        if (!wasCancelled) {
          scheduleNextDetection(detectIntervalMs)
        }
      }, delay)
    }

    scheduleNextDetection(1200)

    return () => {
      wasCancelled = true
      if (detectTimerRef.current) {
        window.clearTimeout(detectTimerRef.current)
        detectTimerRef.current = null
      }
    }
  }, [error, intervalMs, isActive, runDetection])

  const statusTone = error ? 'danger' : isActive ? 'success' : 'default'

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h2 className="text-3xl font-semibold tracking-tight text-zinc-100">{t('dashboard.realtime.title')}</h2>
        <p className="text-zinc-400 max-w-xl">
          {t('dashboard.realtime.description')}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <Card className="overflow-hidden border-zinc-800 bg-zinc-950">
          <CardHeader className="flex flex-col gap-4 border-b border-zinc-800/50 bg-zinc-900/20 pb-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-w-0 items-center gap-3">
              <div className={`h-2.5 w-2.5 rounded-full ${isActive && !error ? 'bg-emerald-500 animate-pulse' : error ? 'bg-red-500' : 'bg-zinc-600'}`} />
              <div>
                <CardTitle className="text-base">{isActive ? t('dashboard.realtime.active') : t('dashboard.realtime.offline')}</CardTitle>
                <CardDescription>{isAnalyzing ? t('dashboard.realtime.processing') : t('dashboard.realtime.cadence', { seconds: (intervalMs / 1000).toFixed(1) })}</CardDescription>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setIsActive((currentValue) => !currentValue)}
              className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-red-500/10 text-red-300 hover:bg-red-500/20'
                  : 'bg-sky-300 text-zinc-950 hover:bg-sky-200'
              }`}
            >
              {isActive ? <Pause className="h-4 w-4" aria-hidden="true" /> : <Camera className="h-4 w-4" aria-hidden="true" />}
              {isActive ? t('dashboard.realtime.stop') : t('dashboard.realtime.start')}
            </button>
          </CardHeader>
          <CardContent className="p-0">
            <div className="relative flex aspect-video w-full items-center justify-center bg-zinc-950">
              {error ? (
                <div className="p-4 text-center text-sm text-red-300">{error}</div>
              ) : !isActive ? (
                <div className="flex flex-col items-center gap-3 text-sm text-zinc-500">
                  <Camera className="h-9 w-9 opacity-60" aria-hidden="true" />
                  {t('dashboard.realtime.standby')}
                </div>
              ) : (
                <>
                  <video
                    ref={videoRef}
                    autoPlay
                    playsInline
                    muted
                    className="absolute inset-0 h-full w-full object-cover"
                  />
                  <canvas ref={canvasRef} className="hidden" />
                  <DetectionOverlay detections={detections} />
                  <div className="pointer-events-none absolute inset-x-4 bottom-4 flex flex-wrap items-end justify-between gap-3">
                    <div className="rounded-md border border-zinc-700 bg-zinc-950/85 px-3 py-2">
                      <p className="text-xs uppercase tracking-[0.14em] text-zinc-500">{t('dashboard.realtime.liveClass')}</p>
                      <p className="text-sm font-medium text-zinc-100">
                        {latestPrediction ? capitalizeLabel(latestPrediction.class) : t('dashboard.realtime.waitingFrame')}
                      </p>
                    </div>
                    {latestPrediction ? (
                      <Badge variant="success">{formatConfidence(latestPrediction.confidence)}</Badge>
                    ) : null}
                  </div>
                </>
              )}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <MetricBlock label={t('dashboard.realtime.stats.status')} value={error ? t('dashboard.realtime.stats.error') : isActive ? t('dashboard.realtime.stats.live') : t('dashboard.realtime.stats.idle')} hint={t('dashboard.realtime.stats.api')} icon={Gauge} tone={statusTone} />
            <MetricBlock label={t('dashboard.realtime.stats.frames')} value={framesProcessed} hint={`${failures} ${t('dashboard.realtime.stats.failures')}`} icon={ScanLine} tone={failures ? 'warning' : 'default'} />
            <MetricBlock label={t('dashboard.realtime.stats.latency')} value={averageLatency ? `${averageLatency}ms` : '-'} hint={t('dashboard.realtime.stats.average')} icon={BrainCircuit} tone="success" />
            <MetricBlock label={t('dashboard.realtime.stats.lastFrame')} value={lastFrameAt ? formatDateTime(lastFrameAt).split(' ')[0] : '-'} hint={lastFrameAt ? formatDateTime(lastFrameAt).split(' ').slice(1).join(' ') : t('dashboard.realtime.stats.none')} icon={Camera} tone="default" />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>{t('dashboard.realtime.controls.title')}</CardTitle>
              <CardDescription>{t('dashboard.realtime.controls.description')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <label className="block space-y-2">
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="font-medium text-zinc-300">{t('dashboard.realtime.controls.interval')}</span>
                  <span className="text-zinc-500">{(intervalMs / 1000).toFixed(1)}s</span>
                </div>
                <input
                  type="range"
                  min="1000"
                  max="5000"
                  step="500"
                  value={intervalMs}
                  onChange={(event) => setIntervalMs(Number(event.target.value))}
                  className="w-full accent-sky-300"
                />
              </label>

              <button
                type="button"
                disabled={!isActive || isAnalyzing}
                onClick={() => captureFrame({ persist: true })}
                className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-zinc-800 px-4 py-2 text-sm font-medium text-zinc-200 transition-colors hover:bg-zinc-900 disabled:cursor-wait disabled:opacity-60"
              >
                <Download className="h-4 w-4" aria-hidden="true" />
                {t('dashboard.realtime.controls.saveFrame')}
              </button>
            </CardContent>
          </Card>

          {detections.length ? (
            <DetectionInsightPanel detections={detections} />
          ) : (
            <EmptyState title={t('dashboard.realtime.emptyTitle')} description={t('dashboard.realtime.emptyDescription')} />
          )}
        </div>
      </div>
    </div>
  )
}

function DetectionInsightPanel({ detections }) {
  const groups = detections.reduce((acc, item) => {
    const key = capitalizeLabel(item.label)
    const confidence = Number(item.confidence) || 0
    if (!acc[key]) {
      acc[key] = { count: 0, best: 0 }
    }
    acc[key].count += 1
    acc[key].best = Math.max(acc[key].best, confidence)
    return acc
  }, {})

  const rows = Object.entries(groups).sort((a, b) => b[1].best - a[1].best)

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-950/40 p-4">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-zinc-100">Objetos detectados</p>
          <p className="text-xs text-zinc-500">{detections.length} no quadro · {rows.length} tipos</p>
        </div>
        <ScanLine className="h-4 w-4 text-sky-300" aria-hidden="true" />
      </div>

      <div className="space-y-3">
        {rows.map(([label, info]) => {
          const percent = Math.round(info.best * 100)
          return (
            <div key={label} className="space-y-1.5">
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="truncate text-zinc-300">
                  {label}
                  {info.count > 1 ? <span className="ml-1.5 text-xs text-zinc-500">×{info.count}</span> : null}
                </span>
                <span className="text-zinc-500">{percent}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-zinc-900">
                <div className="h-full rounded-full bg-emerald-300" style={{ width: `${percent}%` }} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function DetectionOverlay({ detections }) {
  if (!detections?.length) {
    return null
  }

  const palette = ['#22c55e', '#38bdf8', '#f97316', '#eab308', '#ec4899', '#a855f7']

  return (
    <div className="pointer-events-none absolute inset-0">
      {detections.map((detection, index) => {
        const box = detection.box ?? {}
        const color = palette[index % palette.length]
        const left = `${Math.min(Math.max(Number(box.x) || 0, 0), 1) * 100}%`
        const top = `${Math.min(Math.max(Number(box.y) || 0, 0), 1) * 100}%`
        const width = `${Math.min(Math.max(Number(box.width) || 0, 0), 1) * 100}%`
        const height = `${Math.min(Math.max(Number(box.height) || 0, 0), 1) * 100}%`

        return (
          <div
            key={`${detection.label}-${index}`}
            className="absolute rounded-sm"
            style={{ left, top, width, height, border: `2px solid ${color}` }}
          >
            <span
              className="absolute left-0 top-0 -translate-y-full whitespace-nowrap px-1.5 py-0.5 text-[11px] font-semibold text-zinc-950"
              style={{ backgroundColor: color }}
            >
              {capitalizeLabel(detection.label)} {Math.round((Number(detection.confidence) || 0) * 100)}%
            </span>
          </div>
        )
      })}
    </div>
  )
}


function ResearchJobBadge({ status }) {
  const variant = status === 'succeeded' ? 'success' : status === 'failed' ? 'destructive' : 'warning'
  return <Badge variant={variant}>{status}</Badge>
}

function formatClimateNumber(value: unknown, digits = 3) {
  const numericValue = Number(value)
  return Number.isFinite(numericValue) ? numericValue.toFixed(digits) : '-'
}

function getTrendResult(result: Record<string, any> | null) {
  return result?.regional_trend ?? result?.trend_analysis ?? {}
}

function MetricBlock({ label, value, hint, icon: Icon, tone = 'default' }) {
  const toneClass = {
    default: 'text-sky-300',
    success: 'text-emerald-400',
    warning: 'text-amber-400',
    danger: 'text-red-400',
  }[tone] ?? 'text-sky-300'

  return (
    <div className="min-w-0 rounded-lg border border-zinc-800 bg-zinc-950/50 p-4">
      <div className="flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-zinc-500">
        {Icon ? <Icon className={`h-3.5 w-3.5 ${toneClass}`} aria-hidden="true" /> : null}
        <span>{label}</span>
      </div>
      <p className="mt-3 truncate text-2xl font-semibold tracking-tight text-zinc-100">{value}</p>
      {hint ? <p className="mt-1 truncate text-xs text-zinc-500">{hint}</p> : null}
    </div>
  )
}

function PipelineSourceRow({ icon: Icon, title, description, status }) {
  return (
    <div className="flex gap-3 rounded-lg border border-zinc-800 bg-zinc-950/40 p-4">
      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-zinc-900 text-sky-300">
        <Icon className="h-4 w-4" aria-hidden="true" />
      </div>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-medium text-zinc-100">{title}</p>
          <Badge variant="outline">{status}</Badge>
        </div>
        <p className="mt-1 text-sm text-zinc-500">{description}</p>
      </div>
    </div>
  )
}

function OutputList({ outputs }) {
  const entries = Object.entries(outputs ?? {}).filter(([, value]) => value)

  if (!entries.length) {
    return null
  }

  return (
    <div className="space-y-2">
      {entries.map(([key, value]) => (
        <div key={key} className="flex min-w-0 items-center justify-between gap-3 rounded-md border border-zinc-800 bg-zinc-950/40 px-3 py-2">
          <span className="text-xs uppercase tracking-[0.14em] text-zinc-600">{key.replaceAll('_', ' ')}</span>
          <code className="truncate text-xs text-zinc-300">{String(value)}</code>
        </div>
      ))}
    </div>
  )
}

function CompactRecords({ records, columns, emptyLabel }) {
  if (!records?.length) {
    return <p className="text-sm text-zinc-600">{emptyLabel}</p>
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-800">
      <table className="w-full min-w-[560px] text-left text-sm">
        <thead className="bg-zinc-900/70 text-xs uppercase tracking-[0.12em] text-zinc-500">
          <tr>
            {columns.map((column) => (
              <th key={column} className="px-3 py-2 font-medium">{column.replaceAll('_', ' ')}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800">
          {records.slice(0, 6).map((record, index) => (
            <tr key={`${record.year ?? record.city ?? record.period ?? index}-${index}`}>
              {columns.map((column) => (
                <td key={column} className="px-3 py-2 text-zinc-300">
                  {typeof record[column] === 'number' ? formatClimateNumber(record[column], 3) : String(record[column] ?? '-')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ClimateSignalCard({ research }) {
  const { t } = useTranslation()
  const [csvPath, setCsvPath] = useState('')
  const [regionName, setRegionName] = useState(t('dashboard.research.climate.defaultRegion'))
  const result = research.climateResult
  const trend = getTrendResult(result)
  const assessment = result?.final_assessment ?? {}
  const anomaly = result?.anomaly_analysis ?? {}
  const temperature = result?.temperature_summary ?? {}
  const annualRecords = result?.aggregations?.annual ?? []
  const canRun = Boolean(csvPath.trim() || research.status.climate_dataset_exists)

  function runAnalysis() {
    if (!canRun) {
      return
    }

    research.runClimateAnalysis({
      csv_path: csvPath.trim() || undefined,
      region_name: regionName.trim() || undefined,
    })
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <BrainCircuit className="h-4 w-4 text-sky-300" aria-hidden="true" />
              {t('dashboard.research.climate.title')}
            </CardTitle>
            <CardDescription>{t('dashboard.research.climate.description')}</CardDescription>
          </div>
          <button
            type="button"
            disabled={!canRun || research.isAnalyzingClimate}
            onClick={runAnalysis}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-sky-300 px-4 py-2 text-sm font-semibold text-zinc-950 transition-colors hover:bg-sky-200 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Play className="h-4 w-4" aria-hidden="true" />
            {research.isAnalyzingClimate ? t('dashboard.research.climate.running') : t('dashboard.research.climate.run')}
          </button>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-3 lg:grid-cols-[1fr_1.2fr]">
          <label className="space-y-2">
            <span className="text-sm font-medium text-zinc-300">{t('dashboard.research.climate.region')}</span>
            <input
              value={regionName}
              onChange={(event) => setRegionName(event.target.value)}
              className="h-10 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm text-zinc-200 outline-none focus:ring-1 focus:ring-sky-500/60"
            />
          </label>
          <label className="space-y-2">
            <span className="text-sm font-medium text-zinc-300">{t('dashboard.research.climate.csvPath')}</span>
            <input
              value={csvPath}
              onChange={(event) => setCsvPath(event.target.value)}
              placeholder={research.status.climate_dataset_path || t('dashboard.research.climate.csvPlaceholder')}
              className="h-10 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm text-zinc-200 outline-none placeholder:text-zinc-600 focus:ring-1 focus:ring-sky-500/60"
            />
          </label>
        </div>

        {!canRun ? (
          <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4 text-sm text-amber-100">
            <div className="flex gap-3">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" aria-hidden="true" />
              <p>{t('dashboard.research.climate.emptyNoCsv')}</p>
            </div>
          </div>
        ) : null}

        {result ? (
          <div className="space-y-6">
            <div className="grid gap-3 md:grid-cols-4">
              <MetricBlock label={t('dashboard.research.climate.assessment')} value={assessment.label ?? '-'} hint={assessment.summary ?? result.region ?? '-'} icon={CheckCircle2} tone={assessment.level === 'high' ? 'success' : 'default'} />
              <MetricBlock label={t('dashboard.research.climate.slope')} value={`${formatClimateNumber(trend.slope_per_decade)} C/dec`} hint={`${formatClimateNumber(trend.years_covered, 1)} anos`} icon={LineChart} tone={trend.slope_per_decade > 0 ? 'warning' : 'default'} />
              <MetricBlock label={t('dashboard.research.climate.trend')} value={trend.significant ? t('dashboard.research.climate.confidence') : 'triagem'} hint={`p ${formatClimateNumber(trend.p_value, 5)}`} icon={BarChart3} tone={trend.significant ? 'success' : 'warning'} />
              <MetricBlock label="Temp média" value={`${formatClimateNumber(temperature.mean, 2)} C`} hint={`${formatClimateNumber(temperature.min, 1)} a ${formatClimateNumber(temperature.max, 1)} C`} icon={ThermometerSun} tone="default" />
            </div>

            <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
              <div className="rounded-lg border border-zinc-800 bg-zinc-950/40 p-4">
                <p className="mb-3 font-medium text-zinc-100">{t('dashboard.research.climate.warnings')}</p>
                {result.warnings?.length ? (
                  <div className="space-y-2">
                    {result.warnings.map((warning) => (
                      <p key={warning} className="rounded-md border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-sm text-amber-100">{warning}</p>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-zinc-500">{assessment.summary ?? '-'}</p>
                )}
              </div>

              <div className="rounded-lg border border-zinc-800 bg-zinc-950/40 p-4">
                <p className="mb-3 font-medium text-zinc-100">{t('dashboard.research.climate.trend')}</p>
                <div className="grid gap-3 sm:grid-cols-3">
                  <MetricBlock label="Anomalias" value={anomaly.total_anomalies ?? '-'} hint={anomaly.dominant_level ?? '-'} icon={Gauge} tone="warning" />
                  <MetricBlock label="Extremos" value={result.hot_extremes?.hot_days ?? '-'} hint={result.hot_extremes?.threshold ? `>${formatClimateNumber(result.hot_extremes.threshold, 1)} C` : '-'} icon={ThermometerSun} tone="danger" />
                  <MetricBlock label="Correlação" value={formatClimateNumber(result.drivers?.temperature_precipitation_correlation, 3)} hint="temp x chuva" icon={Database} tone="default" />
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <p className="font-medium text-zinc-100">Agregação anual</p>
              <CompactRecords records={annualRecords} columns={['timestamp', 'temperature_2m_mean', 'temperature_2m_max', 'precipitation_sum']} emptyLabel={t('dashboard.research.baixada.noRecords')} />
            </div>
          </div>
        ) : (
          <EmptyState title={t('dashboard.research.climate.emptyTitle')} description={t('dashboard.research.climate.emptyDescription')} />
        )}
      </CardContent>
    </Card>
  )
}

function BaixadaAnalysisCard({ research }) {
  const { t } = useTranslation()
  const today = useMemo(() => new Date().toISOString().slice(0, 10), [])
  const [datasetRoot, setDatasetRoot] = useState('datasets')
  const [outputRoot, setOutputRoot] = useState('outputs')
  const [startDate, setStartDate] = useState('1940-01-01')
  const [endDate, setEndDate] = useState(today)
  const [sourceModel, setSourceModel] = useState('era5')
  const [yearsPerChunk, setYearsPerChunk] = useState('1')
  const [requestDelaySeconds, setRequestDelaySeconds] = useState('2')
  const [retryAttempts, setRetryAttempts] = useState('10')
  const [retryMaxDelaySeconds, setRetryMaxDelaySeconds] = useState('600')
  const [maxBatches, setMaxBatches] = useState('')
  const [useGrid, setUseGrid] = useState(false)
  const [forceDownload, setForceDownload] = useState(false)
  const [forceRebuildOutputs, setForceRebuildOutputs] = useState(false)
  const result = research.baixadaResult
  const trend = getTrendResult(result)
  const coverage = result?.coverage ?? {}
  const confidenceVariant = trend.significant ? 'success' : 'warning'

  function parseOptionalLimit(value) {
    const parsedValue = Number.parseInt(value, 10)
    return Number.isFinite(parsedValue) && parsedValue > 0 ? parsedValue : undefined
  }

  function runAnalysis() {
    research.runBaixadaAnalysis({
      dataset_root: datasetRoot,
      output_root: outputRoot,
      start_date: startDate,
      end_date: endDate,
      source_model: sourceModel,
      years_per_chunk: Number.parseInt(yearsPerChunk, 10) || 1,
      request_delay_seconds: Number.parseFloat(requestDelaySeconds) || 0,
      retry_attempts: Number.parseInt(retryAttempts, 10) || 8,
      retry_max_delay_seconds: Number.parseFloat(retryMaxDelaySeconds) || 300,
      use_grid: useGrid,
      force_download: forceDownload,
      force_rebuild_outputs: forceRebuildOutputs,
      max_batches: parseOptionalLimit(maxBatches),
    })
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <ThermometerSun className="h-4 w-4 text-amber-300" aria-hidden="true" />
              {t('dashboard.research.baixada.title')}
            </CardTitle>
            <CardDescription>{t('dashboard.research.baixada.description')}</CardDescription>
          </div>
          <div className="flex flex-wrap gap-3">
            <a
              href={docsUrls.baixadaReport}
              target="_blank"
              rel="noreferrer"
              className={`inline-flex items-center justify-center gap-2 rounded-lg border border-zinc-800 px-4 py-2 text-sm font-medium transition-colors ${
                research.status.baixada_report_exists
                  ? 'text-zinc-200 hover:bg-zinc-900'
                  : 'pointer-events-none text-zinc-600'
              }`}
            >
              <FileText className="h-4 w-4" aria-hidden="true" />
              {t('dashboard.research.baixada.openReport')}
            </a>
            <button
              type="button"
              disabled={research.isAnalyzingBaixada}
              onClick={runAnalysis}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-sky-300 px-4 py-2 text-sm font-semibold text-zinc-950 transition-colors hover:bg-sky-200 disabled:cursor-wait disabled:opacity-60"
            >
              <Play className="h-4 w-4" aria-hidden="true" />
              {research.isAnalyzingBaixada ? t('dashboard.research.baixada.running') : t('dashboard.research.baixada.run')}
            </button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-3 lg:grid-cols-4">
          <label className="space-y-2">
            <span className="text-sm font-medium text-zinc-300">{t('dashboard.research.baixada.datasetRoot')}</span>
            <input value={datasetRoot} onChange={(event) => setDatasetRoot(event.target.value)} className="h-10 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm text-zinc-200 outline-none focus:ring-1 focus:ring-sky-500/60" />
          </label>
          <label className="space-y-2">
            <span className="text-sm font-medium text-zinc-300">{t('dashboard.research.baixada.outputRoot')}</span>
            <input value={outputRoot} onChange={(event) => setOutputRoot(event.target.value)} className="h-10 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm text-zinc-200 outline-none focus:ring-1 focus:ring-sky-500/60" />
          </label>
          <label className="space-y-2">
            <span className="text-sm font-medium text-zinc-300">{t('dashboard.research.baixada.source')}</span>
            <select value={sourceModel} onChange={(event) => setSourceModel(event.target.value)} className="h-10 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm text-zinc-200 outline-none focus:ring-1 focus:ring-sky-500/60">
              <option value="era5">ERA5</option>
              <option value="era5_land">ERA5-Land</option>
              <option value="best_match">Open-Meteo best match</option>
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-sm font-medium text-zinc-300">{t('dashboard.research.baixada.chunk')}</span>
            <input type="number" min="1" max="10" value={yearsPerChunk} onChange={(event) => setYearsPerChunk(event.target.value)} className="h-10 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm text-zinc-200 outline-none focus:ring-1 focus:ring-sky-500/60" />
          </label>
          <label className="space-y-2">
            <span className="text-sm font-medium text-zinc-300">{t('dashboard.research.baixada.requestDelay')}</span>
            <input type="number" min="0" step="0.5" value={requestDelaySeconds} onChange={(event) => setRequestDelaySeconds(event.target.value)} className="h-10 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm text-zinc-200 outline-none focus:ring-1 focus:ring-sky-500/60" />
          </label>
          <label className="space-y-2">
            <span className="text-sm font-medium text-zinc-300">{t('dashboard.research.baixada.retryAttempts')}</span>
            <input type="number" min="1" max="20" value={retryAttempts} onChange={(event) => setRetryAttempts(event.target.value)} className="h-10 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm text-zinc-200 outline-none focus:ring-1 focus:ring-sky-500/60" />
          </label>
          <label className="space-y-2">
            <span className="text-sm font-medium text-zinc-300">{t('dashboard.research.baixada.retryMaxDelay')}</span>
            <input type="number" min="1" max="3600" value={retryMaxDelaySeconds} onChange={(event) => setRetryMaxDelaySeconds(event.target.value)} className="h-10 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm text-zinc-200 outline-none focus:ring-1 focus:ring-sky-500/60" />
          </label>
          <label className="space-y-2">
            <span className="text-sm font-medium text-zinc-300">{t('dashboard.research.baixada.startDate')}</span>
            <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} className="h-10 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm text-zinc-200 outline-none focus:ring-1 focus:ring-sky-500/60" />
          </label>
          <label className="space-y-2">
            <span className="text-sm font-medium text-zinc-300">{t('dashboard.research.baixada.endDate')}</span>
            <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} className="h-10 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm text-zinc-200 outline-none focus:ring-1 focus:ring-sky-500/60" />
          </label>
          <label className="space-y-2">
            <span className="text-sm font-medium text-zinc-300">{t('dashboard.research.baixada.maxBatches')}</span>
            <input type="number" min="1" placeholder={t('dashboard.research.baixada.allBatches')} value={maxBatches} onChange={(event) => setMaxBatches(event.target.value)} className="h-10 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm text-zinc-200 outline-none placeholder:text-zinc-600 focus:ring-1 focus:ring-sky-500/60" />
          </label>
          <div className="flex flex-col justify-end gap-2">
            <label className="flex items-center gap-2 text-sm text-zinc-300">
              <input type="checkbox" checked={useGrid} onChange={(event) => setUseGrid(event.target.checked)} className="h-4 w-4 accent-sky-300" />
              {t('dashboard.research.baixada.useGrid')}
            </label>
            <label className="flex items-center gap-2 text-sm text-zinc-300">
              <input type="checkbox" checked={forceDownload} onChange={(event) => setForceDownload(event.target.checked)} className="h-4 w-4 accent-sky-300" />
              {t('dashboard.research.baixada.forceDownload')}
            </label>
            <label className="flex items-center gap-2 text-sm text-zinc-300">
              <input type="checkbox" checked={forceRebuildOutputs} onChange={(event) => setForceRebuildOutputs(event.target.checked)} className="h-4 w-4 accent-sky-300" />
              {t('dashboard.research.baixada.forceRebuild')}
            </label>
          </div>
        </div>

        <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4 text-sm text-amber-100">
          <div className="flex gap-3">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" aria-hidden="true" />
            <p>{t('dashboard.research.baixada.reanalysisNote')}</p>
          </div>
        </div>

        {result ? (
          <div className="space-y-6">
            <div className="grid gap-3 md:grid-cols-4">
              <MetricBlock label={t('dashboard.research.baixada.slope')} value={`${formatClimateNumber(trend.slope_per_decade)} C/dec`} hint={`IC95% ${formatClimateNumber(trend.ci95_low_per_decade)} a ${formatClimateNumber(trend.ci95_high_per_decade)}`} icon={LineChart} tone={trend.slope_per_decade > 0 ? 'warning' : 'default'} />
              <MetricBlock label={t('dashboard.research.baixada.pValue')} value={formatClimateNumber(trend.p_value, 5)} hint={`R2 ${formatClimateNumber(trend.r2, 3)}`} icon={BarChart3} tone={trend.significant ? 'success' : 'warning'} />
              <MetricBlock label={t('dashboard.research.baixada.coverage')} value={coverage.hourly_rows ?? '-'} hint={`${coverage.monthly_gap_count ?? 0} ${t('dashboard.research.baixada.gaps')}`} icon={Database} tone="default" />
              <MetricBlock label={t('dashboard.research.baixada.confidence')} value={trend.confidence ?? '-'} hint={trend.significant ? t('dashboard.research.baixada.significant') : t('dashboard.research.baixada.notSignificant')} icon={CheckCircle2} tone={trend.significant ? 'success' : 'warning'} />
            </div>

            <div className="grid gap-4 lg:grid-cols-[1fr_0.9fr]">
              <div className="rounded-lg border border-zinc-800 bg-zinc-950/40 p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <p className="font-medium text-zinc-100">{t('dashboard.research.baixada.regionalConclusion')}</p>
                  <Badge variant={confidenceVariant}>{trend.interpretation ?? '-'}</Badge>
                </div>
                <p className="text-sm leading-6 text-zinc-400">
                  {t('dashboard.research.baixada.conclusionText', {
                    start: result.period?.start_year ?? '-',
                    end: result.period?.end_year ?? '-',
                    slope: formatClimateNumber(trend.slope_per_decade),
                    pValue: formatClimateNumber(trend.p_value, 5),
                  })}
                </p>
              </div>

              <div className="rounded-lg border border-zinc-800 bg-zinc-950/40 p-4">
                <p className="mb-3 font-medium text-zinc-100">{t('dashboard.research.baixada.outputs')}</p>
                <OutputList outputs={result.outputs} />
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-2">
              <div className="space-y-3">
                <p className="font-medium text-zinc-100">{t('dashboard.research.baixada.periodComparison')}</p>
                <CompactRecords records={result.period_comparison ?? []} columns={['period', 'temperature_mean', 'precipitation_sum_mean', 'coverage_ratio_mean']} emptyLabel={t('dashboard.research.baixada.noRecords')} />
              </div>
              <div className="space-y-3">
                <p className="font-medium text-zinc-100">{t('dashboard.research.baixada.cityTrends')}</p>
                <CompactRecords records={result.city_trends ?? []} columns={['city', 'slope_per_decade', 'p_value', 'confidence']} emptyLabel={t('dashboard.research.baixada.noRecords')} />
              </div>
            </div>
          </div>
        ) : (
          <EmptyState title={t('dashboard.research.baixada.emptyTitle')} description={t('dashboard.research.baixada.emptyDescription')} />
        )}
      </CardContent>
    </Card>
  )
}

function ResearchSection({ research }) {
  const { t } = useTranslation()
  const [pipelineLimit, setPipelineLimit] = useState('')
  const status = research.status

  function parseOptionalLimit(value) {
    const parsedValue = Number.parseInt(value, 10)
    return Number.isFinite(parsedValue) && parsedValue > 0 ? parsedValue : undefined
  }

  const pipelineMaxImages = parseOptionalLimit(pipelineLimit)

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h2 className="text-3xl font-semibold tracking-tight text-zinc-100">{t('dashboard.research.title')}</h2>
        <p className="max-w-2xl text-zinc-400">{t('dashboard.research.description')}</p>
      </div>

      {research.error ? (
        <div className="rounded-xl border border-red-900/50 bg-red-950/40 p-4 text-sm text-red-200">
          {research.error}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard
          label={t('dashboard.research.stats.images')}
          value={research.isLoading ? '...' : status.image_count}
          hint={status.latest_image ?? t('dashboard.research.stats.noImages')}
          tone="outline"
        />
        <StatCard
          label={t('dashboard.research.stats.rows')}
          value={research.isLoading ? '...' : status.climate_dataset_rows}
          hint={status.climate_dataset_exists ? t('dashboard.research.stats.csvReady') : t('dashboard.research.stats.csvMissing')}
          tone={status.climate_dataset_exists ? 'success' : 'warning'}
        />
        <StatCard
          label={t('dashboard.research.stats.cache')}
          value="SQLite"
          hint={t('dashboard.research.stats.incremental')}
          tone="accent"
        />
        <StatCard
          label={t('dashboard.research.stats.jobs')}
          value={status.jobs.filter((job) => job.status === 'running').length}
          hint={research.hasRunningJob ? t('dashboard.research.stats.running') : t('dashboard.research.stats.idle')}
          tone={research.hasRunningJob ? 'warning' : 'outline'}
        />
      </div>

      <div className="grid gap-3 lg:grid-cols-4">
        <PipelineSourceRow icon={Satellite} title="Sentinel-2" status="2015+" description={t('dashboard.research.sources.sentinel2')} />
        <PipelineSourceRow icon={ImageIcon} title="Landsat" status="1972+" description={t('dashboard.research.sources.landsat')} />
        <PipelineSourceRow icon={Database} title="ERA5 / Open-Meteo" status="1940+" description={t('dashboard.research.sources.weather')} />
        <PipelineSourceRow icon={Layers3} title={t('dashboard.research.sources.labelsTitle')} status="hybrid" description={t('dashboard.research.sources.labels')} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Satellite className="h-4 w-4 text-sky-300" aria-hidden="true" />
              {t('dashboard.research.satellite.title')}
            </CardTitle>
            <CardDescription>{t('dashboard.research.satellite.description')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div>
              <button
                type="button"
                disabled={research.isStarting || !status.cdse_credentials_configured}
                onClick={() => research.runSatelliteDownload({ dry_run: false, max_items: undefined, overwrite: false })}
                className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-zinc-100 px-4 py-2 text-sm font-medium text-zinc-950 transition-colors hover:bg-zinc-200 disabled:cursor-wait disabled:opacity-60"
              >
                <Download className="h-4 w-4" aria-hidden="true" />
                {t('dashboard.research.satellite.download')}
              </button>
            </div>

            {!status.cdse_credentials_configured ? (
              <p className="text-sm text-zinc-500">{t('dashboard.research.satellite.credentialsHint')}</p>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings2 className="h-4 w-4 text-sky-300" aria-hidden="true" />
              {t('dashboard.research.pipeline.title')}
            </CardTitle>
            <CardDescription>{t('dashboard.research.pipeline.description')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <label className="block space-y-2">
              <span className="text-sm font-medium text-zinc-300">{t('dashboard.research.pipeline.limit')}</span>
              <input
                type="number"
                min="1"
                placeholder={t('dashboard.research.pipeline.allImages')}
                value={pipelineLimit}
                onChange={(event) => setPipelineLimit(event.target.value)}
                className="h-10 w-full rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm text-zinc-200 outline-none placeholder:text-zinc-600 focus:ring-1 focus:ring-zinc-700"
              />
            </label>

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                disabled={research.isStarting || status.image_count === 0}
                onClick={() => research.runClimateDatasetBuild({ device: 'auto', max_images: pipelineMaxImages })}
                className="inline-flex items-center gap-2 rounded-lg bg-zinc-100 px-4 py-2 text-sm font-medium text-zinc-950 transition-colors hover:bg-zinc-200 disabled:cursor-wait disabled:opacity-60"
              >
                <TableProperties className="h-4 w-4" aria-hidden="true" />
                {t('dashboard.research.pipeline.build')}
              </button>
              <a
                href={docsUrls.climateDatasetCsv}
                className={`inline-flex items-center gap-2 rounded-lg border border-zinc-800 px-4 py-2 text-sm font-medium transition-colors ${
                  status.climate_dataset_exists
                    ? 'text-zinc-200 hover:bg-zinc-900'
                    : 'pointer-events-none text-zinc-600'
                }`}
              >
                <FileText className="h-4 w-4" aria-hidden="true" />
                {t('dashboard.research.pipeline.downloadCsv')}
              </a>
            </div>

            <p className="text-sm text-zinc-500">
              {t('dashboard.research.pipeline.path', { path: status.climate_dataset_path || '-' })}
            </p>
          </CardContent>
        </Card>
      </div>

      <ClimateSignalCard research={research} />

      <BaixadaAnalysisCard research={research} />

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-4">
            <div>
              <CardTitle>{t('dashboard.research.jobs.title')}</CardTitle>
              <CardDescription>{t('dashboard.research.jobs.description')}</CardDescription>
            </div>
            <button
              type="button"
              onClick={research.refresh}
              className="inline-flex items-center gap-2 rounded-lg border border-zinc-800 px-3 py-1.5 text-sm text-zinc-300 transition-colors hover:bg-zinc-900"
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              {t('dashboard.research.jobs.refresh')}
            </button>
          </div>
        </CardHeader>
        <CardContent>
          {status.jobs.length ? (
            <div className="space-y-3">
              {status.jobs.map((job) => (
                <div key={job.key} className="flex flex-col gap-2 rounded-xl border border-zinc-800 bg-zinc-900/20 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-zinc-100">{job.label}</p>
                      <ResearchJobBadge status={job.status} />
                    </div>
                    <p className="mt-1 text-sm text-zinc-500">{job.message}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <p className="text-xs text-zinc-600">
                      {job.finished_at ? formatDateTime(job.finished_at) : job.started_at ? formatDateTime(job.started_at) : '-'}
                    </p>
                    <button
                      type="button"
                      disabled={research.isStarting}
                      onClick={() => research.clearJob(job.key)}
                      className="rounded-lg border border-zinc-800 px-3 py-1.5 text-xs font-medium text-zinc-400 transition-colors hover:bg-zinc-900 hover:text-zinc-100 disabled:cursor-wait disabled:opacity-60"
                    >
                      {t('dashboard.research.jobs.clear')}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title={t('dashboard.research.jobs.emptyTitle')} description={t('dashboard.research.jobs.emptyDescription')} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export function HomePage() {
  const { health, isLoading: isHealthLoading } = useHealth()
  const { history, isLoading: isHistoryLoading, error: historyError, filters, setFilter, refresh } = useHistory()
  const research = useResearch()
  const [activeTab, setActiveTab] = useState('dashboard')
  const { t } = useTranslation()

  const predictionState = usePrediction(() => {
    refresh()
    setActiveTab('dashboard')
  })

  return (
    <PageShell>
      <header className="sticky top-0 z-30 border-b border-zinc-800/50 bg-zinc-950/80 backdrop-blur-md">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 h-16">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-700 bg-zinc-900 text-sm font-semibold text-zinc-200">
              A
            </div>
            <span className="text-sm font-medium text-zinc-200">Aeris</span>
            <Badge variant={isHealthLoading ? 'outline' : health.status === 'online' ? 'success' : 'destructive'} className="ml-2">
               {isHealthLoading ? t('health.loading') : health.status}
            </Badge>
          </div>
          <div className="flex items-center gap-6">
            <div className="hidden sm:flex items-center gap-4 border-r border-zinc-800 pr-6">
              <a href={docsUrls.swagger} target="_blank" rel="noreferrer" className="text-sm font-medium text-zinc-400 hover:text-zinc-100 transition-colors">
                Swagger API
              </a>
              <a href={docsUrls.redoc} target="_blank" rel="noreferrer" className="text-sm font-medium text-zinc-400 hover:text-zinc-100 transition-colors">
                ReDoc
              </a>
            </div>
            <LanguageSwitcher />
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl px-6 py-12">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList variant="line" className="mb-10 w-full justify-start border-b border-zinc-800">
            <TabsTrigger value="dashboard">
              {t('dashboard.tabs.overview')}
            </TabsTrigger>
            <TabsTrigger value="prediction">
              {t('dashboard.tabs.inference')}
            </TabsTrigger>
            <TabsTrigger value="realtime">
              {t('dashboard.tabs.realtime')}
            </TabsTrigger>
            <TabsTrigger value="research">
              {t('dashboard.tabs.research')}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="mt-0">
             <DashboardSection
                history={history}
                historyError={historyError}
                isLoading={isHistoryLoading}
                filters={filters}
                setFilter={setFilter}
                health={health}
              />
          </TabsContent>
          <TabsContent value="prediction" className="mt-0">
             <InferenceSection
                prediction={predictionState.prediction}
                mode={predictionState.mode}
                setMode={predictionState.setMode}
                selectedFile={predictionState.selectedFile}
                setSelectedFile={predictionState.setSelectedFile}
                base64Input={predictionState.base64Input}
                setBase64Input={predictionState.setBase64Input}
                previewUrl={predictionState.previewUrl}
                error={predictionState.error}
                isSubmitting={predictionState.isSubmitting}
                submit={predictionState.submit}
                reset={predictionState.reset}
              />
          </TabsContent>
          <TabsContent value="realtime" className="mt-0">
             <RealtimeSection onSaved={refresh} />
          </TabsContent>
          <TabsContent value="research" className="mt-0">
             <ResearchSection research={research} />
          </TabsContent>
        </Tabs>
      </main>
    </PageShell>
  )
}
