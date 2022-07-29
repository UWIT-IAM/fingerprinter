ARG IMAGE
FROM ${IMAGE} AS deployment
ARG DEPLOYMENT_ID
ENV DEPLOYMENT_ID=${DEPLOYMENT_ID}
RUN test -n "${DEPLOYMENT_ID}"
