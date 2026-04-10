# Plano de Migracao: Streamlit -> FastAPI + HTMX

## Objetivo

Substituir a interface atual baseada em Streamlit por uma aplicacao web baseada em FastAPI, Jinja2 e HTMX, preservando:

- analise de planilha Safe Notos
- dashboard e visoes por deck
- wiki de entidades da rede
- modulo de infraestrutura com CRUD e importacao
- graficos Plotly e exportacoes CSV

A migracao deve ser incremental. O Streamlit continua operacional enquanto a nova stack nasce em paralelo.

## Diagnostico do estado atual

### Pontos de entrada

- `network_mapping_app.py`
  - configuracao global da pagina
  - upload principal da planilha
  - roteamento entre mapeamento e infraestrutura
- `app/views/infra_view.py`
  - subroteador interno do modulo de infraestrutura
  - forte dependencia de `st.session_state`, `st.query_params` e `st.rerun`

### Acoplamentos que precisam ser removidos

1. Cache dependente de Streamlit
   - `app/data.py`
   - `app/graphs.py`

2. Estado de navegacao dependente de Streamlit
   - `app/ui.py`
   - `app/views/wiki_view.py`
   - `app/views/infra_view.py`

3. Renderizacao misturada com regra de negocio
   - `app/views/dashboard.py`
   - `app/views/deck_view.py`
   - `app/views/wiki_view.py`
   - `app/views/import_view.py`

4. HTML inline espalhado nas views
   - componentes visualmente reutilizaveis hoje nao existem como templates

### Partes reaproveitaveis

- persistencia SQLite em `app/infra_db.py`
- pipeline de importacao em `app/infra_import.py`
- parsing e normalizacao da planilha em `app/data.py`
- construcao de grafos em `app/graphs.py`
- CSS e componentes conceituais em `app/config.py` e `app/ui.py`

## Arquitetura alvo

### Stack

- FastAPI para rotas HTTP e API server-side
- Jinja2 para templates HTML
- HTMX para interacao parcial sem SPA
- SQLite mantido como armazenamento local
- Plotly mantido para visualizacoes mais ricas
- Uvicorn como servidor ASGI

### Estrutura proposta

```text
net-mapper/
  app/
    domain/
      __init__.py
      mapping_models.py
      infra_models.py
    services/
      __init__.py
      mapping_service.py
      wiki_service.py
      infra_service.py
      import_service.py
      graph_service.py
      cache_service.py
    repositories/
      __init__.py
      infra_repository.py
    web/
      __init__.py
      main.py
      deps.py
      routers/
        __init__.py
        pages.py
        mapping.py
        wiki.py
        infra.py
        imports.py
      templates/
        base.html
        partials/
          alerts.html
          metrics.html
          breadcrumbs.html
          table.html
          plotly.html
          patch_panel.html
          rack_diagram.html
        pages/
          home.html
          mapping_dashboard.html
          mapping_deck.html
          wiki_index.html
          wiki_switch.html
          wiki_panel.html
          wiki_rack.html
          infra_index.html
          infra_equipment_detail.html
          infra_racks.html
          infra_equipment.html
          infra_ports.html
          infra_connections.html
          infra_import.html
      static/
        css/
          app.css
        js/
          htmx.min.js
          plotly-handlers.js
  docs/
    fastapi-htmx-migration-plan.md
```

## Principios da migracao

1. Nao reescrever a regra de negocio junto com a tela.
2. Primeiro extrair funcoes puras, depois trocar o renderer.
3. Rotas HTMX devem responder com fragments pequenos e reutilizaveis.
4. Navegacao e filtro devem usar URL sempre que fizer sentido.
5. Upload da planilha deve ter ciclo de vida explicito.

## Mapeamento de conceitos Streamlit -> FastAPI/HTMX

### Estado

- `st.session_state` -> cookie de sessao + query params + hidden inputs
- `st.rerun()` -> redirect HTTP ou `hx-get`/`hx-post` com swap parcial
- `st.query_params` -> `request.query_params`

### Upload

- `st.file_uploader` -> `multipart/form-data`
- persistencia temporaria por `session_id` + hash do arquivo

### Cache

- `@st.cache_data` -> cache por hash do arquivo e parametros
- candidatos:
  - `functools.lru_cache` para operacoes pequenas
  - armazenamento serializado em `tmp/`
  - invalidador por `sha256(file_bytes)`

### Componentes visuais

- `st.tabs` -> tabs HTML/HTMX ou seccoes navegaveis por query param
- `st.dataframe` -> tabela HTML server-side, com opcao de DataTables depois
- `st.download_button` -> rota `GET` de download
- `st.plotly_chart` -> `fig.to_json()` + render JS no template

## Backlog por fase

### Fase 0: Preparacao

Objetivo: criar trilho seguro para migrar sem quebrar o app atual.

Entregas:

- adicionar dependencias novas
- criar estrutura `app/web`, `app/services`, `app/repositories`
- definir comando de execucao da nova aplicacao
- adicionar documento de arquitetura

