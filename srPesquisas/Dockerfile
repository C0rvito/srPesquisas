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

# Copiando todo o resto da estrutura de código ANTES da instalação para evitar ModuleNotFoundError
COPY src/ ./src/

# Instalação das dependências lendo do pyproject.toml
RUN uv pip install --system -e .

# Inicialização restrita
EXPOSE 8000

# Comando para iniciar o servidor do Streamlit na porta 8000
CMD ["streamlit", "run", "src/sr_pesquisas/app.py", "--server.port=8000", "--server.address=0.0.0.0"]
