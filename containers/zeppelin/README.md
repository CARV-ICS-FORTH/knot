# Zeppelin container image for Karvdash

The Zeppelin image for Karvdash is built upon the default Zeppelin Docker image, with the addition of the Karvdvash Python API library and remote control utility `karvdashctl`. We also add `kubectl` and `argo` binaries to interface with the platform, as well a pre-built Spark distribution with Hadoop.

**Do not build this image from here. Use the top-level `Makefile`.**
