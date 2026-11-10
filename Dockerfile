FROM gcc:14 AS native
WORKDIR /build
COPY cpp_engine ./cpp_engine
RUN make -C cpp_engine
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt constraints.txt ./
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY knowledge ./knowledge
COPY --from=native /build/app/lib/libaiops_core.so ./app/lib/libaiops_core.so
RUN useradd --create-home aiops && mkdir -p /data && chown -R aiops:aiops /data /app
USER aiops
ENV AIOPS_DATABASE_URL=sqlite:////data/ai_ops.db AIOPS_KNOWLEDGE_DB=/data/knowledge.sqlite3 AIOPS_PROVIDER=disabled
EXPOSE 8000
CMD ["sh", "-c", "python -m app.investigation.cli init-db && python -m app.investigation.cli index && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
