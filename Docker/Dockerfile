FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS base

WORKDIR /app

RUN apt-get update && apt-get install -y python3 python3-pip gcc g++ freetds-dev && rm -rf /var/lib/apt/lists/*

FROM mcr.microsoft.com/dotnet/sdk:9.0 AS dotnet-builder

WORKDIR /src
COPY ConfigManagementUI/ .
RUN dotnet build "ConfigManagementUI.csproj" -c Release -o /app/build
RUN dotnet publish "ConfigManagementUI.csproj" -c Release -o /app/publish

FROM base AS final

WORKDIR /app

COPY requirements_api.txt .

RUN pip3 install --no-cache-dir --break-system-packages -r requirements_api.txt && pip3 install --no-cache-dir --break-system-packages pymssql==2.2.11

COPY api/ ./api/
COPY backend/ ./backend/

COPY --from=dotnet-builder /app/publish ./frontend

EXPOSE 8000 5202

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 CMD python3 -c "import requests; requests.get('http://localhost:8000/api/health')" || exit 1

CMD ["sh", "-c", "uvicorn api.api:app --host 0.0.0.0 --port 8000 --workers 1 & cd frontend && dotnet ConfigManagementUI.dll --urls http://0.0.0.0:5202"]