Tarefas:

1. Atualizar `requirements.txt` com:
   - `fastapi`
   - `uvicorn`
   - `jinja2`
   - `python-multipart`
2. Criar `app/web/main.py`
3. Configurar mount de `static/` e `templates/`
4. Criar rota simples `/health`

Criterio de aceite:

- `uvicorn app.web.main:app --reload` sobe localmente
- rota `/health` responde `200`

### Fase 1: Extracao da camada de servicos

Objetivo: remover dependencias de Streamlit da regra de negocio.

Entregas:

- funcoes puras para carga, normalizacao, erros, score e grafos

Tarefas:

1. Criar `app/services/mapping_service.py`
   - mover `load_and_process_data`
   - mover utilitarios `safe`, `hascol`, `ign`
2. Criar `app/services/quality_service.py`
   - mover `detect_errors`
   - mover `health_score`
3. Criar `app/services/graph_service.py`
   - mover `build_switch_graph`
   - mover `radial_pos`
   - mover `get_global_3d_layout`
4. Deixar `app/data.py` e `app/graphs.py` apenas como wrappers temporarios ou marcar para remocao

Criterio de aceite:

- servicos funcionam sem importar `streamlit`
- Streamlit atual continua operacional usando wrappers

### Fase 2: Base HTML e layout compartilhado

Objetivo: criar o shell visual da nova app.

Entregas:

- layout base
- navegacao principal
- CSS consolidado

Tarefas:

1. Criar `base.html`
2. Migrar CSS de `app/config.py` para `static/css/app.css`
3. Definir layout:
   - header
   - sidebar
   - content area
   - area de mensagens
4. Criar pagina inicial com links:
   - mapeamento
   - infraestrutura

Criterio de aceite:

- app navega entre telas base sem Streamlit
- CSS atual reaproveitado com o minimo de regressao

### Fase 3: Modulo Infra primeiro

Objetivo: migrar o modulo de infraestrutura antes do modulo de analise.

Justificativa:

- usa banco local persistente
- CRUD encaixa naturalmente em FastAPI + HTMX
- menor dependencia do upload principal

Entregas:

- index de infraestrutura
- gerenciadores de racks, equipamentos, portas, conexoes
- detalhe de equipamento
- importacao da planilha para infra

Tarefas:

1. Criar `infra_repository.py` como fachada para `app/infra_db.py`
2. Criar `infra_service.py`
3. Criar rotas:
   - `GET /infra`
   - `GET /infra/racks`
   - `POST /infra/racks`
   - `GET /infra/equipment`
   - `GET /infra/equipment/{id}`
   - `POST /infra/equipment`
   - `GET /infra/ports`
   - `POST /infra/ports`
   - `GET /infra/connections`
   - `POST /infra/connections`
4. Criar templates de lista e formularios HTMX
5. Substituir botoes de voltar por links ou redirects reais
6. Criar rota de download do QR code

Criterio de aceite:

- modulo de infraestrutura funciona sem Streamlit
- CRUD principal funciona com swaps HTMX
- deep link de equipamento continua suportado

### Fase 4: Importacao web da planilha

Objetivo: trazer o fluxo de upload e preview para a stack nova.

Entregas:

- upload de planilha
- preview
- confirmacao
- execucao da importacao

Tarefas:

1. Criar `import_service.py`
2. Reusar `parse_spreadsheet` e `execute_import`
3. Criar fluxo:
   - `GET /infra/import`
   - `POST /infra/import/preview`
   - `POST /infra/import/run`
4. Salvar arquivo em `tmp/uploads/<session_id>/`
5. Gerar preview parcial por HTMX
6. Expor erros e avisos em blocos HTML

Criterio de aceite:

- usuario sobe xlsx, ve preview e executa importacao
- resultados batem com a versao Streamlit

### Fase 5: Modulo de mapeamento

Objetivo: migrar dashboard, decks e analise da planilha para a nova stack.

Entregas:

- upload central
- dashboard
- detalhe por deck
- erros
- spotlight
- racks fisicos e patch panels

Tarefas:

1. Criar rota de upload:
   - `GET /mapping`
   - `POST /mapping/upload`
2. Persistir bytes do arquivo por sessao
3. Criar cache do dataset processado por hash
4. Criar paginas:
   - `GET /mapping/dashboard`
   - `GET /mapping/deck/{sheet}`
   - `GET /mapping/errors`
   - `GET /mapping/spotlight`
   - `GET /mapping/racks`
   - `GET /mapping/panels`
5. Trocar filtros da sidebar por formulario GET com query params
6. Trocar `download_button` por endpoint:
   - `GET /mapping/deck/{sheet}/export.csv`

Criterio de aceite:

- fluxo completo de upload e analise roda sem Streamlit
- filtros sao navegaveis por URL

### Fase 6: Wiki de entidades

Objetivo: migrar a navegacao de wiki baseada em estado para URLs reais.

Entregas:

- indice de wiki
- paginas de switch, patch panel e rack

Tarefas:

