FROM python:3.11-slim

# create non-root user
RUN useradd -m runner -s /bin/bash

# minimal runtime deps (add only what your tasks need)
RUN apt-get update && apt-get install -y --no-install-recommends gcc curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /home/runner/work

# entrypoint will run a script that times out and isolates more
COPY sandbox_entrypoint.sh /usr/local/bin/sandbox_entrypoint.sh
RUN chmod +x /usr/local/bin/sandbox_entrypoint.sh

USER runner
ENV HOME=/home/runner

ENTRYPOINT ["/usr/local/bin/sandbox_entrypoint.sh"]
