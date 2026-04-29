# Module 1 — Prometheus

## Exercice 1 : Installer Prometheus

J’ai commencé par récupérer l’image officielle de Prometheus :

```bash
docker pull prom/prometheus:latest
```

Ensuite, j’ai lancé un conteneur Prometheus en exposant le port `9090` :

```bash
docker run -d --name prometheus -p 9090:9090 prom/prometheus:latest
```

Une fois le conteneur lancé, j’ai ouvert l’interface web dans mon navigateur :

```text
http://localhost:9090
```

Pour vérifier que Prometheus fonctionne correctement, je suis allé dans :

```text
Status > Targets
```

La cible `prometheus` était bien en état `UP`, ce qui montre que Prometheus se scrape lui-même avec sa configuration par défaut.

Enfin, j’ai consulté les logs du conteneur :

```bash
docker logs prometheus
```

Dans les logs, je n'ai pas pu trouver la ligne demandé.

## Exercice 2 : Premier `prometheus.yml`

J’ai d’abord arrêté l’ancien conteneur Prometheus :

```bash
docker rm -f prometheus
```

Ensuite, j’ai créé un fichier `prometheus.yml` sur mon poste :

```yaml
global:
  scrape_interval: 10s
  external_labels:
    environment: lab

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]
```

Puis j’ai lancé un nouveau conteneur en utilisant ce fichier :

```bash
docker run -d --name prometheus \
  -p 9090:9090 \
  -v ./prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus:latest \
  --config.file=/etc/prometheus/prometheus.yml \
  --web.enable-lifecycle
```

L’option `--web.enable-lifecycle` permet de recharger la configuration sans redémarrer Prometheus.

Après modification du fichier, j’ai rechargé la configuration avec :

```bash
curl -X POST http://localhost:9090/-/reload
```

Enfin, j’ai vérifié dans l’interface web :

```text
Status > Configuration
```

La configuration affichait bien `scrape_interval: 10s` et le label externe `environment: lab`.
## Exercice 3 : Ajouter `node_exporter`

J’ai d’abord lancé un conteneur `node_exporter` :

```bash
docker run -d --name node-exporter -p 9100:9100 prom/node-exporter:latest
```

Ensuite, j’ai modifié mon fichier `prometheus.yml` pour ajouter un nouveau job :

```yaml
global:
  scrape_interval: 10s
  external_labels:
    environment: lab

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: "node"
    static_configs:
      - targets: ["host.docker.internal:9100"]
```

Le job `node` permet à Prometheus de récupérer les métriques système exposées par `node_exporter`.

Après modification du fichier, j’ai rechargé la configuration avec :

```bash
curl -X POST http://localhost:9090/-/reload
```

Ensuite, j’ai vérifié dans l’interface web :

```text
Status > Targets
```

La cible du job `node` était bien en état `UP`.

Enfin, dans la page de requêtes de Prometheus, j’ai exécuté :

```promql
node_cpu_seconds_total
```

La métrique apparaissait bien, ce qui confirme que Prometheus scrape correctement `node_exporter`.
## Exercice 4 : Découverte de service par fichier

J’ai créé un fichier `targets.json` avec deux endpoints :

```json
[
  {
    "targets": ["host.docker.internal:9100"],
    "labels": {
      "job": "node"
    }
  },
  {
    "targets": ["localhost:9090"],
    "labels": {
      "job": "prometheus"
    }
  }
]
```

Ensuite, j’ai modifié mon fichier `prometheus.yml` pour utiliser `file_sd_configs` :

```yaml
global:
  scrape_interval: 10s
  external_labels:
    environment: lab

scrape_configs:
  - job_name: "file-discovery"
    file_sd_configs:
      - files:
          - /etc/prometheus/sd/*.json
        refresh_interval: 5s
```

Puis j’ai relancé Prometheus en montant les deux fichiers :

