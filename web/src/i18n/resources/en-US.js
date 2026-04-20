const enUS = {
  translation: {
    header: {
      brand: 'Aeris',
      search: 'Search docs',
      openApi: 'Open docs',
      language: {
        label: 'Language',
        options: {
          ptBR: 'Portuguese',
          enUS: 'English',
        },
      },
      nav: {
        gettingStarted: 'Getting started',
        apiReference: 'API reference',
        playground: 'Playground',
      },
    },
    sidebar: {
      title: 'On this page',
      preview: 'Local preview',
      items: {
        overview: 'Overview',
        gettingStarted: 'Getting started',
        apiReference: 'API reference',
        playground: 'Playground',
        structure: 'Structure',
      },
    },
    health: {
      loading: 'checking...',
      status: {
        ok: 'online',
        offline: 'offline',
      },
    },
    hero: {
      badge: 'Aeris documentation',
      title: 'Aeris Documentation.',
      description: 'Climate analysis and forecasting API built with FastAPI and PyTorch.',
      getStarted: 'Get started',
      openSwagger: 'Open Swagger UI',
      viewRedoc: 'View ReDoc',
      apiStatus: 'API status: {{status}}',
    },
    sections: {
      gettingStarted: {
        eyebrow: 'Getting started',
        title: 'Run the project locally',
        description:
          'The backend uses uv and the frontend uses bun. Keep one terminal for each side while developing.',
      },
      structure: {
        eyebrow: 'Structure',
        title: 'Repository layout',
        description:
          'UI, hooks and content are separated on the frontend so the page stays readable.',
        treeTitle: 'Project tree',
        notesTitle: 'Notes',
      },
      apiReference: {
        eyebrow: 'Reference',
        title: 'API endpoints',
        description:
          'FastAPI generates Swagger UI and ReDoc automatically, so there is no manual OpenAPI file to maintain.',
      },
      playground: {
        eyebrow: 'Interactive',
        title: 'Try the prediction endpoint',
        description: 'Enter a numeric vector, send it to the backend and inspect the response.',
        endpointLabel: 'POST /api/predict',
        fieldLabel: 'Numeric vector',
        placeholder: '12, 18, 24',
        running: 'Running...',
        submit: 'Run prediction',
        valuesDetected: '{{count}} values detected',
      },
    },
    api: {
      health: {
        description: 'Returns the current service status.',
      },
      predict: {
        description: 'Receives a numeric feature vector and returns the inference payload.',
      },
      docs: {
        description: 'Swagger UI generated automatically by FastAPI.',
      },
      redoc: {
        description: 'Alternate OpenAPI view for reference.',
      },
    },
    gettingStarted: {
      backendLabel: 'Backend',
      backendCommand: 'uv sync\nuv run uvicorn api.app:app --reload',
      frontendLabel: 'Frontend',
      frontendCommand: 'cd web\nbun install\nbun run dev',
    },
    structure: {
      backendTitle: 'Backend grouped together',
      backendText: 'FastAPI, core and schemas live under api/ so the codebase stays predictable.',
      frontendTitle: 'Frontend separated',
      frontendText: 'UI, hooks and content stay isolated in web/src/ so the layout stays readable.',
      weightsTitle: 'Model artifacts',
      weightsText: 'When a trained model exists, place the weights in api/weights/.',
    },
    result: {
      title: 'Result',
      emptyTitle: 'The API response appears here after submission.',
      emptyDescription:
        'After running inference, you will see the model, prediction and normalized vector here.',
      emptyState: 'No data yet.',
      model: 'Model',
      version: 'Version',
      prediction: 'Prediction',
      artifact: 'Artifact',
      normalized: 'Normalized vectors',
      features: 'features',
      placeholderArtifact: 'no artifact',
    },
    errors: {
      emptyFeatures: 'Enter at least one valid number.',
      requestFailed: 'Could not run the prediction.',
    },
  },
}

export default enUS