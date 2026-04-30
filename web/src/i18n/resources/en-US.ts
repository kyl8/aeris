const enUS = {
  translation: {
    dashboard: {
      overview: {
        title: 'Overview',
        description: 'Monitor the performance and activity of the Aeris Climate Stack inference engine in real-time.',
        stats: {
          totalPredictions: 'Total Predictions',
          totalPredictionsHint: 'In API',
          confidence: 'Confidence',
          confidenceHint: 'Average',
          topClass: 'Top Class',
          topClassHint: 'Most frequent',
          lastInference: 'Last Inference',
          lastInferenceNone: 'None',
        }
      },
      realtime: {
        title: 'Realtime Inference',
        description: 'Connect your webcam to run live detection and classification.',
        active: 'Camera Active',
        offline: 'Camera Offline',
        start: 'Start Camera',
        stop: 'Stop Camera',
        standby: 'Camera is on standby',
        demoLabel: 'Person 0.89',
        error: {
          cameraAccess: 'Failed to access camera. Please ensure permissions are granted.',
        },
      },
      distribution: {
        title: 'Class Distribution',
        description: 'Breakdown of recognized climate phenomena across all processed images.',
        emptyTitle: 'No distribution data',
        emptyDescription: 'Process an image to generate distribution analytics.',
        total: 'Total'
      },
      activity: {
        title: 'Inference Activity',
        description: 'Volume of predictions processed over time.',
        emptyTitle: 'No timeline data',
        emptyDescription: 'Activity will appear here once predictions are made.',
        predictions: 'predictions'
      },
      history: {
        title: 'Prediction History',
        allClasses: 'All Classes',
        table: {
          class: 'Class',
          confidence: 'Confidence',
          model: 'Model',
          timestamp: 'Timestamp'
        },
        error: 'Error Loading History',
        emptyTitle: 'No history found',
        emptyDescription: 'Adjust your filters or submit a new image for inference.'
      },
      inference: {
        title: 'Run Inference',
        description: 'Upload an image or provide a Base64 string to analyze climate phenomena using our models.',
        tabs: {
          upload: 'Upload',
          base64: 'Base64'
        },
        input: {
          title: 'Input Image',
          clickUpload: 'Click to upload',
          dragDrop: 'or drag and drop',
          supportedFiles: 'PNG, JPG or WebP',
          pasteBase64: 'Paste base64 image data here...',
          processing: 'Processing...',
          submit: 'Run Inference',
          clear: 'Clear'
        },
        results: {
          title: 'Results',
          detectedClass: 'Detected Class',
          modelInfo: 'Model Info',
          latency: 'ms latency',
          waitingTitle: 'Waiting for results...',
          waitingDescription: 'Submit the image to see prediction data.'
        }
      },
      docs: {
        title: 'API Documentation',
        description: 'Explore the Aeris REST API schema natively using Swagger or ReDoc.',
      },
      tabs: {
        overview: 'Overview',
        inference: 'Inference',
        realtime: 'Realtime',
        docs: 'Documentation'
      }
    },
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
    classes: {
      cloudyOvercast: 'Cloudy or overcast',
      foggyHazy: 'Foggy or hazy',
      rainStorm: 'Rain or storm',
      snowFrosty: 'Snow or frosty',
      sunClear: 'Sun or clear',
      dew: 'Dew',
      fogsmog: 'Fog/Smog',
      frost: 'Frost',
      glaze: 'Glaze',
      hail: 'Hail',
      lightning: 'Lightning',
      rain: 'Rain',
      rainbow: 'Rainbow',
      rime: 'Rime',
      sandstorm: 'Sandstorm',
      snow: 'Snow',
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
