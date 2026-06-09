FROM python:3.12-slim-bookworm AS construtor_producao

# Configuração rígida de variáveis de ambiente do Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Instalação imperativa de pacotes e ligações C do SO
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar ferramenta 'uv' para otimização extrema da instalação de dependências Python
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Fixação da localização geográfica dentro do filesystem virtual criado na imagem
WORKDIR /opt/projeto_ai_pesquisas

# Copiando apenas o manifesto primeiro para usufruir de cache das camadas do Docker
COPY pyproject.toml README.md ./

# Instalação das dependências lendo do pyproject.toml
RUN uv pip install --system -e .

# Copiando todo o resto da estrutura de código
COPY src/ ./src/

# Inicialização restrita
EXPOSE 8000

# Como o projeto atual é um CLI, mantemos o comando base de ajuda.
# Futuramente pode ser substituído por uvicorn se adicionarmos uma API REST
CMD ["sr_pesquisas", "--help"]