1. Criar `wiki_service.py`
2. Criar rotas:
   - `GET /wiki`
   - `GET /wiki/switch/{name}`
   - `GET /wiki/panel/{name}`
   - `GET /wiki/rack/{name}`
3. Remover dependencia de `go_wiki` e `st.session_state`
4. Reaproveitar `patch_panel_html` e `rack_diagram_html` como partials Jinja

Criterio de aceite:

- cada entidade tem URL propria
- back/forward do navegador funciona corretamente

### Fase 7: Graficos e visualizacoes especiais

Objetivo: recuperar as visualizacoes ricas com boa performance.

Entregas:

- Plotly integrado via templates
- grafo 3D
- radial por switch
- Sankey

Tarefas:

1. Padronizar serializacao `fig.to_json()`
2. Criar partial `partials/plotly.html`
3. Inicializar graficos no frontend via JS
4. Avaliar lazy-load para graficos pesados
5. Limitar volume de dados em views caras

Criterio de aceite:

- graficos carregam na nova UI sem congelar a pagina

### Fase 8: Corte do Streamlit

Objetivo: remover a antiga casca Streamlit quando houver paridade suficiente.

Entregas:

- Streamlit fora da dependencia principal
- entrypoint unico FastAPI

Tarefas:

1. Validar checklist de paridade
2. Remover imports de `streamlit`
3. Remover wrappers temporarios
4. Atualizar README e comandos de execucao
5. Revisar `requirements.txt`

Criterio de aceite:

- app roda apenas em FastAPI
- principais fluxos estao cobertos por testes

## Rotas iniciais recomendadas

```text
GET   /health
GET   /

GET   /mapping
POST  /mapping/upload
GET   /mapping/dashboard
GET   /mapping/deck/{sheet}
GET   /mapping/errors
GET   /mapping/spotlight
GET   /mapping/racks
GET   /mapping/panels
GET   /mapping/deck/{sheet}/export.csv

GET   /wiki
GET   /wiki/switch/{name}
GET   /wiki/panel/{name}
GET   /wiki/rack/{name}

GET   /infra
GET   /infra/racks
POST  /infra/racks
GET   /infra/equipment
GET   /infra/equipment/{equipment_id}
POST  /infra/equipment
GET   /infra/ports
POST  /infra/ports
GET   /infra/connections
POST  /infra/connections
GET   /infra/import
POST  /infra/import/preview
POST  /infra/import/run
GET   /infra/equipment/{equipment_id}/qr.png
```

## Decisoes tecnicas recomendadas

### 1. Sessao do upload

Nao jogar o arquivo inteiro em cookie ou memoria global sem controle.

Recomendacao:

- gerar `session_id`
- salvar arquivo em `tmp/uploads/<session_id>/<sha256>.xlsx`
- salvar um manifesto simples com:
  - hash
  - nome original
  - timestamp

### 2. Cache do processamento

O dataset processado pode ser reaproveitado por hash do arquivo.

Recomendacao:

- `tmp/cache/<sha256>.pickle`
- invalidacao por hash
- metadados com versao do parser

### 3. Templates

Separar tela e fragmento desde o inicio.

Exemplo:

- pagina completa: `pages/infra_equipment.html`
- fragmento HTMX: `partials/infra/equipment_table.html`

### 4. Tabelas

Nao tentar replicar o `st.dataframe` de imediato.

Primeira iteracao:

- tabela HTML simples
- busca server-side
- export CSV

Segunda iteracao opcional:

- DataTables ou grid JS mais rica

## Riscos e mitigacoes

### Risco: migracao grande demais

Mitigacao:

- executar em paralelo
- modulo infra primeiro
- usar wrappers temporarios

### Risco: performance no processamento de planilhas

Mitigacao:

- cache por hash
- limitar graficos pesados
- evitar recalculo por request

### Risco: regressao de navegacao

Mitigacao:

- mover navegacao para URL
- abandonar estado implicito de pagina

### Risco: HTML inline dificil de manter

Mitigacao:

- converter cedo para partials Jinja
- manter componentes visuais centralizados

## Checklist de paridade funcional

- upload da planilha principal
- dashboard consolidado
- visao por deck com filtros
- wiki de switch
- wiki de rack
- wiki de patch panel
- erros e inconsistencias
- spotlight
- racks fisicos
- patch panels
- CRUD de racks
- CRUD de equipamentos
- CRUD de portas
- CRUD de conexoes
- importacao para infraestrutura
- deep link por QR code
- exportacao CSV

## Ordem sugerida de execucao real

1. Fase 0
2. Fase 1
3. Fase 2
4. Fase 3
5. Fase 4
6. Fase 5
7. Fase 6
8. Fase 7
9. Fase 8

## Proximo passo recomendado

Implementar agora o esqueleto inicial da nova aplicacao:

1. atualizar dependencias
2. criar `app/web/main.py`
3. criar `base.html`
4. criar rota `/health`
5. criar rota `/` com links para `mapping` e `infra`

Depois disso, iniciar a extracao de `app/data.py` para `app/services/mapping_service.py`.
