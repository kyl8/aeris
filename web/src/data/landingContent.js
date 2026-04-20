export const docsLinks = {
  swagger: 'http://127.0.0.1:8000/docs',
  redoc: 'http://127.0.0.1:8000/redoc',
}

export const headerNavItems = [
  { href: '#getting-started', labelKey: 'header.nav.gettingStarted' },
  { href: '#api-reference', labelKey: 'header.nav.apiReference' },
  { href: '#playground', labelKey: 'header.nav.playground' },
]

export const sidebarItems = [
  { id: 'overview', labelKey: 'sidebar.items.overview' },
  { id: 'getting-started', labelKey: 'sidebar.items.gettingStarted' },
  { id: 'api-reference', labelKey: 'sidebar.items.apiReference' },
  { id: 'playground', labelKey: 'sidebar.items.playground' },
  { id: 'structure', labelKey: 'sidebar.items.structure' },
]

export const quickStartCommands = [
  {
    titleKey: 'gettingStarted.backendLabel',
    commandKey: 'gettingStarted.backendCommand',
  },
  {
    titleKey: 'gettingStarted.frontendLabel',
    commandKey: 'gettingStarted.frontendCommand',
  },
]

export const apiReference = [
  {
    method: 'GET',
    path: '/health',
    descriptionKey: 'api.health.description',
  },
  {
    method: 'POST',
    path: '/api/predict',
    descriptionKey: 'api.predict.description',
  },
  {
    method: 'GET',
    path: '/docs',
    descriptionKey: 'api.docs.description',
  },
  {
    method: 'GET',
    path: '/redoc',
    descriptionKey: 'api.redoc.description',
  },
]

export const projectTree = `pyproject.toml
.venv/
api/
  app.py
  core/
  routes/
  schemas/
  weights/
web/
  src/
  public/`

export const structureNotes = [
  {
    titleKey: 'structure.backendTitle',
    textKey: 'structure.backendText',
  },
  {
    titleKey: 'structure.frontendTitle',
    textKey: 'structure.frontendText',
  },
  {
    titleKey: 'structure.weightsTitle',
    textKey: 'structure.weightsText',
  },
]