FROM python:3.11-slim
WORKDIR /app
# Install the required libraries
RUN pip install PyGithub pyyaml
COPY carbon_router.py .
CMD ["python", "carbon_router.py"]