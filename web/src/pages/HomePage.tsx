import { useMemo, useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'

import { PageShell } from '../components/layout/PageShell'
import { LanguageSwitcher } from '../components/layout/LanguageSwitcher'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs'
import { Table, TableHeader, TableRow, TableHead, TableBody, TableCell } from '../components/ui/table'
import { Badge } from '../components/ui/badge'
import { useHealth } from '../hooks/useHealth'
import { useHistory } from '../hooks/useHistory'
import { usePrediction } from '../hooks/usePrediction'
import {
  buildDistributionData,
  buildTimelineData,
  capitalizeLabel,
  formatConfidence,
  formatDateTime,
  summarizeHistory,
} from '../lib/dashboard'
import { docsUrls } from '../lib/api'

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
                className="px-4 py-2 bg-white text-black text-sm font-medium rounded-lg hover:bg-zinc-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-900/30">
                  <p className="text-xs text-zinc-500 mb-1">{t('dashboard.inference.results.detectedClass')}</p>
                  <p className="text-lg font-medium text-zinc-100 flex items-center gap-2">
                    {capitalizeLabel(prediction.class)}
                    <Badge variant="success" className="text-[10px] py-0">{formatConfidence(prediction.confidence)}</Badge>
                  </p>
                </div>
                <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-900/30">
                  <p className="text-xs text-zinc-500 mb-1">{t('dashboard.inference.results.modelInfo')}</p>
                  <p className="text-sm text-zinc-300">{prediction.model_name}</p>
                  <p className="text-xs text-zinc-500 mt-1">{prediction.inference_ms}{t('dashboard.inference.results.latency')}</p>
                </div>
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

function RealtimeSection() {
  const { t } = useTranslation()
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isActive, setIsActive] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let stream: MediaStream | null = null

    async function startCamera() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
        if (videoRef.current) {
          videoRef.current.srcObject = stream
        }
        setError(null)
      } catch (err) {
        setError(t('dashboard.realtime.error.cameraAccess', 'Failed to access camera. Please ensure permissions are granted.'))
        setIsActive(false)
      }
    }

    if (isActive) {
      startCamera()
    } else {
      if (videoRef.current && videoRef.current.srcObject) {
        const currentStream = videoRef.current.srcObject as MediaStream
        currentStream.getTracks().forEach((track) => track.stop())
        videoRef.current.srcObject = null
      }
    }

    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop())
      }
    }
  }, [isActive])

  // Fake YOLO-style bounding boxes simulation overlay since we don't have websocket backend yet.
  // In a real implementation, we would capture frames from the video to a canvas, send via WS,
  // and draw the returned bounding boxes.
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <h2 className="text-3xl font-semibold tracking-tight text-zinc-100">{t('dashboard.realtime.title', 'Realtime Inference')}</h2>
        <p className="text-zinc-400 max-w-xl">
          {t('dashboard.realtime.description', 'Connect your webcam to perform live object detection and classification.')}
        </p>
      </div>

      <Card className="overflow-hidden border-zinc-800 bg-zinc-950">
        <CardHeader className="flex flex-col gap-4 border-b border-zinc-800/50 bg-zinc-900/20 pb-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-center gap-3">
            <div className={`h-2.5 w-2.5 rounded-full ${isActive ? 'bg-emerald-500 animate-pulse' : 'bg-zinc-600'}`} />
            <CardTitle className="text-base">{isActive ? t('dashboard.realtime.active') : t('dashboard.realtime.offline')}</CardTitle>
          </div>
          <button
            onClick={() => setIsActive(!isActive)}
            className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-colors ${
              isActive 
                ? 'bg-red-500/10 text-red-500 hover:bg-red-500/20' 
                : 'bg-white text-black hover:bg-zinc-200'
            }`}
          >
            {isActive ? t('dashboard.realtime.stop', 'Stop Camera') : t('dashboard.realtime.start', 'Start Camera')}
          </button>
        </CardHeader>
        <CardContent className="p-0">
          <div className="relative aspect-video w-full bg-zinc-950 flex items-center justify-center">
            {error ? (
              <div className="text-sm text-red-400 p-4 text-center">{error}</div>
            ) : !isActive ? (
              <div className="text-zinc-500 text-sm flex flex-col items-center gap-2">
                <svg className="w-8 h-8 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                {t('dashboard.realtime.standby', 'Camera is on standby')}
              </div>
            ) : (
              <>
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="absolute inset-0 w-full h-full object-cover"
                />
                <canvas 
                  ref={canvasRef} 
                  className="absolute inset-0 w-full h-full pointer-events-none" 
                />
                
                {/* Temporary Simulated Bounding Box for Demonstration */}
                <div className="absolute top-1/4 left-1/4 w-48 h-64 border-2 border-emerald-500 pointer-events-none">
                  <div className="absolute -top-6 left-0 bg-emerald-500 text-black text-[10px] font-bold px-1.5 py-0.5 whitespace-nowrap">
                    {t('dashboard.realtime.demoLabel', 'person 0.89')}
                  </div>
                </div>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export function HomePage() {
  const { health, isLoading: isHealthLoading } = useHealth()
  const { history, isLoading: isHistoryLoading, error: historyError, filters, setFilter, refresh } = useHistory()
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
             <RealtimeSection />
          </TabsContent>
        </Tabs>
      </main>
    </PageShell>
  )
}