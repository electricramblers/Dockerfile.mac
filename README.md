# RagFlow Build Instructions

This document provides instructions on how to build and run RagFlow, with a focus on macOS compatibility.

## Repository Overview

Here's a summary of the key files in this repository:

-   `.env.template`: Template file for environment variables. Copy this to `.env` and fill in the required values.
-   `.gitignore`: Specifies intentionally untracked files that Git should ignore.
-   `service_conf.yaml.template`: Template file for service configurations.
-   `docker-compose-mac.yml`: Docker Compose file for macOS, defining the services (Elasticsearch, MySQL, MinIO, Redis, Ragflow) and their configurations.
-   `ragflow_macos.yml`: Ansible playbook for configuring RagFlow on macOS, including dependency updates and Docker image building.
-   `Dockerfile.mac`: Dockerfile for building the RagFlow image on macOS, optimized for performance and compatibility.

## Prerequisites

Before you begin, ensure you have the following installed:

-   [Docker](https://www.docker.com/get-started/)
-   [Ansible](https://docs.ansible.com/get_started/installation.html)
-   [Python](https://www.python.org/downloads/) (for running Ansible)
-   `pyyaml` (install with `pip install pyyaml`)

## Setup Instructions

Follow these steps to set up and run RagFlow:

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd ragflow
    ```

2.  **Configure Environment Variables:**

    *   Copy `.env.template` to `.env`:

        ```bash
        cp .env.template .env
        ```

    *   Edit `.env` and fill in the necessary environment variables, such as passwords, ports, and timezone.

3.  **Run the Ansible Playbook:**

    *   Execute the `ragflow_macos.yml` playbook:

        ```bash
        ansible-playbook ragflow_macos.yml
        ```

    *   This playbook automates the following tasks:
        *   Updates `xgboost` version in `pyproject.toml`.
        *   Enables macOS mode in the `.env` file.
        *   Adds `LIGHTEN=0` to the `.env` file.
        *   Adds `DOCKER_VOLUME_DIRECTORY` to the `.env` file.
        *   Installs `huggingface_hub` and `nltk`.
        *   Downloads dependencies.
        *   Builds the dependencies image.
        *   Clones necessary repositories.
        *   Builds the RagFlow image for macOS.
        *   Starts the services using `docker-compose-mac.yml`.

4.  **Verify the Installation:**

    *   Once the Ansible playbook completes, RagFlow should be running.
    *   Access the web UI at `http://localhost` (or the port specified by `${SVR_HTTP_PORT}` in your `.env` file, default is `9380`).

## Docker Compose Configuration

The `docker-compose-mac.yml` file defines the following services:

-   **es01:** Elasticsearch instance for indexing and searching data.
-   **mysql:** MySQL database for storing application data.
-   **minio:** MinIO server for object storage.
-   **redis:** Redis server for caching.
-   **ragflow:** The main RagFlow application.

Ensure that the ports defined in `.env` are available on your system.

## Dockerfile Notes

The `Dockerfile.mac` is used to build the RagFlow Docker image. It includes:

-   Base image setup with Ubuntu 22.04.
-   Installation of dependencies, including Python, Node.js, and Rust.
-   Configuration of the Python environment using `uv`.
-   Building the frontend application.
-   Copying the necessary files and configurations.

## Troubleshooting

*   **Permissions Issues:** Ensure that the user running the Ansible playbook has the necessary permissions to execute Docker commands.
*   **Port Conflicts:** Check for any port conflicts if the services fail to start.
*   **Resource Limits:** Adjust the `mem_limit` in `docker-compose-mac.yml` if you encounter memory-related issues.

## Additional Information

*   For more detailed information on configuring RagFlow, refer to the comments within the `docker-compose-mac.yml` and `Dockerfile.mac` files.
*   Check the `./ragflow-logs` directory for application logs.