```bash
docker rm -f prometheus
docker run -d --name prometheus \
  -p 9090:9090 \
  -v ./prometheus.yml:/etc/prometheus/prometheus.yml \
  -v ./targets.json:/etc/prometheus/sd/targets.json \
  prom/prometheus:latest \
  --config.file=/etc/prometheus/prometheus.yml \
  --web.enable-lifecycle
```

Après ça, j’ai vérifié dans l’interface web :

```text
Status > Targets
```

Les cibles présentes dans le fichier `targets.json` étaient bien affichées.

Enfin, j’ai modifié le fichier `targets.json` en ajoutant ou retirant une cible.
Grâce au `refresh_interval: 5s`, Prometheus a pris en compte le changement automatiquement, sans redémarrage ni rechargement manuel.
## Exercice 5 : Règles d’enregistrement

J’ai d’abord créé un dossier `rules` :

```bash
mkdir rules
```

Puis j’ai créé le fichier `rules/api_rules.yml` :

```yaml
groups:
  - name: api_rules
    interval: 30s
    rules:
      - record: job:http_requests:rate5m
        expr: sum by (job) (rate(demo_http_requests_total[5m]))
```

Ensuite, j’ai ajouté les règles dans mon fichier `prometheus.yml` :

```yaml
global:
  scrape_interval: 10s
  external_labels:
    environment: lab

rule_files:
  - /etc/prometheus/rules/*.yml

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: "demo-api"
    static_configs:
      - targets: ["host.docker.internal:8000"]
```

J’ai relancé Prometheus en montant le dossier des règles :

```bash
docker rm -f prometheus

docker run -d --name prometheus \
  -p 9090:9090 \
  -v ./prometheus.yml:/etc/prometheus/prometheus.yml \
  -v ./rules:/etc/prometheus/rules \
  prom/prometheus:latest \
  --config.file=/etc/prometheus/prometheus.yml \
  --web.enable-lifecycle
```

Après modification, j’ai rechargé Prometheus :

```bash
curl -X POST http://localhost:9090/-/reload
```

J’ai vérifié dans `Status > Rules` que la règle était bien chargée avec une évaluation toutes les `30s`.

Enfin, j’ai testé la nouvelle métrique dans Prometheus :

```promql
job:http_requests:rate5m
```

La métrique apparaît bien avec le job `demo-api`, ce qui montre que la règle d’enregistrement fonctionne.
## Exercice 6 : Règles d’alerte et Alertmanager

J’ai commencé par lancer Alertmanager sur le port `9093` :

```bash
docker run -d --name alertmanager \
  --network monitoring \
  -p 9093:9093 \
  prom/alertmanager:latest
```

Ensuite, j’ai créé le dossier `alerts` :

```bash
mkdir alerts
```

Puis j’ai créé le fichier `alerts/api_alerts.yml` avec l’alerte `HighErrorRate` :

```yaml
groups:
  - name: api_alerts
    rules:
      - alert: HighErrorRate
        expr: sum(rate(demo_http_requests_total{status=~"5.."}[5m])) / sum(rate(demo_http_requests_total[5m])) > 0.05
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Taux d'erreur élevé sur demo-api"
```

Cette alerte se déclenche si plus de `5 %` des requêtes de `demo-api` sont des erreurs pendant au moins `2 minutes`.

Après ça, j’ai modifié mon fichier `prometheus.yml` pour ajouter Alertmanager et le fichier d’alerte :

```yaml
global:
  scrape_interval: 10s
  external_labels:
    environment: lab

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093

rule_files:
  - /etc/prometheus/rules/*.yml
  - /etc/prometheus/alerts/*.yml

scrape_configs:
  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]

  - job_name: "demo-api"
    static_configs:
      - targets: ["host.docker.internal:8000"]
```

J’ai ensuite relancé Prometheus en montant le dossier `alerts` :

