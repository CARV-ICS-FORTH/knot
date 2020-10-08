# Zeppelin container image for Karvdash with CUDA and TensorFlow

This is a very simple stitching of various Dockerfiles. The idea was to recreate `nvidia:cuda:10.1-base-ubuntu16.04` and `tensorflow/tensorflow:2.2.1-gpu` on top of our custom Zeppelin Docker image, so to run TensorFlow with GPU support inside Zeppelin.

**Do not build this image from here. Use the top-level `Makefile`.**
