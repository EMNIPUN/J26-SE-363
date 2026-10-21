# Image with the Security Assistant detection tools (static analysis only; no JDK/Maven/Gradle on purpose,
# CodeQL runs with --build-mode=none so no student code is built or executed).
# Build (context = this folder, nothing is copied into the image):
#   docker build -t selvia-security-assistant-tools backend/agentic_framework/app/agents/security_assistant
# Pin and bump these versions deliberately; the exact versions are recorded in every ToolRun.
FROM python:3.11-slim

ARG CODEQL_VERSION=2.20.0
ARG GITLEAKS_VERSION=8.24.0
ARG TRUFFLEHOG_VERSION=3.88.0
ARG OSV_SCANNER_VERSION=2.0.0
ARG ACTIONLINT_VERSION=1.7.7
ARG ZIZMOR_VERSION=1.5.2

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates git unzip nodejs npm \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pip-audit zizmor==${ZIZMOR_VERSION}

RUN set -eux; \
    curl -fsSL https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz | tar -xz -C /usr/local/bin gitleaks; \
    curl -fsSL https://github.com/trufflesecurity/trufflehog/releases/download/v${TRUFFLEHOG_VERSION}/trufflehog_${TRUFFLEHOG_VERSION}_linux_amd64.tar.gz | tar -xz -C /usr/local/bin trufflehog; \
    curl -fsSL -o /usr/local/bin/osv-scanner https://github.com/google/osv-scanner/releases/download/v${OSV_SCANNER_VERSION}/osv-scanner_linux_amd64 && chmod +x /usr/local/bin/osv-scanner; \
    curl -fsSL https://github.com/rhysd/actionlint/releases/download/v${ACTIONLINT_VERSION}/actionlint_${ACTIONLINT_VERSION}_linux_amd64.tar.gz | tar -xz -C /usr/local/bin actionlint

RUN set -eux; \
    curl -fsSL --retry 30 --retry-delay 5 --retry-all-errors -C - -o /tmp/codeql.tar.gz \
        https://github.com/github/codeql-action/releases/download/codeql-bundle-v${CODEQL_VERSION}/codeql-bundle-linux64.tar.gz; \
    tar -xzf /tmp/codeql.tar.gz -C /opt && rm /tmp/codeql.tar.gz; \
    ln -s /opt/codeql/codeql /usr/local/bin/codeql

# A Java runtime only: CodeQL's build-mode=none Java extractor runs `java -version` to pick a JDK
# version for Gradle projects and fails without it. No Maven/Gradle/JDK compiler is installed.
RUN apt-get update && apt-get install -y --no-install-recommends default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# The Security Assistant worker code and Python dependencies are added by the team's worker image build.
WORKDIR /app
CMD ["python", "-m", "app.agents.security_assistant.tools.check"]