```bash
docker rm -f prometheus

docker run -d --name prometheus \
  --network monitoring \
  -p 9090:9090 \
  -v ./prometheus.yml:/etc/prometheus/prometheus.yml \
  -v ./rules:/etc/prometheus/rules \
  -v ./alerts:/etc/prometheus/alerts \
  prom/prometheus:latest \
  --config.file=/etc/prometheus/prometheus.yml \
  --web.enable-lifecycle
```

J’ai rechargé la configuration Prometheus :

```bash
curl -X POST http://localhost:9090/-/reload
```

Pour vérifier que la règle était bien chargée, je suis allé dans :

```text
Status > Rules
```

La règle `HighErrorRate` apparaissait bien dans le groupe `api_alerts`.

Pour déclencher l’alerte, j’ai généré des erreurs en continu sur `demo-api` :

```bash
while true; do
  curl -s http://localhost:8000/
done
```

Cette commande envoie des requêtes vers une route qui renvoie des erreurs. 

Ensuite, j’ai attendu environ `2 minutes`, car l’alerte contient `for: 2m`.

J’ai vérifié l’état de l’alerte dans Prometheus :

```text
http://localhost:9090/alerts
```

L’alerte est passée en `FIRING`.

Enfin, j’ai ouvert Alertmanager :

```text
http://localhost:9093
```

L’alerte `HighErrorRate` apparaissait bien dans l’interface, donc Prometheus envoyait correctement les alertes vers Alertmanager.
## Exercice 7 : PromQL — bases

J’ai ouvert l’interface Prometheus :

```text
http://localhost:9090
```

Ensuite, j’ai testé cette première requête :

```promql
demo_http_requests_total
```

Le résultat est un **vecteur instantané**.
Il affiche la valeur actuelle de chaque série au moment où la requête est lancée.

Après, j’ai exécuté :

```promql
demo_http_requests_total[1m]
```

Cette fois, le résultat est un **vecteur de plage**.
Il affiche l’historique des valeurs sur les 1 dernières minutes pour chaque série. Ce type de résultat ne se trace pas directement comme une courbe simple.

Ensuite, j’ai lancé :

```promql
rate(demo_http_requests_total[1m])
```

`rate()` calcule la vitesse d’augmentation de la métrique sur 1 minute.
Le résultat redevient un **vecteur instantané**.

Chaque ligne correspond à un jeu de labels différent, par exemple selon la route, la méthode HTTP, le status ou le job. Cela permet de voir le taux de requêtes séparément pour chaque série.

Enfin, j’ai exécuté :

```promql
scalar(sum(demo_http_requests_total))
```

Cette requête renvoie un **scalaire**, donc une seule valeur numérique.
Ici, elle correspond au total global des requêtes HTTP de `demo-api`.
# Exercice 8 : PromQL — agrégations et jointures

J’ai d’abord généré du trafic régulier vers les deux endpoints demandés :

```bash
while true; do
  curl -s http://localhost:8000/api/users > /dev/null
  curl -s http://localhost:8000/api/orders > /dev/null
  sleep 0.5
done
```

Ensuite, dans Prometheus, j’ai calculé le taux de requêtes total par endpoint :

```promql
sum by (endpoint) (rate(demo_http_requests_total[1m]))
```

Cette requête calcule d’abord le taux de requêtes avec `rate()`, puis regroupe les résultats par `endpoint`.

Pour le ratio d’erreurs par endpoint, j’ai utilisé :

```promql
sum by (endpoint) (rate(demo_http_requests_total{status=~"5.."}[1m]))
/
sum by (endpoint) (rate(demo_http_requests_total[1m]))
```

Cette requête divise le taux de requêtes en erreur `5xx` par le taux total de requêtes, pour chaque endpoint.

Enfin, pour afficher les 3 pods avec le plus de requêtes, j’ai utilisé `topk` :

```promql
topk(3, sum by (pod) (rate(demo_http_requests_total[1m])))
```

Cette requête calcule le taux de requêtes par pod, puis garde seulement les 3 plus élevés.

J’ai bien utilisé `rate()` avant `sum()`, car il faut d’abord calculer le taux sur chaque série avant de faire l’agrégation.
