# Mutating Admission Controller for Karvdash

To build, first create and sign the certificates:
```
(cd ssl && make cert)
docker build -t karvdash-maw:1 .
docker tag karvdash-maw:1 karvdash-maw:latest
```
