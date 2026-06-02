# 🔬 LitScout Knowledge System (LLM Wiki)

Este documento define a estrutura e os fluxos de trabalho para a base de conhecimento do **LitScout**, seguindo a metodologia **LLM Wiki**. O objetivo é transformar resultados de pesquisas acadêmicas isoladas em uma síntese de conhecimento persistente e interconectada.

## 🏗️ Arquitetura da Wiki (`@wiki/`)

A Wiki reside no diretório `/home/m40ista/Projects/srPesquisas/wiki/` e é composta por:

### 1. Camadas de Informação
- **`wiki/sources/`**: Fontes brutas (exports JSON de sessões, PDFs, se houver). São imutáveis.
- **`wiki/compounds/`**: Páginas centrais para cada composto químico ou tema pesquisado (ex: `Carvacrol.md`).
- **`wiki/articles/`**: Fichamentos detalhados de artigos chave, focando em metodologia e resultados.
- **`wiki/concepts/`**: Definições de conceitos científicos, métodos analíticos e mecanismos de ação cruzados.

### 2. Arquivos de Controle
- **`wiki/index.md`**: Catálogo mestre de todas as páginas, organizado por categorias.
- **`wiki/log.md`**: Registro cronológico de todas as buscas realizadas, novos artigos adicionados e atualizações de síntese.

---

## 🛠️ Workflows de Operação

### 🚀 Ingestão (Pós-Busca)
Sempre que uma nova busca for concluída via `litscout search`, o agente deve:
1. **Registrar no Log**: Adicionar entrada em `log.md` com a query e o ID da sessão.
2. **Atualizar Composto**: Se for um composto novo, criar página em `compounds/`. Se existente, atualizar com novos achados e referências.
3. **Fichar Artigos de Alta Relevância**: Criar páginas em `articles/` para os top-N artigos que apresentarem metodologias inovadoras ou resultados contraditórios.
4. **Extrair Conceitos**: Identificar termos recorrentes (ex: "MIC", "Synergistic effect") e garantir que tenham páginas em `concepts/`.
5. **Atualizar Index**: Garantir que todas as novas páginas estejam linkadas em `index.md`.

### 🔍 Consulta e Síntese
Ao responder perguntas sobre a literatura, o agente deve:
1. Consultar o `index.md` para localizar páginas relevantes.
2. Priorizar informações já sintetizadas na Wiki em vez de re-analisar dados brutos.
3. Se a resposta gerar um insight novo (ex: uma comparação entre dois compostos), salvar essa análise como uma nova página na Wiki.

### 🧹 Manutenção (Lint)
Periodicamente, o agente deve revisar a Wiki para:
- Identificar contradições entre artigos diferentes.
- Linkar páginas órfãs.
- Atualizar estados de "conhecimento consolidado" conforme novos dados chegam.

---

## 📜 Regras de Estilo e Convenções
- **Links**: Use links markdown padrão: `[[Conceito]]` (se usando Obsidian) ou `[Conceito](./concepts/Conceito.md)`.
- **Citações**: Sempre referenciar o DOI ou ID do Scholar ao citar um dado.
- **Metadados**: Cada página deve começar com um bloco YAML contendo tags, data de criação e fontes.

---

## 💻 Ambiente e Workflow

### Ambiente de Desenvolvimento
- **Gerenciador**: O projeto utiliza `uv` para gestão de dependências e ambiente virtual.
- **Venv**: O ambiente virtual está em `/home/m40ista/Projects/srPesquisas/litscout/.venv/`.
- **Execução**: Utilize sempre `uv run` para garantir que o ambiente correto seja utilizado, ou garanta a ativação do venv antes de rodar testes/scripts.

### Ciclo de Desenvolvimento
1. **Implementação**: Realizar mudanças cirúrgicas e idiomáticas.
2. **Validação**: Rodar testes e linters (ex: `ruff`).
3. **Commit**: Após cada implementação funcional e validada, realizar o commit com mensagem clara (seguindo Conventional Commits).
4. **Push**: Subir as alterações para o repositório remoto no GitHub.

---

*Este sistema é co-mantido pelo LitScout Agent e pelo usuário.*
