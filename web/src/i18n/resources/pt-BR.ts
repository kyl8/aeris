const ptBR = {
  translation: {
    dashboard: {
      overview: {
        title: 'Visão Geral',
        description: 'Monitore o desempenho e a atividade do motor de inferência Aeris Climate Stack em tempo real.',
        stats: {
          totalPredictions: 'Total Predições',
          totalPredictionsHint: 'Na API',
          confidence: 'Confiança',
          confidenceHint: 'Média',
          topClass: 'Top Classe',
          topClassHint: 'Mais frequente',
          lastInference: 'Última Inferência',
          lastInferenceNone: 'Nenhuma',
        }
      },
      realtime: {
        title: 'Inferência em tempo real',
        description: 'Conecte sua webcam para fazer detecção e classificação ao vivo.',
        active: 'Câmera ativa',
        offline: 'Câmera offline',
        start: 'Iniciar câmera',
        stop: 'Parar câmera',
        standby: 'Câmera em espera',
        demoLabel: 'Pessoa 0.89',
        error: {
          cameraAccess: 'Não foi possível acessar a câmera. Verifique as permissões.',
        },
      },
      distribution: {
        title: 'Distribuição de Classes',
        description: 'Detalhamento dos fenômenos climáticos reconhecidos em todas as imagens processadas.',
        emptyTitle: 'Sem dados de distribuição',
        emptyDescription: 'Processe uma imagem para gerar análises de distribuição.',
        total: 'Total'
      },
      activity: {
        title: 'Atividade de Inferência',
        description: 'Volume de predições processadas ao longo do tempo.',
        emptyTitle: 'Sem dados de linha do tempo',
        emptyDescription: 'A atividade aparecerá aqui assim que as predições forem feitas.',
        predictions: 'predições'
      },
      history: {
        title: 'Histórico de Predições',
        allClasses: 'Todas as Classes',
        table: {
          class: 'Classe',
          confidence: 'Confiança',
          model: 'Modelo',
          timestamp: 'Data/Hora'
        },
        error: 'Erro ao carregar histórico',
        emptyTitle: 'Nenhum histórico encontrado',
        emptyDescription: 'Ajuste seus filtros ou envie uma nova imagem para inferência.'
      },
      inference: {
        title: 'Executar Inferência',
        description: 'Envie uma imagem ou forneça uma string Base64 para analisar fenômenos climáticos.',
        tabs: {
          upload: 'Upload',
          base64: 'Base64'
        },
        input: {
          title: 'Imagem de Entrada',
          clickUpload: 'Clique para enviar',
          dragDrop: 'ou arraste e solte',
          supportedFiles: 'PNG, JPG ou WebP',
          pasteBase64: 'Cole os dados da imagem em base64 aqui...',
          processing: 'Processando...',
          submit: 'Executar Inferência',
          clear: 'Limpar'
        },
        results: {
          title: 'Resultados',
          detectedClass: 'Classe Detectada',
          modelInfo: 'Informações do Modelo',
          latency: 'ms latência',
          waitingTitle: 'Aguardando resultados...',
          waitingDescription: 'Envie a imagem para ver os dados da predição.'
        }
      },
      docs: {
        title: 'Documentação da API',
        description: 'Explore o esquema da API REST do Aeris nativamente usando Swagger ou ReDoc.',
      },
      tabs: {
        overview: 'Visão Geral',
        inference: 'Inferência',
        realtime: 'Tempo real',
        docs: 'Documentação'
      }
    },
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
    classes: {
      cloudyOvercast: 'Nublado',
      foggyHazy: 'Neblina',
      rainStorm: 'Chuva ou tempestade',
      snowFrosty: 'Neve ou geada',
      sunClear: 'Sol ou céu limpo',
      dew: 'Orvalho',
      fogsmog: 'Neblina e fumaça',
      frost: 'Geada',
      glaze: 'Camada de gelo',
      hail: 'Granizo',
      lightning: 'Raio',
      rain: 'Chuva',
      rainbow: 'Arco-íris',
      rime: 'Geada branca',
      sandstorm: 'Tempestade de areia',
      snow: 'Neve',
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
