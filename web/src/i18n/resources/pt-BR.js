const ptBR = {
  translation: {
    header: {
      brand: 'Aeris',
      search: 'Buscar na documentação',
      openApi: 'Abrir documentação',
      language: {
        label: 'Idioma',
        options: {
          ptBR: 'Português',
          enUS: 'Inglês',
        },
      },
      nav: {
        gettingStarted: 'Primeiros passos',
        apiReference: 'Referência da API',
        playground: 'Área de testes',
      },
    },
    sidebar: {
      title: 'Nesta página',
      preview: 'Pré-visualização local',
      items: {
        overview: 'Visão geral',
        gettingStarted: 'Primeiros passos',
        apiReference: 'Referência da API',
        playground: 'Área de testes',
        structure: 'Estrutura',
      },
    },
    health: {
      loading: 'checando...',
      status: {
        ok: 'no ar',
        offline: 'fora do ar',
      },
    },
    hero: {
      badge: 'Documentação do Aeris',
      title: 'Documentação do Aeris.',
      description: 'API de análise climática e previsão construída com FastAPI e Pytorch.',
      getStarted: 'Começar',
      openSwagger: 'Abrir Swagger UI',
      viewRedoc: 'Ver ReDoc',
      apiStatus: 'Estado da API: {{status}}',
    },
    sections: {
      gettingStarted: {
        eyebrow: 'Primeiros passos',
        title: 'Execute o projeto localmente',
        description:
          'O backend usa uv e o frontend usa bun. Mantenha um terminal para cada lado enquanto desenvolve.',
      },
      structure: {
        eyebrow: 'Estrutura',
        title: 'Layout do repositório',
        description:
          'UI, hooks e conteúdo ficam separados no frontend para a página continuar legível.',
        treeTitle: 'Árvore do projeto',
        notesTitle: 'Notas',
      },
      apiReference: {
        eyebrow: 'Referência',
        title: 'Endpoints da API',
        description:
          'O FastAPI gera Swagger UI e ReDoc automaticamente, então não há arquivo OpenAPI manual para manter.',
      },
      playground: {
        eyebrow: 'Área de testes',
        title: 'Teste o endpoint de predição',
        description: 'Digite um vetor numérico, envie para o backend e veja a resposta.',
        endpointLabel: 'POST /api/predict',
        fieldLabel: 'Vetor numérico',
        placeholder: '12, 18, 24',
        running: 'Executando...',
        submit: 'Executar predição',
        valuesDetected: '{{count}} valores detectados',
      },
    },
    api: {
      health: {
        description: 'Retorna o status atual do serviço.',
      },
      predict: {
        description: 'Recebe um vetor numérico de features e retorna o payload de inferência.',
      },
      docs: {
        description: 'Swagger UI gerado automaticamente pelo FastAPI.',
      },
      redoc: {
        description: 'Visão alternativa da OpenAPI para referência.',
      },
    },
    gettingStarted: {
      backendLabel: 'Backend',
      backendCommand: 'uv sync\nuv run uvicorn api.app:app --reload',
      frontendLabel: 'Frontend',
      frontendCommand: 'cd web\nbun install\nbun run dev',
    },
    structure: {
      backendTitle: 'Backend organizado',
      backendText: 'FastAPI, core e schemas ficam agrupados em api/ para manter a base previsível.',
      frontendTitle: 'Frontend separado',
      frontendText: 'UI, hooks e conteúdo estão isolados em web/src/ para o layout continuar legível.',
      weightsTitle: 'Artefatos do modelo',
      weightsText: 'Quando houver um modelo treinado, coloque os pesos em api/weights/.',
    },
    result: {
      title: 'Resultado',
      emptyTitle: 'A resposta da API aparece aqui depois do envio.',
      emptyDescription:
        'Depois de executar a inferência, você verá aqui o modelo, a predição e o vetor normalizado.',
      emptyState: 'Sem dados ainda.',
      model: 'Modelo',
      version: 'Versão',
      prediction: 'Predição',
      artifact: 'Artefato',
      normalized: 'Vetores normalizados',
      features: 'atributos',
      placeholderArtifact: 'sem artefato',
    },
    errors: {
      emptyFeatures: 'Digite ao menos um número válido.',
      requestFailed: 'Não foi possível executar a predição.',
    },
  },
}

export default ptBR