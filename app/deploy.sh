#!/bin/bash
set -e

# Generate unique timestamp tag
IMAGE_TAG=$(date +%Y%m%d%H%M%S)
ECR_REGISTRY="068167017169.dkr.ecr.us-east-1.amazonaws.com"
IMAGE_NAME="cookbook-chatbot"
FULL_IMAGE="${ECR_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "Building Docker image with tag: ${IMAGE_TAG}"
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

echo "Tagging image for ECR"
docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${FULL_IMAGE}

echo "Pushing to ECR"
docker push ${FULL_IMAGE}

echo "Image pushed successfully: ${FULL_IMAGE}"

echo "Updating Terraform with new image tag"
echo "Container image: ${FULL_IMAGE}"
cd ../terraform
terraform apply -var="container_image=${FULL_IMAGE}"