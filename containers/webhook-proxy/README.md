# Webhook proxy for Karvdash

Karvdash provides both mutating and validating admission webhooks, that need to be accessed over SSL. In the Karvdash deployment, we use a secondary NGINX container as an HTTPS proxy. This container creates a self-signed certificate and registers the webhooks when it runs.

**Do not build this image from here. Use the top-level `Makefile`.**
