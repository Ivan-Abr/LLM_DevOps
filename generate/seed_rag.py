from .rag_store import add_document, check_connection, count_documents

SEED_DOCUMENTS = [
    {
        "category": "dockerfile",
        "title": "Multi-stage Dockerfile для Kotlin/Gradle Spring Boot",
        "content": """FROM gradle:8-jdk21 AS build
WORKDIR /app
COPY . .
RUN gradle build --no-daemon -x test

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /app/build/libs/*.jar app.jar
USER 1000
HEALTHCHECK --interval=10s --timeout=3s CMD curl -f http://localhost:8080/actuator/health || exit 1
ENTRYPOINT ["java", "-jar", "app.jar"]
""",
    },
    {
        "category": "dockerfile",
        "title": "Multi-stage Dockerfile для Python/Poetry FastAPI",
        "content": """FROM python:3.12-slim AS build
WORKDIR /app
RUN pip install poetry
COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt --output requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=build /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
USER 1000
HEALTHCHECK --interval=10s CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
""",
    },
    {
        "category": "compose",
        "title": "docker-compose минимальный сервис без БД",
        "content": """services:
  app:
    build: .
    ports:
      - "8080:8080"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/actuator/health"]
      interval: 10s
      timeout: 5s
      retries: 3
""",
    },
    {
        "category": "compose",
        "title": "docker-compose с PostgreSQL и healthcheck",
        "content": """services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DB_URL=jdbc:postgresql://db:5432/${DB_NAME}
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=${DB_NAME}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  db-data:
""",
    },
    {
        "category": "gitlab_ci",
        "title": ".gitlab-ci.yml для Gradle-проекта",
        "content": """image: gradle:8-jdk21

stages:
  - build
  - test
  - deploy

cache:
  key: "$CI_COMMIT_REF_SLUG"
  paths:
    - .gradle/

build:
  stage: build
  script:
    - gradle build -x test --build-cache
  artifacts:
    paths:
      - build/libs/*.jar
    expire_in: 1 hour

test:
  stage: test
  script:
    - gradle test

deploy:
  stage: deploy
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  only:
    - main
""",
    },
    {
        "category": "gitlab_ci",
        "title": ".gitlab-ci.yml для Maven-проекта",
        "content": """image: maven:3.9-eclipse-temurin-21

stages:
  - build
  - test
  - deploy

cache:
  paths:
    - .m2/repository/

build:
  stage: build
  script:
    - mvn clean package -DskipTests
  artifacts:
    paths:
      - target/*.jar

test:
  stage: test
  script:
    - mvn test

deploy:
  stage: deploy
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  only:
    - main
""",
    },
    {
        "category": "deploy",
        "title": "deploy.sh с корректной сборкой Gradle и обработкой ошибок",
        "content": """#!/bin/bash
set -euo pipefail

# Build the application
./gradlew build -x test || { echo "Build failed"; exit 1; }

# Locate the built jar
JAR_FILE=$(find build/libs -name "*.jar" ! -name "*-plain.jar" | head -n 1)
if [ -z "$JAR_FILE" ]; then
    echo "No jar file found"
    exit 1
fi

# Deploy to the remote server
scp "$JAR_FILE" user@server:/opt/app/app.jar || { echo "Deployment failed"; exit 1; }
ssh user@server "sudo systemctl restart app" || { echo "Restart failed"; exit 1; }

echo "Deployment successful"
""",
    }
]

def seed() -> None:
    if not check_connection():
        print("[ERROR] Cannot connect to RAG store.")

    print(f"Seeding {len(SEED_DOCUMENTS)} document(s)\n")

    for doc in SEED_DOCUMENTS:
        doc_id = add_document(doc["category"], doc["title"], doc["content"])
        print(f"  [{doc_id}] {doc['category']:<12} {doc['title']}")
    total = count_documents()
    print(f"\nDone. Total documents in knowledge_base: {total}")

if __name__ == "__main__":
    seed()