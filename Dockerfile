FROM ghcr.io/uwit-iam/poetry AS dependencies
WORKDIR build/
COPY poetry.lock pyproject.toml ./
RUN apt-get update && apt-get -y install jq && \
    poetry install --no-root --no-interaction --no-dev

FROM dependencies AS cli
COPY ./fingerprinter ./fingerprinter
RUN poetry install --no-interaction --no-dev
ENTRYPOINT ["fingerprinter"]
