# Genome

Genome is Evolve's integration dashboard. It supplies the landing page for working on the Kubernetes cluster, manages users, launches notebooks, and wires up relevant storage to the appropriate paths inside running containers.

To start working on Genome, first create the Python environment:
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Then:
```
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

